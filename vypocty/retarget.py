"""Retarget + optimise the original 21 cm climb: keep contact schedule and end-effector paths,
re-pose the torso (6 DOF) per frame to minimise the highest servo utilisation."""
import sys; sys.path.insert(0,'/home/claude/sim')
import numpy as np, math, json, pickle, time
from planner import *
import collide as K
from scipy.optimize import minimize
ORIG=json.load(open(W+'r9ClimbData.json'))
OP=ORIG['poses']; NO=len(OP)
C1={5:np.array([54,-24,85.0]),15:np.array([-54,-24,85.0])}; C2={5:np.array([54,-24,122.0]),15:np.array([-54,-24,122.0])}; SL_R=8.0
NAMES=['leftFoot','rightFoot','leftKnee','rightKnee','leftPalm','rightPalm']
def intervals(n):
    iv=[];on=False
    for f,p in enumerate(OP):
        c=n in p['contacts']
        if c and not on: st=f; on=True
        if not c and on: iv.append((st,f-1)); on=False
    if on: iv.append((st,NO-1))
    return iv
IV={n:intervals(n) for n in NAMES}
KNEE={'L':IV['leftKnee'][0],'R':IV['rightKnee'][0]}          # (first,last) frame of knee contact
LIFT={'L':IV['leftFoot'][0][1]+1,'R':IV['rightFoot'][0][1]+1}  # first airborne frame before kneeling
PALM_END={'L':IV['leftPalm'][-1][1],'R':IV['rightPalm'][-1][1]}
PLANT={'L':IV['leftFoot'][1][0],'R':IV['rightFoot'][1][0]}   # first frame of the foot on the tread
def leg_mode(side,i):
    k0,k1=KNEE[side]
    if i<LIFT[side]: return 'foot'
    if i<k0: return 'approach'
    if i<=k1: return 'knee'
    return 'foot'
class Ref:
    """targets taken from original frame i (optionally with palm stance offsets)"""
    def __init__(s,i):
        s.i=i; st=State.from_pose(OP[i]); s.st=st; s.q=st.q.copy()
        s.foot={sd:(st.w[FOOT[sd]][0].copy(),st.pt(FOOT[sd],refpt(sd,'A'))) for sd in 'LR'}
        s.c1={sd:st.pt(SHIN[sd],C1[SHIN[sd]]) for sd in 'LR'}
        s.shz={sd:st.vec(SHIN[sd],EZ) for sd in 'LR'}
        s.palm={sd:st.pt(ARM[sd],refpt(sd,'P')) for sd in 'LR'}
        s.contacts=set(OP[i]['contacts']); s.phase=OP[i]['phase']
        s.pel=st.pel(); s.R=st.R.copy()
REFS=[Ref(i) for i in range(NO)]

def euler(R):
    """R = Rz(yaw) Ry(roll) Rx(pitch) -> (pitch, roll, yaw) degrees"""
    roll=math.asin(-R[2,0]); pitch=math.atan2(R[2,1],R[2,2]); yaw=math.atan2(R[1,0],R[0,0])
    return np.degrees([pitch,roll,yaw])
def Reul(e): return Rz(e[2])@Ry(e[1])@Rx(e[0])

class Frame:
    """one new frame: reference + adjustments"""
    def __init__(s,src,support,palm_off=None,foot_off=None,knee_off=None):
        s.src=src; s.ref=REFS[src]; s.support=support
        s.palm_off=palm_off or {'L':np.zeros(3),'R':np.zeros(3)}
        s.foot_off=foot_off or {'L':np.zeros(3),'R':np.zeros(3)}
        s.knee_off=knee_off or {'L':np.zeros(3),'R':np.zeros(3)}
        s.foot_rot={'L':np.eye(3),'R':np.eye(3)}       # extra world rotation applied to the reference foot orientation
        s.shz={'L':None,'R':None}                       # override of the shin axis target during approach
        s.q_off=np.zeros(22)                            # offsets added to posture references

