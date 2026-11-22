"""Quasi-static multi-contact solver: minimise the highest servo utilisation (LP)."""
import numpy as np
from scipy.optimize import linprog
from emil import *
ANC=[]  # ancestors (joints) of each link incl. itself
for i in range(23):
    a=[]; j=i
    while j<22: a.append(j); j=PAR[j]
    ANC.append(a)
LINKOF={'leftFoot':7,'rightFoot':17,'leftKnee':5,'rightKnee':15,'leftPalm':10,'rightPalm':20}
SOLEP={7:np.array(SOLE['left']),17:np.array(SOLE['right'])}
NDIR=8
CONE=[(np.cos(a),np.sin(a)) for a in np.arange(NDIR)*2*np.pi/NDIR]

def surface(y,step_h=210.0):
    return step_h if y<=0 else 0.0

def contact_points(w,contacts,tol=1.5,step_h=210.0):
    """list of (link, point) force application points"""
    pts=[]
    for k,c in contacts.items():
        link=LINKOF[k]
        if 'Foot' in k:
            sp=np.array([pt(w,link,p) for p in SOLEP[link]])
            h=c[2]
            sel=sp[np.abs(sp[:,2]-h)<=tol]
            if len(sel)==0:  # toe / corner contact: lowest sole points
                sel=sp[sp[:,2]<=sp[:,2].min()+tol]
            for p in sel: pts.append((link,p,k))
        else:
            pts.append((link,np.array(c,float),k))
    return pts

def gravity_tau(w,links=LINKS,extra=None):
    """motor torque needed against gravity only; also total weight & com"""
    tau=np.zeros(22); 
    for i in range(22):
        c=pt(w,i,links[i,1:]); F=np.array([0,0,-links[i,0]*G])
        for j in ANC[i]:
            Rp,tp=w[PAR[j]]; piv=Rp@P[j]+tp; ax=Rp@AX[j]
            tau[j]-=1e-3*ax@np.cross(c-piv,F)
    return tau

def jac_rows(w,link,p):
    """A[j,k]: motor torque at joint j per unit contact force component k at point p on link"""
    A=np.zeros((22,3))
    for j in ANC[link]:
        Rp,tp=w[PAR[j]]; piv=Rp@P[j]+tp; ax=Rp@AX[j]
        r=p-piv
        # -(ax . (r x F)) = -(ax x r) . F
        A[j]=-1e-3*np.cross(ax,r)
    return A

def solve(w,contacts,mu=0.5,links=LINKS,lim=LIM,step_h=210.0,skip=(11,21),fixed=None,return_all=False,mass_scale=1.0):
    pts=contact_points(w,contacts,step_h=step_h)
    n=len(pts)
    M=links[:,0].sum()*mass_scale; c=com(w,links)
    tg=gravity_tau(w,links)*mass_scale
    # variables: per point  f = fn*z + sum_d lam_d*(mu*dir_d + z)   -> use cone generators: f = sum_d lam_d*(mu*cx,mu*cy,1)
    nv=n*NDIR+1
    gen=np.array([[mu*cx,mu*cy,1.0] for cx,cy in CONE])   # NDIR x 3
    Aeq=np.zeros((6,nv)); beq=np.zeros(6)
    for i,(link,p,k) in enumerate(pts):
        for d in range(NDIR):
            f=gen[d]; col=i*NDIR+d
            Aeq[:3,col]=f; Aeq[3:,col]=np.cross((p-c)*1e-3,f)
    beq[2]=M*G
    T=np.zeros((22,nv-1))
    for i,(link,p,k) in enumerate(pts):
        J=jac_rows(w,link,p)
        for d in range(NDIR): T[:,i*NDIR+d]=J@gen[d]
    use=[j for j in range(22) if j not in skip]
    Aub=[];bub=[]
    for j in use:
        r=np.zeros(nv); r[:-1]=T[j]/lim[j]; r[-1]=-1; Aub.append(r); bub.append(-tg[j]/lim[j])
        r=np.zeros(nv); r[:-1]=-T[j]/lim[j]; r[-1]=-1; Aub.append(r); bub.append(tg[j]/lim[j])
    cost=np.zeros(nv); cost[-1]=1
    res=linprog(cost,A_ub=np.array(Aub),b_ub=np.array(bub),A_eq=Aeq,b_eq=beq,bounds=[(0,None)]*nv,method='highs')
    if res.status!=0: return None
    x=res.x; tau=tg+T@x[:-1]
    F={}
    for i,(link,p,k) in enumerate(pts):
        f=gen.T@x[i*NDIR:(i+1)*NDIR]; F[k]=F.get(k,0)+f
    return dict(s=x[-1],tau=tau,ratio=np.abs(tau)/lim,forces=F,com=c,pts=pts,x=x)
