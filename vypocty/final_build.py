import sys; sys.path.insert(0,'/home/claude/sim')
from relax import *
from seqmetrics import *
import run_ending
from scipy.ndimage import gaussian_filter1d
def smooth_swing(recs,sigma=1.6):
    n=len(recs); Q=np.array([r['state'].q for r in recs]); Qs=Q.copy()
    groups=[('leftFoot','leftKnee',[2,3,4,5,6,7]),('rightFoot','rightKnee',[12,13,14,15,16,17]),('leftPalm',None,[8,9,10]),('rightPalm',None,[18,19,20])]
    for a,b,js in groups:
        on=np.array([(a in r['contacts']) or (b is not None and b in r['contacts']) for r in recs])
        near=on.copy()
        for i in np.where(on)[0]: near[max(0,i-1):i+2]=True
        w=gaussian_filter1d((~near).astype(float),2.0)      # 0 near contact .. 1 in free swing
        w=np.where(near,0.0,np.clip(w*1.5,0,1))
        for j in js:
            f=gaussian_filter1d(Q[:,j],sigma,mode='nearest'); Qs[:,j]=Q[:,j]*(1-w)+f*w
        # after each lift-off the free limb leaves its last contact pose gradually (no jump of the IK target)
        sw=~on
        for a_ in np.where(sw[1:]&~sw[:-1])[0]+1:
            b_=a_
            while b_<n and sw[b_]: b_+=1
            L=min(12,b_-a_)
            for k in range(L):
                u=smooth((k+1)/(L+1)); Qs[a_+k,js]=Qs[a_-1,js]+(Qs[a_+k,js]-Qs[a_-1,js])*u
        for it in range(4):
            spd=np.abs(np.diff(Qs[:,js],axis=0)).max(axis=1)*HZ
            for i in np.where(spd>40)[0]:
                a_=max(0,i-2); b_=min(n-1,i+3)
                if near[a_+1:b_].all(): continue
                for k in range(a_+1,b_):
                    if not on[k]: Qs[k,js]=Qs[a_,js]+(Qs[b_,js]-Qs[a_,js])*(k-a_)/(b_-a_)
    for r,q in zip(recs,Qs):
        st=r['state']; st.q=q.copy(); st.update()
    return recs
