"""Keyframe planner for the 21 cm climb: segments -> per-frame whole-body IK -> poses."""
import numpy as np, math, copy
from contact import *
HZ=6
EZ=np.array([0,0,1.0]); EY=np.array([0,1.0,0])
FOOT={'L':7,'R':17}; SHIN={'L':5,'R':15}; ARM={'L':10,'R':20}
SGN={'L':1,'R':-1}
def refpt(side,ref):
    s=SGN[side]
    return {'A':np.array([s*54,0,0.]),'T':np.array([s*54,-70,0.]),'H':np.array([s*54,50,0.]),
            'S':np.array([s*54,-32,102.]),'S1':np.array([s*54,-32,82.]),'S2':np.array([s*54,-32,122.]),
            'P':np.array([s*146,-12,205.])}[ref]
# joint limits in "left convention" [lo,hi]; mirrored for right
LIM_L={2:(-23,23),3:(-25,25),4:(-121,6),5:(-14,127),6:(-60.5,43.5),7:(-19,19),8:(-70,20),9:(-22,3),10:(-100,0)}
QLO=np.full(22,-1e9); QHI=np.full(22,1e9)
_L={2:(-23,23),3:(-25.5,25.5),4:(-121,6),5:(-14,127),6:(-60.5,43.5),7:(-19,19),8:(-70,20),9:(-22,22),10:(-100,0)}
for j,(lo,hi) in _L.items():
    QLO[j]=lo; QHI[j]=hi
    if j in (2,3,7,9): QLO[j+10]=lo; QHI[j+10]=hi      # same axis direction both sides
    else: QLO[j+10]=-hi; QHI[j+10]=-lo                 # mirrored axis
QLO[[0,1,11,21]]=0; QHI[[0,1,11,21]]=0; QHI[1]=4
QHI[2]=5.0; QLO[12]=-6.0     # keeps the two hip-yaw frames >= 10 mm apart
QLO[5]=0.5; QHI[15]=-0.5      # no knee hyper-extension: one IK branch only
QHI[10]=-2.0; QLO[20]=2.0     # elbows never fully straight (IK singularity)

def smooth(u): return u*u*(3-2*u)