FREE_J=np.zeros(28,bool); FREE_J[6:]=True
def limb_ik(st,fr,qprev=None,arm_free=None,iters=20,both=False):
    """solve all limbs for the current torso pose of `st` (root fixed).
    returns max residual (mm) of contact end effectors (+ swing ones if both=True)"""
    r=fr.ref; i=fr.src; tasks=[]; qref=r.q+fr.q_off; wq=np.full(22,0.03); wq[[0,1,11,21]]=5.0; checks=[]
    for sd in 'LR':
        o=0 if sd=='L' else 10; mode=leg_mode(sd,i)
        if mode=='foot':
            Rf,pA=r.foot[sd]; pA=pA+fr.foot_off[sd]; Rf=fr.foot_rot[sd]@Rf; f=FOOT[sd]
            ww=1.0; k1=KNEE[sd][1]; land=PLANT[sd]
            if k1<i<land: ww=smooth(min(1.0,max(0.0,(i-(k1+0.3*(land-k1)))/(0.45*(land-k1)))))
            tasks.append(T_point(f,refpt(sd,'A'),pA,3+97*ww)); tasks.append(T_dir(f,EZ,Rf@EZ,1.5+48.5*ww)); tasks.append(T_dir(f,EY,Rf@EY,1.5+48.5*ww))
            if ww>=1: checks.append((f,refpt(sd,'A'),pA,('leftFoot' if sd=='L' else 'rightFoot') in r.contacts))
            if ww<1: wq[[2+o,3+o,4+o,5+o,6+o,7+o]]=0.3*(1-ww)+0.03
        else:
            k=SHIN[sd]; c=r.c1[sd]+fr.knee_off[sd]
            if mode=='approach':
                # early swing: the leg keeps its original joint angles (moves with the new torso);
                # only towards touchdown it is steered to the world landing point
                k0=KNEE[sd][0]; ww=smooth(min(1.0,max(0.0,(i-(k0-45))/30.0)))
                tasks.append(T_point(k,C1[k],c,3+97*ww)); tasks.append(T_dir(k,EZ,fr.shz[sd] if fr.shz[sd] is not None else r.shz[sd],1+19*ww))
                if ww>=1: checks.append((k,C1[k],c,False))
                wq[[2+o,3+o,4+o,5+o]]=0.3*(1-ww)+0.02
            else:
                tasks.append(T_point(k,C1[k],c,100)); checks.append((k,C1[k],c,True))
                wq[[2+o,3+o,4+o,5+o]]=0.02
            wq[[6+o,7+o]]=1.0     # hanging foot keeps the original ankle angles
        if i<=PALM_END[sd]:
            a=ARM[sd]; pp=r.palm[sd]+fr.palm_off[sd]
            tasks.append(T_point(a,refpt(sd,'P'),pp,100)); checks.append((a,refpt(sd,'P'),pp,('leftPalm' if sd=='L' else 'rightPalm') in r.contacts))
            wq[[8+o,9+o,10+o]]=0.01
        else:
            wq[[8+o,9+o,10+o]]=1.0
            if arm_free is not None: qref[[8+o,9+o,10+o]]=arm_free[sd]
    solve_ik(st,tasks,qref=qref,wq=wq,qlo=QLO,qhi=QHI,iters=iters,free=FREE_J,tol=2e-5)
    rc=0.0; rs_=0.0
    for l,pl,pw,con in checks:
        e=np.abs(st.pt(l,pl)-pw).max()
        if con: rc=max(rc,e)
        else: rs_=max(rs_,e)
    return (rc,rs_) if both else max(rc,rs_)

def knee_patch(st,name):
    k=LINKOF[name]; a=st.pt(k,C1[k]); b=st.pt(k,C2[k]); out=[]
    zmin=min(a[2],b[2])
    for c in (a,b):
        if c[2]<=zmin+1.0 and abs(c[2]-SL_R-STEP_H)<=1.5: out.append(c-np.array([0,0,SL_R]))
    return out
def support_pts(st,support):
    names=[];extra=[]
    for n in support:
        if 'Knee' in n: extra+=[(LINKOF[n],p,n) for p in knee_patch(st,n)]
        else: names.append(n)
    return names,extra
def stat(st,support,mu=0.5,mass_scale=1.0):
    names,extra=support_pts(st,support)
    return statics(st,names,extra_pts=extra,mu=mu,mass_scale=mass_scale)

# environment clearance: everything except functional contact geometry
SLEEVE_ITEMS=None
def env_clear(st,fr,cutoff=12.0):
    ex=set()
    for sd in 'LR':
        if leg_mode(sd,fr.src)=='foot':
            if ('leftFoot' if sd=='L' else 'rightFoot') in fr.ref.contacts: ex.add((FOOT[sd],'body'))
    return K.env_dist(st,exclude=ex,cutoff=cutoff,placed=True)
