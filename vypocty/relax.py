"""Red-black relaxation of the keyframe torso parameters with neighbour coupling, look-ahead support
and exact (FCL) self/environment clearance penalties."""
import sys; sys.path.insert(0,'/home/claude/sim')
from fullpass import *
LOOK=3; KS=3; HARD=[(244,266),(640,662),(64,86)]
def setup():
    src,sup=timeline(); poff=palm_offsets(src); R=Runner(src,sup,poff); n=len(src)
    supo=[]
    for f in range(n):
        s=set(sup[f])
        for g in range(f,min(n,f+LOOK+1)): s&=sup[g]
        supo.append(s if len(s)>=2 else set(sup[f]))
    return R,supo
def env_exact(st,fr):
    ex=set()
    for sd in 'LR':
        foot=('leftFoot' if sd=='L' else 'rightFoot')
        a_near=any(a-8<=fr.src<=b+8 for a,b in IV[foot])
        if leg_mode(sd,fr.src)=='foot' and a_near: ex.add((FOOT[sd],'body'))
        k0,k1=KNEE[sd]
        if k0-14<=fr.src<=k1+14: ex.add((SHIN[sd],'sleeve'))
    return K.env_dist(st,exclude=ex,cutoff=12,placed=True)[0]
def cost_full(R,supo,f,v,st_init,exact=False,detail=False):
    fr=R.frame(f); st=make_state(fr,v,st_init); rc,rsw=limb_ik(st,fr,both=True)
    r=stat(st,supo[f],mu=0.4); m=margin(st,supo[f])
    if exact:
        K.place(st); dself=K.min_dist(st,cutoff=12.5,placed=True)[0]; env=env_exact(st,fr)
    else:
        dself=99; env,_=env_fast(st,fr)
    straight=0.0
    for sd in 'LR':
        o_=0 if sd=='L' else 10
        if fr.src<=PALM_END[sd] and ('leftPalm' if sd=='L' else 'rightPalm') in fr.ref.contacts: straight+=max(0,4.0-abs(st.q[10+o_]))
        if leg_mode(sd,fr.src)=='foot' and ('leftFoot' if sd=='L' else 'rightFoot') in fr.ref.contacts and fr.src<300: straight+=max(0,3.0-abs(st.q[5+o_]))
    J=(r['s'] if r else 3.0+max(0,-m)/50.0)+0.02*straight+0.02*max(0,7.5-env)**2+0.5*max(0,rc-0.15)+0.004*max(0,rsw-2.0)+0.004*max(0,12-m)**2+0.02*max(0,11.0-dself)**2
    if detail: return dict(J=J,s=None if r is None else r['s'],env=env,self=dself,rc=rc,rsw=rsw,m=m,st=st)
    return J
def relax_key(R,supo,V,keys,k,st_init,lam=0.05,exact=False,maxiter=90,starts=1):
    f=keys[k]; nb=[V[keys[j]] for j in (k-1,k+1) if 0<=j<len(keys)]
    def cost(v):
        J=cost_full(R,supo,f,v,st_init,exact=exact)+2e-4*float(v@v)
        for w in nb: J+=lam*float((v-w)@(v-w))
        return J
    best=None
    cands=[V[f].copy()]
    if starts>1: cands.append(np.mean(nb,axis=0))
    if starts>2: cands+=[np.zeros(6),np.array([4,0,0.5,0,0,0.]),np.array([3,-1,2,1,-1,-2.])]
    for v0 in cands:
        sim=np.vstack([v0]+[v0+0.5*np.eye(6)[i] for i in range(6)])
        rs=minimize(cost,v0,method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.0007,maxiter=maxiter,initial_simplex=sim))
        if best is None or rs.fun<best.fun: best=rs
    return best.x,best.fun
if __name__=='__main__':
    vin,vout,color,part,nparts=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
    flags=set(json.load(open(sys.argv[6]))) if len(sys.argv)>6 else set()
    only=len(sys.argv)>7 and sys.argv[7]=='only'
    EXF=set(json.load(open(sys.argv[8]))) if len(sys.argv)>8 else flags
    R,supo=setup(); V=np.load(vin); n=len(R.src); keys=list(range(0,n,KS))
    todo=[k for k in range(len(keys)) if k%2==color and (k//2)%nparts==part and keys[k]>=9]
    if only: todo=[k for k in todo if any(abs(keys[k]-g)<=3 for g in flags)]
    out={}; t=time.time(); log=open(vout+'.log','w')
    for k in todo:
        f=keys[k]; ex=any(abs(f-g)<=4 for g in EXF)
        st0=REFS[int(R.src[f])].st
        hard=any(a<=f<=b for a,b in HARD)
        v,J=relax_key(R,supo,V,keys,k,st0,exact=ex,starts=3 if hard else 2,maxiter=140 if hard else 90)
        d=cost_full(R,supo,f,v,st0,exact=ex,detail=True); out[f]=v
        print(f,'J',round(J,3),'s',d['s'] and round(d['s'],3),'env',round(d['env'],1),'self',round(d['self'],1),'rc',round(d['rc'],2),'rsw',round(d['rsw'],1),'m',round(d['m']),round(time.time()-t),file=log,flush=True)
    pickle.dump(out,open(vout,'wb'))
