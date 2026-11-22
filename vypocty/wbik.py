"""Whole-body inverse kinematics for Emil (floating base + 22 joints), analytic Jacobians."""
import numpy as np, math
from emil import *
from statics import ANC
PEL=np.array([0,1,278.0])          # pelvis reference point in rest coords
MASS=LINKS[:,0]; MTOT=MASS.sum()
DEG=math.pi/180

def expm(w):
    th=np.linalg.norm(w)
    if th<1e-12: return np.eye(3)
    k=w/th; K=np.array([[0,-k[2],k[1]],[k[2],0,-k[0]],[-k[1],k[0],0]])
    return np.eye(3)+math.sin(th)*K+(1-math.cos(th))*K@K

class State:
    __slots__=('R','t','q','w','piv','ax')
    def __init__(s,R,t,q):
        s.R=np.array(R,float); s.t=np.array(t,float); s.q=np.array(q,float); s.update()
    @staticmethod
    def from_pose(p):
        R,t=rt2T(p['rt']); return State(R,t,p['q'])
    def copy(s): return State(s.R,s.t,s.q)
    def update(s):
        w=[None]*23; w[22]=(s.R,s.t); piv=np.zeros((22,3)); ax=np.zeros((22,3))
        for i in range(22):
            Rp,tp=w[PAR[i]]; R,t=rot(AX[i],s.q[i],P[i]); w[i]=(Rp@R,Rp@t+tp)
            piv[i]=Rp@P[i]+tp; ax[i]=Rp@AX[i]
        s.w=w; s.piv=piv; s.ax=ax
    def rt(s): return list(s.R.T.reshape(-1))+list(s.t)
    def pose(s,**kw): return dict(q=[round(float(v),6) for v in s.q],rt=[round(float(v),9) for v in s.rt()],**kw)
    def pt(s,link,p): R,t=s.w[link]; return R@np.asarray(p,float)+t
    def vec(s,link,d): return s.w[link][0]@np.asarray(d,float)
    def pel(s): return s.R@PEL+s.t
    def com(s):
        c=np.zeros(3)
        for i in range(23): c+=MASS[i]*s.pt(i,LINKS[i,1:])
        return c/MTOT
    # Jacobians: columns = [root trans(3), root rot(3, about pelvis point), joints(22, radians)]
    def Jpt(s,link,pw):
        J=np.zeros((3,28)); J[:,:3]=np.eye(3)
        r=pw-s.pel(); J[:,3:6]=-np.array([[0,-r[2],r[1]],[r[2],0,-r[0]],[-r[1],r[0],0]])
        for j in ANC[link]: J[:,6+j]=np.cross(s.ax[j],pw-s.piv[j])
        return J
    def Jvec(s,link,dw):
        J=np.zeros((3,28))
        J[:,3:6]=-np.array([[0,-dw[2],dw[1]],[dw[2],0,-dw[0]],[-dw[1],dw[0],0]])
        for j in ANC[link]: J[:,6+j]=np.cross(s.ax[j],dw)
        return J
    def Jcom(s):
        J=np.zeros((3,28))
        for i in range(23): J+=MASS[i]*s.Jpt(i,s.pt(i,LINKS[i,1:]))
        return J/MTOT
    def step(s,dx):
        c=s.pel(); Rn=expm(dx[3:6])@s.R
        s.t=c+dx[:3]-Rn@PEL; s.R=Rn; s.q=s.q+dx[6:]/DEG; s.update()
    def pitch(s):   # torso forward lean about world x (deg); positive = leaning forward (-y)
        up=s.R@np.array([0,0,1.0]); return math.degrees(math.atan2(-up[1],up[2]))

def solve_ik(s,tasks,qref=None,wq=None,qlo=None,qhi=None,iters=40,tol=1e-4,lam=1e-6,free=None):
    """tasks: list of callables task(state)->(residual vector, Jacobian) already weighted.
    Minimises sum |r|^2 + posture term.  free: boolean mask (28) of variables allowed to move."""
    if free is None: free=np.ones(28,bool)
    for it in range(iters):
        rs=[];Js=[]
        for tk in tasks:
            r,J=tk(s); rs.append(np.atleast_1d(r)); Js.append(np.atleast_2d(J))
        if qref is not None:
            Jq=np.zeros((22,28)); Jq[:,6:]=np.diag(wq/DEG); rs.append(wq*(s.q-qref)); Js.append(Jq)
        r=np.concatenate(rs); J=np.vstack(Js)[:,free]
        H=J.T@J+lam*np.eye(J.shape[1]); g=J.T@r
        dx=np.zeros(28); dx[free]=-np.linalg.solve(H,g)
        # step limiting
        m=max(np.abs(dx[:3]).max()/25.0, np.abs(dx[3:]).max()/0.25, 1.0); dx/=m
        s.step(dx)
        if qlo is not None: 
            qc=np.clip(s.q,qlo,qhi)
            if np.any(qc!=s.q): s.q=qc; s.update()
        if np.abs(dx).max()<tol and m==1.0: break
    return s

# ---- task factories (w = weight) ----
def T_point(link,plocal,target,w=1.0,axes=(0,1,2)):
    plocal=np.asarray(plocal,float); target=np.asarray(target,float); axes=list(axes)
    def f(s):
        pw=s.pt(link,plocal); return w*(pw-target)[axes], w*s.Jpt(link,pw)[axes]
    return f
def T_dir(link,dlocal,target,w=1.0,axes=(0,1,2)):
    """align link direction (unit) with world target direction; residual in mm-equivalent: scale 100"""
    dlocal=np.asarray(dlocal,float); target=np.asarray(target,float); axes=list(axes)
    def f(s):
        dw=s.vec(link,dlocal); return 100*w*(dw-target)[axes], 100*w*s.Jvec(link,dw)[axes]
    return f
def T_com(target,w=1.0,axes=(0,1)):
    target=np.asarray(target,float); axes=list(axes)
    def f(s):
        return w*(s.com()[axes]-target), w*s.Jcom()[axes]
    return f
def T_pel(target,w=1.0,axes=(0,1,2)):
    target=np.asarray(target,float); axes=list(axes)
    def f(s):
        J=np.zeros((3,28)); J[:,:3]=np.eye(3); return w*(s.pel()[axes]-target), w*J[axes]
    return f
def T_torso(Rtarget,w=1.0):
    """orientation error of the torso (rotation vector, scaled by 100 mm/rad)"""
    def f(s):
        E=Rtarget@s.R.T; 
        v=0.5*np.array([E[2,1]-E[1,2],E[0,2]-E[2,0],E[1,0]-E[0,1]])
        J=np.zeros((3,28)); J[:,3:6]=np.eye(3)
        return -100*w*v, 100*w*J
    return f
def Rx(deg): 
    a=deg*DEG; c,s_=math.cos(a),math.sin(a); return np.array([[1,0,0],[0,c,-s_],[0,s_,c]])
def Ry(deg):
    a=deg*DEG; c,s_=math.cos(a),math.sin(a); return np.array([[c,0,s_],[0,1,0],[-s_,0,c]])
def Rz(deg):
    a=deg*DEG; c,s_=math.cos(a),math.sin(a); return np.array([[c,-s_,0],[s_,c,0],[0,0,1]])
