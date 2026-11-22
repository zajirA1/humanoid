import sys; sys.path.insert(0,'/home/claude/sim')
from ending import *
import pickle, time
F={'leftFoot','rightFoot'}; LP='leftPalm'; RP='rightPalm'
def run(st0,palmL,palmR,yp_new=-160.0,log=print):
    """returns list of dict(state,support,contacts,phase) ; phases: 0 regrip, 1 weight to feet, 2 release, 3 rise"""
    E=Ending(st0,palmL,palmR); out=[]
    p=params_of(st0); st=st0.copy()
    armsP=lambda l,r:{'L':('palm',l),'R':('palm',r)}
    L0=np.array(palmL,float); R0=np.array(palmR,float); L1=np.array([146,yp_new,PZ]); R1=np.array([-146,yp_new,PZ])
    def add(st,support,contacts,ph): out.append(dict(state=st.copy(),support=set(support),contacts=set(contacts),phase=ph))
    def move(p_from,p_to,arms_fn,support,contacts,ph,n):
        nonlocal st
        for i in range(1,n+1):
            u=smooth(i/n); pp=p_from+(p_to-p_from)*u; st,res=E.pose(pp,arms_fn(u),st); add(st,support,contacts,ph)
        return p_to.copy()
    allc=F|{LP,RP}
    # --- A: symmetric all-fours, then pre-unload the left palm
    t=time.time()
    pS=p.copy(); pS[[0,4,5]]=0
    pA,_,J=E.opt(pS,armsP(L0,R0),F|{RP},st,free=(0,1,2,3)); log('pre-unload L palm',pA.round(1),round(J,3))
    p=move(p,pA,lambda u:armsP(L0,R0),allc,allc,0,12)
    for i in range(4): add(st,F|{RP},allc,0)
    # left palm swing (lift 28 mm)
    def swing(a,b,u): q=a+(b-a)*smooth(u); q=q.copy(); q[2]=PZ+16*math.sin(math.pi*u)**1.0; return q
    pB,_,J=E.opt(pA,armsP(L1,R0),F|{LP},st,free=(0,1,2,3)); log('pre-unload R palm',pB.round(1),round(J,3))
    pm=(pA+pB)/2
    n=26
    for i in range(1,n+1):
        u=i/n; pp=pA+(pm-pA)*smooth(u); st,res=E.pose(pp,armsP(swing(L0,L1,u),R0),st); add(st,F|{RP},F|{RP} if i<n else allc,0)
    p=pm.copy(); p=move(p,pB,lambda u:armsP(L1,R0),allc,allc,0,8)
    for i in range(4): add(st,F|{LP},allc,0)
    # pose with both palms near the feet, weight on the feet only
    fy=E.foot['L'][1][1]; best=None
    for seed in ([0,fy+72,STEP_H+147,46,0,0],[0,fy+68,STEP_H+150,50,0,0],list(pB*np.array([0,1,1,1,0,0]))):
        pc_,_,J=E.opt(np.array(seed,float),armsP(L1,R1),F,st,free=(1,2,3),maxiter=300)
        if best is None or J<best[1]: best=(pc_,J)
    pC,J=best; log('feet-only pose A',pC.round(1),round(J,3))
    pm=pB.copy()
    for i in range(1,n+1):
        u=i/n; pp=pB+(pm-pB)*smooth(u); st,res=E.pose(pp,armsP(L1,swing(R0,R1,u)),st); add(st,F|{LP},F|{LP} if i<n else allc,0)
    p=pm.copy(); nseg=6
    for k in range(1,nseg+1):
        tgt=pm+(pC-pm)*(k/nseg)
        if k<nseg: tgt,_,J=E.opt(tgt,armsP(L1,R1),allc,st,free=(1,2,3),prev=1,lam=0.05,maxiter=120,step=0.5); log('to pose A',k,tgt.round(1),round(J,3))
        p=move(p,tgt,lambda u:armsP(L1,R1),allc,allc,1,10)
    for i in range(6): add(st,F,allc,1)
    log('t',round(time.time()-t))
    # --- release: arms free, torso rises towards the squat pose
    sg={'L':1,'R':-1}
    al=float(st.q[8]); el=abs(float(st.q[10])); rl=float(st.q[9]); rr=float(st.q[19])
    arms={'L':('free',(al,rl,el)),'R':('free',(al,rr,el))}
    wp=[(pC.copy(),arms)]
    pc=pC.copy(); arm=arms
    pitch=pc[3]
    while pitch>31:
        pitch-=2.5; p0=pc.copy(); p0[3]=pitch
        # shoulder roll relaxes to zero
        arm={'L':('free',(arm['L'][1][0],arm['L'][1][1]*0.6,arm['L'][1][2])),'R':('free',(arm['R'][1][0],arm['R'][1][1]*0.6,arm['R'][1][2]))}
        pc,arm,J=E.opt(p0,arm,F,st,free=(1,2),prev=1,lam=0.02,arm_free_vars=True,maxiter=160,step=0.5); wp.append((pc.copy(),arm)); log('release pitch',round(pitch,1),pc.round(1),[round(x) for x in arm['L'][1]],round(J,3))
    z=pc[2]
    while z<STEP_H+277.5-9:
        z=min(z+9,STEP_H+277.5-9); p0=pc.copy(); p0[2]=z
        pc,arm,J=E.opt(p0,arm,F,st,free=(1,3),prev=1,lam=0.02,arm_free_vars=True,maxiter=140,step=0.5); wp.append((pc.copy(),arm)); log('rise z',round(z),pc.round(1),[round(x) for x in arm['L'][1]],round(J,3))
    # final: upright, arms down
    Rf,pAf=E.foot['L']; yst=pAf[1]+1.0
    pend=np.array([0,yst-8,STEP_H+277.5,0,0,0.]); wp.append((pend,{'L':('free',(0,0,0)),'R':('free',(0,0,0))}))
    for k in range(1,len(wp)):
        (pa,aa),(pb,ab)=wp[k-1],wp[k]; nfr=6 if k<len(wp)-1 else 18
        ph=2 if k<=3 else 3
        for i in range(1,nfr+1):
            u=i/nfr if k<len(wp)-1 else smooth(i/nfr)
            pp=pa+(pb-pa)*u
            ar={sd:('free',tuple(np.array(aa[sd][1])+(np.array(ab[sd][1])-np.array(aa[sd][1]))*u)) for sd in 'LR'}
            st,res=E.pose(pp,ar,st); add(st,F,F,ph)
    for i in range(6): add(st,F,F,3)
    log('t',round(time.time()-t))
    return out
if __name__=='__main__':
    # stand-alone test from the original frame 757 pose with palms at y=-234
    from retarget import REFS
    st0=REFS[757].st.copy()
    out=run(st0,[146,-264,PZ],[-146,-264,PZ])
    ss=[]
    for o in out:
        r=stat(o['state'],o['support'],mu=0.5); ss.append(r['s'] if r else np.nan)
    ss=np.array(ss); print(len(out),'peak',np.nanmax(ss),'at',np.nanargmax(ss),'nan',np.isnan(ss).sum())
    print(' '.join(f"{x:.2f}" for x in ss[::4]))
    pickle.dump(out,open('ending_test.pkl','wb'))