class Plan:
    def __init__(s,state):
        s.st=state.copy(); s.segs=[]; s.cur={}
    def seg(s,dur,name=None,support=None,**targets):
        s.segs.append(dict(dur=dur,name=name,support=support,targets=targets))
    def run(s,verbose=False):
        st=s.st.copy(); frames=[]; cur={}   # cur: channel -> current target value (np array / float / dict)
        phase=-1; phases=[]; support=set(); leg={'L':'foot','R':'foot'}; fref={'L':'A','R':'A'}
        qref=st.q.copy(); wq=np.full(22,0.03); wq[[0,1,11,21]]=5
        wq[[2,12]]=0.3   # keep hip yaw near zero
        for sg in s.segs:
            if sg['name'] is not None: phase+=1; phases.append(sg['name'])
            if sg['support'] is not None: support=set(sg['support'])
            tg=sg['targets']; start={}; end={}
            # mode switches
            for side in 'LR':
                if 'leg'+side in tg: leg[side]=tg['leg'+side]
                if 'fref'+side in tg: fref[side]=tg['fref'+side]
            # capture start values from the actual state for every channel (keeps continuity)
            act=s.actual(st,leg,fref)
            for ch,val in tg.items():
                if ch.startswith('leg') or ch.startswith('fref'): continue
                a=cur.get(ch,act.get(ch))
                if ch in ('foot'+c for c in 'LR') or ch in ('knee'+c for c in 'LR') or ch in ('palm'+c for c in 'LR'):
                    a=act[ch] if ch not in cur or cur[ch] is None else cur[ch]
                start[ch]=np.array(a,float) if a is not None else None
                end[ch]=None if val is None else np.array(val,float)
            n=max(1,int(round(sg['dur']*HZ)))
            for i in range(1,n+1):
                u=smooth(i/n)
                for ch in end:
                    if end[ch] is None: cur[ch]=None
                    elif start[ch] is None: cur[ch]=end[ch]
                    else: cur[ch]=start[ch]+(end[ch]-start[ch])*u
                # invalidate inactive leg channels
                for side in 'LR':
                    if leg[side]=='foot': cur['knee'+side]=None
                    else: cur['foot'+side]=None
                s.ik(st,cur,leg,fref,support,qref,wq)
                frames.append(dict(state=st.copy(),phase=phase,support=set(support),cur=copy.deepcopy(cur),seg=len(frames)))
            if verbose: print(sg['name'],len(frames))
        s.frames=frames; s.phases=phases
        return frames
    @staticmethod
    def actual(st,leg,fref):
        a={}
        for side in 'LR':
            f=FOOT[side]; p=st.pt(f,refpt(side,fref[side])); y=st.vec(f,EY); phi=math.degrees(math.atan2(y[2],y[1]))
            a['foot'+side]=np.array([p[0],p[1],p[2],phi])
            k=SHIN[side]; p=st.pt(k,refpt(side,'S')); z=st.vec(k,EZ); ang=math.degrees(math.atan2(-z[1],z[2]))
            a['knee'+side]=np.array([p[0],p[1],p[2],ang])
            a['palm'+side]=st.pt(ARM[side],refpt(side,'P'))
        c=st.com(); a['com']=c[:2].copy(); a['pitch']=np.array(st.pitch()); a['pelz']=np.array(st.pel()[2]); a['pely']=np.array(st.pel()[1]); a['pelx']=np.array(st.pel()[0])
        a['roll']=np.array(0.0); a['yaw']=np.array(0.0)
        for j in range(22): a['q%d'%j]=np.array(st.q[j])
        return a
    def ik(s,st,cur,leg,fref,support,qref,wq):
        tasks=[]; qr=qref.copy(); w=wq.copy()
        for side in 'LR':
            if leg[side]=='foot' and cur.get('foot'+side) is not None:
                x,y,z,phi=cur['foot'+side]; f=FOOT[side]; R=Rx(phi)
                hard=200 
                tasks.append(T_point(f,refpt(side,fref[side]),[x,y,z],hard))
                tasks.append(T_dir(f,EZ,R@EZ,hard*0.5)); tasks.append(T_dir(f,EY,R@EY,hard*0.5,axes=(0,)))
            if leg[side]=='knee' and cur.get('knee'+side) is not None:
                x,y,z,ang=cur['knee'+side]; k=SHIN[side]; R=Rx(ang)
                tasks.append(T_point(k,refpt(side,'S'),[x,y,z],200))
                tasks.append(T_dir(k,EZ,R@EZ,100)); tasks.append(T_dir(k,EY,R@EY,100,axes=(0,)))
            if cur.get('palm'+side) is not None:
                tasks.append(T_point(ARM[side],refpt(side,'P'),cur['palm'+side],200))
        if cur.get('com') is not None: tasks.append(T_com(cur['com'],cur.get('wcom',8.0)))
        pitch=float(cur['pitch']) if cur.get('pitch') is not None else None
        if pitch is not None:
            Rt=Rz(float(cur.get('yaw',0) or 0))@Ry(float(cur.get('roll',0) or 0))@Rx(pitch)
            tasks.append(T_torso(Rt,float(cur.get('wpitch',3.0))))
        for ch,ax in (('pelx',0),('pely',1),('pelz',2)):
            if cur.get(ch) is not None: tasks.append(T_pel([float(cur[ch])],float(cur.get('w'+ch,2.0)),axes=(ax,)))
        for j in range(22):
            v=cur.get('q%d'%j)
            if v is not None: qr[j]=float(v); w[j]=max(w[j],float(cur.get('wq%d'%j,1.0)))
        solve_ik(st,tasks,qref=qr,wq=w,qlo=QLO,qhi=QHI,iters=30)
