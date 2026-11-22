import sys; sys.path.insert(0,'/home/claude/sim')
from fullpass import *
import time
src,sup=timeline(); poff=palm_offsets(src); R=Runner(src,sup,poff)
KB=pickle.load(open('key_B3.pkl','rb')); keys=KB['keys']
v=np.zeros((len(src),6)); vi=interp_v(keys,KB['v'],len(src)); v[keys[0]:keys[-1]+1]=vi[keys[0]:keys[-1]+1]
t=time.time(); seq=full_pass(R,v,keys[0],keys[-1]); print('fullpass',time.time()-t)
t=time.time(); rows=metrics(seq,exact=True); print('metrics',time.time()-t)
pickle.dump((seq,rows),open('fp_B3.pkl','wb'))
f0=keys[0]
def col(k): return np.array([np.nan if r[k] is None else r[k] for r in rows],float)
for k in ('s50','s40','s30','margin','self','adj','env','riser','pad','rc','rsw'):
    c=col(k); i=np.nanargmin(c) if k in('margin','self','adj','env','riser','pad') else np.nanargmax(c)
    print(k,'min' if k in('margin','self','adj','env','riser','pad') else 'max',round(float(c[i]),3),'at',f0+i,'src',rows[i]['src'],rows[i].get(k+'pair') or rows[i].get(k+'key') or '', 'nan:',int(np.isnan(c).sum()))
s=col('s50'); print('frames s>0.5:',[(f0+i,round(x,2)) for i,x in enumerate(s) if x>0.5])
e=col('env'); print('env<5:',[(f0+i,round(x,1),rows[i]['envkey']) for i,x in enumerate(e) if x<5][:40])
sf=col('self'); print('self<10:',[(f0+i,round(x,1),rows[i]['selfpair']) for i,x in enumerate(sf) if x<10][:40])
ad=col('adj'); print('adj<2.1:',[(f0+i,round(x,2),rows[i]['adjpair']) for i,x in enumerate(ad) if x<2.1][:40])
q=np.array([st.q for fr,st in seq]); dq=np.abs(np.diff(q,axis=0))*HZ; print('max joint speed deg/s',dq.max().round(1),'joint',JN[np.unravel_index(dq.argmax(),dq.shape)[1]],'frame',f0+np.unravel_index(dq.argmax(),dq.shape)[0])