def build(Vfile,log=print):
    R,supo=setup(); V=np.load(Vfile); n=len(R.src); keys=list(range(0,n,KS))
    v=interp_v(keys,{f:V[f] for f in keys},n)
    v=gaussian_filter1d(v,1.2,axis=0,mode='nearest'); v[:4]*=np.linspace(0,1,4)[:,None]
    f_end=int(np.where(R.src==757)[0][-1])
    # pass 1: solve every frame (this also projects unreachable torso poses back to reachable ones)
    seq1=full_pass(R,v.copy(),0,f_end); n=f_end+1
    A=np.zeros((n,6))
    for f in range(n):
        r=REFS[int(R.src[f])]; vv=seq1[f][0].v; A[f,:3]=r.pel+vv[:3]*SC[:3]; A[f,3:]=euler(r.R)+vv[3:]*SC[3:]
    lim=np.array([4.0,4.0,4.0,1.2,1.2,1.2])
    # where the torso would still jump between two frames (support change / skipped source frames) insert hold frames:
    # contacts stay, free limbs wait, the torso travels at a limited rate
    rate=(np.abs(np.diff(A,axis=0))/lim).max(axis=1)
    src2=[];sup2=[];pl=[];pr=[];A2=[]
    for f in range(n):
        src2.append(R.src[f]); sup2.append(R.sup[f]); pl.append(R.poff['L'][f]); pr.append(R.poff['R'][f]); A2.append(A[f])
        if f<n-1 and rate[f]>1.3:
            m=int(math.ceil(rate[f]*1.4))
            for k in range(1,m+1):
                u=smooth(k/(m+1)); src2.append(R.src[f+1]); sup2.append(R.sup[f+1]&R.sup[f]); pl.append(R.poff['L'][f+1]); pr.append(R.poff['R'][f+1]); A2.append(A[f]+(A[f+1]-A[f])*u)
    log('inserted hold frames',len(src2)-n,'max rate',round(float(rate.max()),1))
    R.src=np.array(src2); R.sup=sup2; R.poff={'L':np.array(pl),'R':np.array(pr)}; A=np.array(A2); n=len(src2); R.n=n
    v=np.zeros((n,6))
    for f in range(n):
        r=REFS[int(R.src[f])]; v[f,:3]=(A[f,:3]-r.pel)/SC[:3]; v[f,3:]=(A[f,3:]-euler(r.R))/SC[3:]
    f_end=n-1
    # long hold runs: optimise two way-points inside (straight interpolation between two optima can be poor)
    ins=np.zeros(n,bool); k_=0
    for f in range(len(rate)+1):
        k_+=1
        if f<len(rate) and rate[f]>1.3:
            m=int(math.ceil(rate[f]*1.4)); ins[k_:k_+m]=True; k_+=m
    f=0
    while f<n:
        if ins[f]:
            g=f
            while g<n and ins[g]: g+=1
            m=g-f
            if m>=4:
                wps=[f+m//3,f+(2*m)//3]; pts={f-1:v[f-1].copy(),g:v[g].copy() if g<n else v[g-1].copy()}
                for wf in wps:
                    v0=v[wf].copy(); st0=REFS[int(R.src[wf])].st
                    def c_(x): return cost_full(R,R.sup,wf,x,st0,exact=True)+0.04*float((x-v0)@(x-v0))
                    best=None
                    for seed in (v0,v[g] if g<n else v0,v[f-1]):
                        sim=np.vstack([seed]+[seed+0.5*np.eye(6)[i_] for i_ in range(6)])
                        rs=minimize(c_,seed,method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.0007,maxiter=110,initial_simplex=sim))
                        if best is None or rs.fun<best.fun: best=rs
                    pts[wf]=best.x; d_=cost_full(R,R.sup,wf,best.x,st0,exact=True,detail=True); log('  hold way-point',wf,'s',d_['s'] and round(d_['s'],3),'env',round(d_['env'],1),'self',round(d_['self'],1),'m',round(d_['m']))
                def absA(fi,x):
                    r=REFS[int(R.src[fi])]; return np.concatenate([r.pel+x[:3]*SC[:3],euler(r.R)+x[3:]*SC[3:]])
                gi=min(g,n-1); ks=sorted(pts); Ak=np.array([absA(min(k,n-1),pts[k]) for k in ks])
                for fi in range(f,g):
                    a_=np.array([np.interp(fi,ks,Ak[:,c]) for c in range(6)]); r=REFS[int(R.src[fi])]
                    v[fi,:3]=(a_[:3]-r.pel)/SC[:3]; v[fi,3:]=(a_[3:]-euler(r.R))/SC[3:]
            f=g
        else: f+=1
    seq=full_pass(R,v,0,f_end)
    recs=[dict(state=st,support=set(fr.support),contacts=set(fr.ref.contacts),phase=fr.ref.phase,src=fr.src,rc=fr.rc,rsw=fr.rsw,proj=getattr(fr,'projected',False)) for fr,st in seq]
    # repair pass: isolated frames that failed (unreached contact, no equilibrium, joint-speed spike) are re-solved
    # from the neighbouring solution instead of the original pose
    def bad_frames():
        Q=np.array([r['state'].q for r in recs]); spd=np.abs(np.diff(Q,axis=0))*HZ; bad=set()
        for i,r in enumerate(recs):
            if r['rc']>0.3 or stat(r['state'],r['support'],mu=0.5) is None: bad.add(i)
        return sorted(b_ for b_ in bad if 0<b_<len(recs)-1)
    for rnd in range(3):
        bad=bad_frames(); log('repair round',rnd,len(bad),bad[:40])
        if not bad: break
        for i in bad:
            fr,_=seq[i]; prev=recs[i-1]['state']; nxt=recs[i+1]['state']
            best=None
            for vv in (0.5*(seq[i-1][0].v+seq[i+1][0].v),fr.v,seq[i-1][0].v):
                for seed in (prev,nxt):
                    st=make_state(fr,vv,seed); rc,rsw=limb_ik(st,fr,both=True,iters=60)
                    x=stat(st,fr.support,mu=0.5); sc=(rc*2 if rc>0.15 else 0)+(5 if x is None else x['s'])+0.02*np.abs(st.q-prev.q).max()
                    if best is None or sc<best[0]: best=(sc,st,rc,rsw,vv)
            recs[i]['state']=best[1]; recs[i]['rc']=best[2]; recs[i]['rsw']=best[3]; fr.v=best[4]
    recs=smooth_swing(recs)
    # remove residual frame-to-frame zig-zag (alternating IK solutions) with a 3-point median on the affected joints
    Q=np.array([r['state'].q for r in recs])
    for it in range(3):
        d=np.diff(Q,axis=0); zz=(d[1:]*d[:-1]<0)&(np.abs(d[1:])>0.8)&(np.abs(d[:-1])>0.8); fr_,jj_=np.where(zz)
        if len(fr_)==0: break
        break
    log('zig-zag samples (not filtered)',int(len(fr_)))
    for r,q in zip(recs,Q):
        r['state'].q=q.copy(); r['state'].update()
    st_last=recs[-1]['state']
    pL=st_last.pt(10,refpt('L','P')); pR=st_last.pt(20,refpt('R','P')); pL[2]=PZ=STEP_H+PAD_R; pR[2]=PZ
    end=run_ending.run(st_last,pL,pR,log=log)
    for e in end: e['phase']=13+e['phase']; e['src']=-1; e['rc']=0; e['rsw']=0; e['proj']=False
    return recs+end
