"""Sequential retarget run: timeline with dwells and unload buffers, keyframe optimisation, relaxation."""
import sys; sys.path.insert(0,'/home/claude/sim')
from opt import *
import pickle, time
DWELL={204:8,240:8,477:8,625:9,731:8}
B_PRE=5; B_POST=2; NDEC=12
SKIP=set(range(241,248))        # the right foot leaves the floor from its frame-240 pose
JUMP_FROM,JUMP_TO,JUMP_N=240,248,14
def timeline(dwell=DWELL,last=None):
    src=[]
    for i in range(NO if last is None else last+1):
        if i in SKIP: continue
        src.append(i); src+=[i]*dwell.get(i,0)
    src=np.array(src); sup=[set() for _ in src]
    for n in NAMES:
        for a,b in IV[n]:
            while a in SKIP: a+=1
            while b in SKIP: b-=1
            ia=np.where(src==a)[0]; ib=np.where(src==b)[0]
            if len(ia)==0: continue
            na=ia[0]; nb=ib[-1] if len(ib) else len(src)-1
            lo=na+(B_POST if a>0 else 0); hi=nb-(B_PRE if b<NO-1 and len(ib) else 0)
            for f in range(lo,hi+1): sup[f].add(n)
    return src,sup
# palm stance offsets (world mm) per stance interval index, per side
PALM_STANCE_OFF={'L':[(0,-30),(0,0),(0,30)],'R':[(0,0),(0,0),(0,20),(0,30)]}
def palm_offsets(src,stance_off=PALM_STANCE_OFF):
    out={sd:np.zeros((len(src),3)) for sd in 'LR'}
    for sd,name in (('L','leftPalm'),('R','rightPalm')):
        iv=IV[name]; offs=[np.array([o[0],o[1],0.0]) for o in stance_off[sd]]
        for f,i in enumerate(src):
            if i<=iv[0][1]:
                out[sd][f]=offs[0]+(np.array([0,0,7.0*min(1.0,max(0.0,(iv[0][0]-i)/6.0))]) if i<iv[0][0] else 0); continue
            done=False
            for k,(a,b) in enumerate(iv):
                if a<=i<=b: out[sd][f]=offs[k]; done=True; break
                if k+1<len(iv) and b<i<iv[k+1][0]:
                    u0=(i-b)/(iv[k+1][0]-b); u=smooth(u0); out[sd][f]=offs[k]*(1-u)+offs[k+1]*u+np.array([0,0,8.0*math.sin(math.pi*u0)**2]); done=True; break
            if not done: out[sd][f]=offs[-1]
    return out
def logm3(R):
    c=(np.trace(R)-1)/2; th=math.acos(max(-1,min(1,c)))
    if th<1e-9: return np.zeros(3)
    return th/(2*math.sin(th))*np.array([R[2,1]-R[1,2],R[0,2]-R[2,0],R[1,0]-R[0,1]])
class Runner:
    def __init__(s,src,sup,poff,v_init=None):
        s.src=src; s.sup=sup; s.poff=poff; s.n=len(src); s.v=np.zeros((s.n,6)) if v_init is None else v_init.copy()
    def frame(s,f):
        fr=Frame(int(s.src[f]),s.sup[f],palm_off={sd:s.poff[sd][f].copy() for sd in 'LR'})
        i=fr.src
        for sd,(a,b) in (('L',(705,729)),('R',(732,756))):     # higher foot lift while re-placing the feet on the tread
            if a<=i<=b: fr.foot_off[sd]=np.array([0,0,7.0*math.sin(math.pi*(i-a+1)/(b-a+2))**2])
        for sd,o,sg in (('L',0,-1.0),('R',10,1.0)):              # hanging foot a little more dorsiflexed: thigh/foot gap > 10 mm
            if leg_mode(sd,i) in ('knee','approach'): fr.q_off[6+o]=4.0*sg
        if False and JUMP_TO<=i<JUMP_TO+JUMP_N:      # blend the right foot from its frame-240 pose into the original swing path
            w=1-smooth((i-JUMP_TO+1)/(JUMP_N+1)); R0,p0=REFS[JUMP_FROM].foot['R']; R1,p1=fr.ref.foot['R']
            fr.foot_off['R']=fr.foot_off['R']+(p0-p1)*w; fr.foot_rot['R']=expm(logm3(R0@R1.T)*w)
        return fr
    def keyopt(s,keys,lam=0.02,maxiter=160,log=None,v0=None):
        vprev=np.zeros(6) if v0 is None else v0; st=REFS[int(s.src[keys[0]])].st.copy(); out={}
        t=time.time()
        for n,f in enumerate(keys):
            fr=s.frame(f)
            v,J=optimise(fr,vprev.copy(),st,vprev=vprev if n>0 else None,lam=lam,maxiter=maxiter)
            if n==0 or True:
                # also try from zero when the warm start looks poor
                e=evaluate(fr,v,st,full=True)
                if e['r'] is None or e['r']['s']>0.42 or e['J']-0.02*max(0,e['rsw']-1.0)>e['r']['s']+0.15:
                    for vs,stp in ((np.zeros(6),1.0),(vprev+np.array([1,-1,1,1,-1,-2.]),0.8),(vprev+np.array([-1,1,0,-2,1,2.]),0.8)):
                        v2,J2=optimise(fr,vs,st,vprev=vprev if n>0 else None,lam=lam*0.3,maxiter=maxiter+80,step=stp)
                        if J2<J-1e-3: v,J=v2,J2; e=evaluate(fr,v,st,full=True)
            st=e['st']; s.v[f]=v; vprev=v; out[f]=e
            if log: print(f"{f} src{s.src[f]} ph{fr.ref.phase} s={'X' if e['r'] is None else round(e['r']['s'],3)} j={'' if e['r'] is None else e['r']['jmax']} env={e['env']:.1f} m={e['margin']:.0f} res={e['res']:.2f}/{e['rsw']:.1f} v={(v*SC).round(0)} t={time.time()-t:.0f}",file=log,flush=True)
        return out
if __name__=='__main__':
    a,b,tag=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]; KS=int(sys.argv[4]) if len(sys.argv)>4 else 3
    src,sup=timeline(); poff=palm_offsets(src)
    R=Runner(src,sup,poff); keys=list(range(a,min(b,len(src)),KS))
    log=open(f'log_{tag}.txt','w'); out=R.keyopt(keys,log=log)
    pickle.dump(dict(keys=keys,v={f:R.v[f] for f in keys},s={f:(None if out[f]['r'] is None else out[f]['r']['s']) for f in keys}),open(f'key_{tag}.pkl','wb'))
