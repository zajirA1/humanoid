"""Contact geometry + minimax statics on a State (realistic patches: sole polygon, sleeve bar, palm sphere)."""
import numpy as np
from scipy.optimize import linprog
from wbik import *
from statics import ANC, SOLEP, CONE, NDIR
STEP_H=210.0
SLEEVE={5:[np.array([54+dx,-32.0,z]) for z in (82.0,122.0) for dx in (-6.0,6.0)],
        15:[np.array([-54+dx,-32.0,z]) for z in (82.0,122.0) for dx in (-6.0,6.0)]}
SLEEVE_MID={5:np.array([54,-32.0,102.0]),15:np.array([-54,-32.0,102.0])}
PADC={10:np.array([146,-12,205.0]),20:np.array([-146,-12,205.0])}; PAD_R=12.0
LINKOF={'leftFoot':7,'rightFoot':17,'leftKnee':5,'rightKnee':15,'leftPalm':10,'rightPalm':20}
def surf(y): return STEP_H if y<=0 else 0.0

def patch(s,name,tol=1.0,h=None):
    """world points where contact `name` can transmit force (empty list = not touching)"""
    link=LINKOF[name]
    if 'Foot' in name:
        sp=np.array([s.pt(link,p) for p in SOLEP[link]])
        if h is None: h=surf(sp[:,1].mean())
        return [p for p in sp if abs(p[2]-h)<=tol and (h==0.0 or p[1]<=0.5)]
    if 'Knee' in name:
        pts=[s.pt(link,p) for p in SLEEVE[link]]; zmin=min(p[2] for p in pts)
        return [p for p in pts if p[2]<=zmin+tol and abs(zmin-STEP_H)<=tol and p[1]<=0.5]
    c=s.pt(link,PADC[link]); p=c-np.array([0,0,PAD_R])
    return [p] if abs(p[2]-STEP_H)<=tol and p[1]<=0.5 else []

def grav_tau(s):
    tau=np.zeros(22)
    for i in range(22):
        c=s.pt(i,LINKS[i,1:]); F=np.array([0,0,-MASS[i]*G])
        for j in ANC[i]: tau[j]-=1e-3*s.ax[j]@np.cross(c-s.piv[j],F)
    return tau

def statics(s,names,mu=0.5,lim=LIM,skip=(11,21),mass_scale=1.0,extra_pts=None,weights=None,payload=None):
    """min-max utilisation.  names: contacts assumed active.  Returns None if no equilibrium."""
    pts=[]
    for n in names:
        for p in patch(s,n): pts.append((LINKOF[n],p,n))
    if extra_pts: pts+=extra_pts
    if not pts: return None
    n=len(pts); c=s.com(); M=MTOT*mass_scale; tg=grav_tau(s)*mass_scale
    gen=np.array([[mu*cx,mu*cy,1.0] for cx,cy in CONE]); nv=n*NDIR+1
    Aeq=np.zeros((6,nv)); T=np.zeros((22,nv-1))
    for i,(link,p,k) in enumerate(pts):
        for j in ANC[link]:
            a=-1e-3*np.cross(s.ax[j],p-s.piv[j])
            T[j,i*NDIR:(i+1)*NDIR]=gen@a
        Aeq[:3,i*NDIR:(i+1)*NDIR]=gen.T
        Aeq[3:,i*NDIR:(i+1)*NDIR]=np.cross((p-c)*1e-3,gen).T
    beq=np.zeros(6); beq[2]=M*G
    use=[j for j in range(22) if j not in skip]
    A=T[use]/lim[use,None]; b=tg[use]/lim[use]
    Aub=np.block([[A,-np.ones((len(use),1))],[-A,-np.ones((len(use),1))]]); bub=np.concatenate([-b,b])
    cost=np.zeros(nv); cost[-1]=1
    res=linprog(cost,A_ub=Aub,b_ub=bub,A_eq=Aeq,b_eq=beq,bounds=[(0,None)]*nv,method='highs')
    if res.status!=0: return None
    x=res.x; tau=tg+T@x[:-1]; F={}
    for i,(link,p,k) in enumerate(pts):
        F[k]=F.get(k,0)+gen.T@x[i*NDIR:(i+1)*NDIR]
    ratio=np.abs(tau)/lim; ratio[list(skip)]=0
    ptf=[(link,p,gen.T@x[i*NDIR:(i+1)*NDIR],k) for i,(link,p,k) in enumerate(pts)]
    return dict(s=float(ratio.max()),jmax=int(ratio.argmax()),tau=tau,ratio=ratio,forces=F,com=c,npts=n,ptf=ptf)

def joint_wrenches(st,res,mass_scale=1.0):
    """wrench transmitted through each joint (child subtree -> parent), resolved at the pivot.
    returns arrays: tau_axis (N*m, motor), bend (N*m, off-axis moment carried by the bearings/fork),
    axial (N, along the axis), radial (N)"""
    F=np.zeros((22,3)); M=np.zeros((22,3))
    def add(link,p,f):
        for j in ANC[link]: F[j]+=f; M[j]+=1e-3*np.cross(p-st.piv[j],f)
    for i in range(22): add(i,st.pt(i,LINKS[i,1:]),np.array([0,0,-MASS[i]*G*mass_scale]))
    for link,p,f,k in res['ptf']: add(link,p,f)
    tau=np.einsum('ij,ij->i',M,st.ax); bend=np.linalg.norm(M-tau[:,None]*st.ax,axis=1)
    axial=np.einsum('ij,ij->i',F,st.ax); radial=np.linalg.norm(F-axial[:,None]*st.ax,axis=1)
    return tau,bend,axial,radial