PHASES_END=[('Dlaně blíž k chodidlům','Emil stojí na obou chodidlech a přenese dlaně jednu po druhé z hloubky 234 mm na 160 mm za hranu, těsně před špičky.'),
            ('Přenos váhy na chodidla','S dlaněmi na nášlapu si Emil dřepne nad paty a zvedne trup. Dlaně se odlehčí dřív, než je zvedne.'),
            ('Odlehčení dlaní','Paže se uvolní a visí svisle. Trup se ze dřepu zvedá, těžiště zůstává nad chodidly.'),
            ('Vzpřímení','Emil se z hlubokého dřepu narovná do stoje na schodu.')]
if __name__=='__main__':
    recs=build(sys.argv[1]); pickle.dump(recs,open(sys.argv[2],'wb')); print('frames',len(recs))
    rows,sp=seq_metrics(recs,exact=(len(sys.argv)<4)); pickle.dump((rows,sp),open(sys.argv[2].replace('.pkl','_m.pkl'),'wb'))
    summarize(rows,sp,'NEW')
    def col(k): return np.array([np.nan if r.get(k) is None else r[k] for r in rows],float)
    s=col('s50'); print('s>0.5 or nan:',[(i,None if np.isnan(x) else round(x,2)) for i,x in enumerate(s) if not x<=0.5])
    print('rc>0.3:',[(i,round(r['rc'],1)) for i,r in enumerate(recs) if r['rc']>0.3])
    print('margin<8:',[(i,round(r['margin'])) for i,r in enumerate(rows) if r['margin']<8])
    print('speed>45:',[(int(i),round(float(sp[i].max()))) for i in sorted(set(np.where(sp>45)[0].tolist()))])
    if len(sys.argv)>3: sys.exit()
    print('self<10:',[(i,round(r['self'],1),r['selfpair'][0][0],r['selfpair'][1][0]) for i,r in enumerate(rows) if r['self']<10])
    print('env<5:',[(i,round(r['env'],1),r['envkey'][0]) for i,r in enumerate(rows) if r['env']<5])
    print('pad<5:',[(i,round(r['pad'],1)) for i,r in enumerate(rows) if r['pad']<5])
    print('pen>0.3:',[(i,round(r['pen'],2)) for i,r in enumerate(rows) if r['pen']>0.3])
