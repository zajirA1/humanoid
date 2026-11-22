"""Fork (joint support) analysis: measured cheek geometry + reaction loads carried by the two-sided support."""
import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
from geom import ITEMS
FR={2:'r12_L_hip_yaw_ram',3:'r11_ST3250_L_hip_roll_ram',4:'r12_L_hip_pitch_ram',5:'r12_L_knee_ram',6:'r11_ST3250_L_ankle_pitch_ram',7:'r12_L_ankle_roll_ram',8:'r11_clear_L_shoulder_pitch_ram',9:'r11_clear_L_shoulder_roll_ram',10:'r8_L_elbow_ram'}
def geometry():
    out={}
    for L,key in FR.items():
        it=[i for i in ITEMS if i['key']==key and i['link']==L][0]; v=it['v']; a=AX[L]/np.linalg.norm(AX[L]); p=P[L]
        d=v-p; u=d@a; perp=d-np.outer(u,a); rad=np.linalg.norm(perp,axis=1)
        near=rad<13; us=np.sort(u[near]); 
        neg=us[us<0]; pos=us[us>0]
        if len(neg)==0 or len(pos)==0: out[L]=None; continue
        tn=neg.max()-neg.min(); tp=pos.max()-pos.min(); gap=pos.min()-neg.max()
        # bridge: material between the cheeks (|u| < gap/2 - 2), closest approach to the axis
        mid=(u>neg.max()+2)&(u<pos.min()-2)
        Lb=float(rad[mid].min()) if mid.any() else None
        # cheek width: extent of cheek vertices across the cheek near the axis
        ch=(np.abs(u)>=min(abs(neg.max()),pos.min())-0.5)&(rad<Lb+2 if Lb else rad<30)
        w=float(2*np.percentile(rad[near],95))
        out[L]=dict(t=(float(tn),float(tp)),gap=float(gap),span=float((pos.min()+pos.max())/2-(neg.min()+neg.max())/2),bridge=Lb,width=w)
    return out
def loads(recs,rows):
    n=len(recs); bend=np.zeros((n,22)); ax=np.zeros((n,22)); rad=np.zeros((n,22))
    for i,(rec,row) in enumerate(zip(recs,rows)):
        r=row['r']
        if r is None: continue
        t,b,a,rr=joint_wrenches(rec['state'],r); bend[i]=b; ax[i]=np.abs(a); rad[i]=rr
    return bend,ax,rad
E_PETG=2000.0   # MPa, printed PETG, in-plane; conservative
def cheek_deflection(F,L,t,w):
    I=w*t**3/12; return F*L**3/(3*E_PETG*I)
if __name__=='__main__':
    g=geometry()
    for L,v in g.items(): print(L,JN[L],v)
