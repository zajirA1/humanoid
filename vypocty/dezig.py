import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
recs=pickle.load(open('final10.pkl','rb'))
def zz(Q,th=1.2):
    d=np.diff(Q,axis=0); z=(d[1:]*d[:-1]<0)&(np.abs(d[1:])>th)&(np.abs(d[:-1])>th); return z
Q=np.array([r['state'].q for r in recs]); print('zigzag before',int(zz(Q).sum()), 'hyperext frames L',int((Q[:,5]<0).sum()),'R',int((Q[:,15]>0).sum()))
fixed=0;fail=0
for i,r in enumerate(recs):
    st=r['state']
    for sd,o,sgn in (('L',0,1),('R',10,-1)):
        k=5+o
        if sgn*st.q[k]>=0.5: continue
        f=FOOT[sd]; Rf=st.w[f][0].copy(); pA=st.pt(f,refpt(sd,'A')); s2=st.copy(); s2.q[k]=sgn*3.0; s2.update()
        qlo=QLO.copy(); qhi=QHI.copy()
        if sd=='L': qlo[5]=0.5
        else: qhi[15]=-0.5
        free=np.zeros(28,bool); free[6+2+o:6+8+o]=True
        tasks=[T_point(f,refpt(sd,'A'),pA,100),T_dir(f,EZ,Rf@EZ,50),T_dir(f,EY,Rf@EY,50)]
        wq=np.full(22,0.01); solve_ik(s2,tasks,qref=s2.q.copy(),wq=wq,qlo=qlo,qhi=qhi,iters=60,free=free,tol=1e-6)
        e=np.abs(s2.pt(f,refpt(sd,'A'))-pA).max(); eo=np.abs(s2.w[f][0]-Rf).max()
        incontact=('leftFoot' if sd=='L' else 'rightFoot') in r['contacts']
        if e<(0.15 if incontact else 2.0) and eo<(0.004 if incontact else 0.05): st.q=s2.q.copy(); st.update(); fixed+=1
        else: fail+=1
Q=np.array([r['state'].q for r in recs]); z=zz(Q); print('fixed',fixed,'unreachable without hyper-extension',fail,'zigzag after',int(z.sum()))
import collections; fr,jj=np.where(z); print({JN[j]:n for j,n in collections.Counter(jj).most_common()}); print(sorted(set(fr.tolist()))[:80])
pickle.dump(recs,open('final13.pkl','wb'))
