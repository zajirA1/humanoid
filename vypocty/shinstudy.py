import sys; sys.path.insert(0,'/home/claude/sim')
from run_retarget import *
import retarget as RT
sup={'leftKnee','leftPalm','rightPalm'}
def limb_ik_shin(st,fr,da):
    # same as limb_ik but with an explicit left-shin pitch target (orig pitch + da degrees)
    r=fr.ref; z=r.shz['L']; a=math.degrees(math.atan2(-z[1],z[2]))+da; tgt=Rx(a)@EZ
    base=RT.limb_ik
    return base(st,fr),tgt
def evaluate7(fr,v,st_init):
    st=make_state(fr,v[:6],st_init)
    r=fr.ref; z=r.shz['L']; a=math.degrees(math.atan2(-z[1],z[2]))+v[6]*5; tgt=Rx(a)@EZ
    old=r.shz['L']; r.shz['L']=tgt
    # force shin pitch tracking in knee mode by temporarily treating as approach
    k0=RT.KNEE['L']; RT.KNEE['L']=(10**6,10**6)
    try: res=limb_ik(st,fr)
    finally: RT.KNEE['L']=k0; r.shz['L']=old
    rr=stat(st,fr.support,mu=0.4); env,el=env_fast(st,fr); m=margin(st,fr.support)
    J=(rr['s'] if rr else 3.0+max(0,-m)/50.0)+0.02*max(0,6-env)**2+0.1*max(0,res-0.2)+0.004*max(0,12-m)**2
    return J,rr,res,m,env,st
for i in (247,256):
    fr=Frame(i,sup); st0=REFS[i].st; best=None
    for v0 in (np.array([4,0,0.5,0,0,0,0.]),np.array([3,-1,2,1,-1,-2,-2.]),np.array([3,-1,2,1,-1,-2,2.])):
        sim=np.vstack([v0]+[v0+0.8*np.eye(7)[k] for k in range(7)])
        rs=minimize(lambda v:evaluate7(fr,v,st0)[0],v0,method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.001,maxiter=320,initial_simplex=sim))
        if best is None or rs.fun<best.fun: best=rs
    J,rr,res,m,env,st=evaluate7(fr,best.x,st0)
    print(i,'J',round(J,3),'s',round(rr['s'],3),JN[rr['jmax']],'res',round(res,2),'m',round(m),'env',round(env,1),'v',(best.x[:6]*SC).round(0),'dshin',round(best.x[6]*5,1),'knee',round(st.q[5]),flush=True)
