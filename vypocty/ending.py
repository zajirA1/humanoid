"""Custom ending: hands closer to the feet, weight onto the feet, release, squat-rise. Symmetric torso."""
import sys; sys.path.insert(0,'/home/claude/sim')
from opt import *
PZ=STEP_H+PAD_R
class Ending:
    def __init__(s,st0,palmL,palmR):
        s.st0=st0.copy()
        s.foot={sd:(st0.w[FOOT[sd]][0].copy(),st0.pt(FOOT[sd],refpt(sd,'A'))) for sd in 'LR'}
        s.palm0={'L':np.array(palmL,float),'R':np.array(palmR,float)}
    def pose(s,p,arms,st_init,iters=30):
        """p=(x,y,z,pitch,roll,yaw); arms={'L':('palm',xyz)|('free',(alpha,roll,elb)), 'R':...} alpha<0 = arm forward"""
        st=st_init.copy(); R=Rz(p[5])@Ry(p[4])@Rx(p[3]); pel=np.array(p[:3],float); st.R=R; st.t=pel-R@PEL; st.update()
        tasks=[]; qref=np.zeros(22); wq=np.full(22,0.03); wq[[0,1,11,21]]=5; chk=[]
        for sd in 'LR':
            Rf,pA=s.foot[sd]; f=FOOT[sd]; o=0 if sd=='L' else 10; sg=1 if sd=='L' else -1
            tasks+=[T_point(f,refpt(sd,'A'),pA,100),T_dir(f,EZ,Rf@EZ,50),T_dir(f,EY,Rf@EY,50)]; chk.append((f,refpt(sd,'A'),pA))
            kind,val=arms[sd]
            if kind=='palm':
                tasks.append(T_point(ARM[sd],refpt(sd,'P'),val,100)); wq[[8+o,9+o,10+o]]=0.01; chk.append((ARM[sd],refpt(sd,'P'),np.array(val,float)))
            else:
                a,rl,e=val; qref[8+o]=sg*a; qref[9+o]=rl; qref[10+o]=-sg*abs(e); wq[[8+o,9+o,10+o]]=3.0
        qlo=QLO.copy(); qhi=QHI.copy()
        if arms['L'][0]=='palm': qhi[10]=-4.0; st.q[10]=min(st.q[10],-6.0)
        if arms['R'][0]=='palm': qlo[20]=4.0; st.q[20]=max(st.q[20],6.0)
        st.update()
        solve_ik(st,tasks,qref=qref,wq=wq,qlo=qlo,qhi=qhi,iters=iters,free=FREE_J,tol=2e-5)
        res=max(np.abs(st.pt(l,pl)-pw).max() for l,pl,pw in chk)
        return st,res
    def cost(s,p,arms,support,st_init,full=False,mu=0.4,mmin=15):
        st,res=s.pose(p,arms,st_init); r=stat(st,support,mu=mu); m=margin(st,support)
        J=(r['s'] if r else 3+max(0,-m)/50)+0.5*max(0,res-0.15)+0.004*max(0,mmin-m)**2
        # keep 2.5 deg away from the knee / hip flexion limits
        lim=max(0,abs(st.q[5])-124.5)+max(0,abs(st.q[15])-124.5)+max(0,abs(st.q[4])-118.5)+max(0,abs(st.q[14])-118.5)
        J+=0.05*lim
        for sd,o in (('L',0),('R',10)):
            if arms[sd][0]=='palm': J+=0.02*max(0,5.0-abs(st.q[10+o]))
        if full: return dict(J=J,st=st,r=r,m=m,res=res)
        return J
    def opt(s,p0,arms,support,st_init,free=(1,2,3),prev=None,lam=0.0,arm_free_vars=False,maxiter=220,step=None):
        """optimise selected torso params (indices into p) and optionally symmetric (alpha,elb)"""
        p0=np.array(p0,float); sc=np.array([10,10,10,5,4,4.0]); idx=list(free)
        a0=None
        if arm_free_vars: a0=np.array([arms['L'][1][0]/10.0,arms['L'][1][2]/10.0])
        def unpack(v):
            p=p0.copy(); p[idx]=p0[idx]+v[:len(idx)]*sc[idx]; ar=arms
            if arm_free_vars:
                al,el=(a0+v[len(idx):])*10; ar={'L':('free',(al,arms['L'][1][1],abs(el))),'R':('free',(al,arms['R'][1][1],abs(el)))}
            return p,ar
        def f(v):
            p,ar=unpack(v); J=s.cost(p,ar,support,st_init)
            if prev is not None: J+=lam*float(v@v)
            return J
        n=len(idx)+(2 if arm_free_vars else 0); v0=np.zeros(n); stp=step or 0.8
        sim=np.vstack([v0]+[v0+stp*np.eye(n)[k] for k in range(n)])
        rs=minimize(f,v0,method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.0005,maxiter=maxiter,initial_simplex=sim))
        p,ar=unpack(rs.x); return p,ar,rs.fun
def params_of(st):
    e=euler(st.R); pel=st.pel(); return np.array([pel[0],pel[1],pel[2],e[0],e[1],e[2]])
