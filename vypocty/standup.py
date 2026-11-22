import sys; sys.path.insert(0,'/home/claude/sim')
from opt import *
i0=800; r0=REFS[i0]
footL=r0.foot['L']; footR=r0.foot['R']
print('feet A',footL[1],footR[1],'palms',r0.palm)
def pose(z,y,pitch,alpha,elb,st_init,palms=None):
    st=st_init.copy(); R=Rx(pitch); pel=np.array([0,y,z]); st.R=R; st.t=pel-R@PEL; st.update()
    tasks=[]; qref=np.zeros(22); wq=np.full(22,0.03); wq[[0,1,11,21]]=5
    for sd,(Rf,pA) in (('L',footL),('R',footR)):
        f=FOOT[sd]; tasks+=[T_point(f,refpt(sd,'A'),pA,100),T_dir(f,EZ,EZ,50),T_dir(f,EY,EY,50)]
    if palms is None:
        qref[8]=alpha; qref[18]=-alpha; qref[10]=-elb; qref[20]=elb; wq[[8,9,10,18,19,20]]=2.0
    else:
        for sd in 'LR': tasks.append(T_point(ARM[sd],refpt(sd,'P'),palms[sd],100)); 
        wq[[8,9,10,18,19,20]]=0.01
    solve_ik(st,tasks,qref=qref,wq=wq,qlo=QLO,qhi=QHI,iters=30,free=FREE_J,tol=2e-5)
    res=max(np.abs(st.pt(FOOT[sd],refpt(sd,'A'))-pA).max() for sd,(Rf,pA) in (('L',footL),('R',footR)))
    if palms is not None: res=max(res,max(np.abs(st.pt(ARM[sd],refpt(sd,'P'))-palms[sd]).max() for sd in 'LR'))
    return st,res
SUP={'leftFoot','rightFoot'}
def cost(z,x,st_init,palms=None,full=False):
    y,pitch,alpha,elb=x[0]*10,x[1]*5,x[2]*10,abs(x[3])*10 if len(x)>3 else 10
    st,res=pose(z,y,pitch,alpha,elb,st_init,palms)
    r=stat(st,SUP,mu=0.4); m=margin(st,SUP)
    J=(r['s'] if r else 3+max(0,-m)/50)+0.1*max(0,res-0.2)+0.004*max(0,15-m)**2
    if full: return J,st,r,m,res
    return J
if __name__=='__main__':
    st_init=r0.st
    zs=list(range(350,489,10))+[488]; out=[]
    x=np.array([-9.0,10,0,1])
    for z in zs:
        best=None
        for x0 in ([-9,10,0,1],list(x)):
            sim=np.vstack([x0]+[np.array(x0)+np.eye(4)[k] for k in range(4)])
            rs=minimize(lambda v:cost(z,v,st_init),np.array(x0,float),method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.001,maxiter=160,initial_simplex=sim))
            if best is None or rs.fun<best.fun: best=rs
        x=best.x; J,st,r,m,res=cost(z,x,st_init,full=True)
        print(z,'J',round(J,3),'s',round(r['s'],3) if r else None,JN[r['jmax']] if r else '','y',round(x[0]*10),'pitch',round(x[1]*5),'alpha',round(x[2]*10),'elb',round(abs(x[3])*10),'m',round(m),'res',round(res,2),'knee',round(st.q[5]),'hip',round(-st.q[4]),'ank',round(st.q[6]))
