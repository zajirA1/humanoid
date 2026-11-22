import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
LEGJ={'L':[2,3,4,5,6,7],'R':[12,13,14,15,16,17]}; ARMJ={'L':[8,9,10],'R':[18,19,20]}
def zzmask(Q,th=0.8):
    d=np.diff(Q,axis=0); z=(d[1:]*d[:-1]<0)&(np.abs(d[1:])>th)&(np.abs(d[:-1])>th); return z
def resolve(st,rec,pel,eul):
    """same contacts, new torso pose: re-solve the limbs that are in contact"""
    s2=st.copy(); tasks=[]; free=np.zeros(28,bool); chk=[]
    for n in rec['contacts']:
        sd='L' if n.startswith('left') else 'R'; l=LINKOF[n]
        if 'Foot' in n:
            Rf=st.w[l][0].copy(); pA=st.pt(l,refpt(sd,'A')); tasks+=[T_point(l,refpt(sd,'A'),pA,100),T_dir(l,EZ,Rf@EZ,50),T_dir(l,EY,Rf@EY,50)]; chk.append((l,refpt(sd,'A'),pA)); free[[6+j for j in LEGJ[sd]]]=True
        elif 'Knee' in n:
            c=st.pt(l,C1[l]); tasks.append(T_point(l,C1[l],c,100)); chk.append((l,C1[l],c)); free[[6+j for j in LEGJ[sd][:4]]]=True
        else:
            c=st.pt(l,refpt(sd,'P')); tasks.append(T_point(l,refpt(sd,'P'),c,100)); chk.append((l,refpt(sd,'P'),c)); free[[6+j for j in ARMJ[sd]]]=True
    R=Reul(eul); s2.R=R; s2.t=pel-R@PEL; s2.update()
    wq=np.full(22,0.02); solve_ik(s2,tasks,qref=st.q.copy(),wq=wq,qlo=QLO_,qhi=QHI_,iters=50,free=free,tol=1e-6)
    res=max([np.abs(s2.pt(l,pl)-pw).max() for l,pl,pw in chk] or [0])
    return s2,res
QLO_=QLO.copy(); QHI_=QHI.copy(); QLO_[5]=-14; QHI_[15]=14; QHI_[10]=0; QLO_[20]=0; QHI_[2]=23; QLO_[12]=-23
def run(recs,rounds=4,log=print):
    n=len(recs)
    for rnd in range(rounds):
        Q=np.array([r['state'].q for r in recs]); z=zzmask(Q); fr=np.where(z.any(axis=1))[0]+1
        if len(fr)==0: break
        mask=np.zeros(n,bool)
        for f in fr: mask[max(1,f-3):min(n-1,f+4)]=True
        P_=np.array([r['state'].pel() for r in recs]); E_=np.array([euler(r['state'].R) for r in recs])
        w=np.array([1,2,3,2,1.])/9
        Ps=P_.copy(); Es=E_.copy()
        for f in range(2,n-2):
            Ps[f]=(w[:,None]*P_[f-2:f+3]).sum(0); Es[f]=(w[:,None]*E_[f-2:f+3]).sum(0)
        ok=0;bad=0
        for f in np.where(mask)[0]:
            if f<2 or f>=n-2: continue
            s2,res=resolve(recs[f]['state'],recs[f],Ps[f],Es[f])
            if res<0.12: recs[f]['state']=s2; ok+=1
            else: bad+=1
        Q=np.array([r['state'].q for r in recs]); log('round',rnd,'zigzag samples',int(z.sum()),'-> ',int(zzmask(Q).sum()),'frames resolved',ok,'kept',bad)
    return recs
if __name__=='__main__':
    recs=pickle.load(open(sys.argv[1],'rb')); recs=run(recs); pickle.dump(recs,open(sys.argv[2],'wb'))
    Q=np.array([r['state'].q for r in recs]); sp=np.abs(np.diff(Q,axis=0))*HZ; print('max speed',sp.max())
