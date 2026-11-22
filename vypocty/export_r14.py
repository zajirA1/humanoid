import sys,json,pickle; sys.path.insert(0,'/home/claude/sim')
from retarget import *
from contact import *
import fork
recs=pickle.load(open('final14.pkl','rb'))
fr=[];ref=[]
for r in recs:
    st=r['state']; names,extra=support_pts(st,r['support'])
    pts=[]
    for n in names:
        for p in patch(st,n): pts.append((LINKOF[n],p))
    pts+=[(l,p) for l,p,k in extra]
    flat=[]
    for l,p in pts:
        R,t=st.w[l]; loc=R.T@(p-t); flat+=[int(l)]+[round(float(x),3) for x in loc]
    res=stat(st,r['support'])
    fr.append(flat); ref.append([round(res['s'],5),res['jmax']]+[round(float(x),4) for x in res['tau']])
g=fork.geometry()
forks={}
for L,v in g.items():
    if v and v['bridge']:
        for j in (L,L+10): forks[j]=dict(L=round(v['bridge'],1),t=round(min(v['t']),2),span=round(v['span'],1),w=round(v['width'],1))
SM={j:(0.018 if j in(0,1,11,21) else 0.150 if j in(3,13) else 0.075 if j in(4,5,6,14,15,16) else 0.055) for j in range(22)}
out=dict(mu=0.5,lim=[float(x) for x in LIM],links=[[float(x) for x in r] for r in LINKS],P=[[float(x) for x in p] for p in P],
 contacts=fr,ref=ref,forks=forks,servoKg=[SM[j] for j in range(22)],
 q=[[float(x) for x in r['state'].q] for r in recs],rt=[[float(x) for x in r['state'].rt()] for r in recs])
json.dump(out,open('r14data.json','w'),separators=(',',':'))
print(len(fr),max(len(f)//4 for f in fr),max(x[0] for x in ref),forks.keys())
