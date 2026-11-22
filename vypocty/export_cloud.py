import sys,json,pickle; sys.path.insert(0,'/home/claude/sim')
import numpy as np
from collide import G,PAIRS
from seqmetrics import near_mask,FOOTN,KNEEN
gj=json.load(open('geom.json'))['items']
rng=np.random.default_rng(1)
def sample(g,n=240):
    v=g.v; f=g.f; a=v[f[:,0]];b=v[f[:,1]];c=v[f[:,2]]; ar=np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
    k=rng.choice(len(f),size=6000,p=ar/ar.sum()); u=rng.random((6000,2)); s=u.sum(1)>1; u[s]=1-u[s]
    pts=a[k]+u[:,:1]*(b[k]-a[k])+u[:,1:]*(c[k]-a[k]); own=np.zeros(len(f),int)-1
    for o0,o1,key,idx in g.parts:
        it=gj[idx]; ow=it.get('owner'); tag=ow if (it.get('kind')=='cad' and not it.get('frame') and ow is not None and ow<22) else -1
        own[(f[:,0]>=o0)&(f[:,0]<o1)]=tag
    tags=own[k]
    sel=[int(np.argmax(pts[:,2]))]; d=np.linalg.norm(pts-pts[sel[0]],axis=1)
    while len(sel)<min(n,len(pts)):
        i=int(np.argmax(d)); sel.append(i); d=np.minimum(d,np.linalg.norm(pts-pts[i],axis=1))
    return pts[sel],tags[sel]
keys=list(G); clouds=[]
for (l,kind) in keys:
    p,t=sample(G[(l,kind)]); clouds.append(dict(link=l,kind=kind,p=[round(float(x),2) for x in p.ravel()],tag=[int(x) for x in t]))
pairs=[[keys.index(a),keys.index(b)] for a,b in PAIRS]
recs=pickle.load(open('final14.pkl','rb')); T=pickle.load(open('T_new2.pkl','rb')); rows=T['rows']
nF={sd:near_mask(recs,FOOTN[sd],8) for sd in 'LR'}; nK={sd:near_mask(recs,KNEEN[sd],14) for sd in 'LR'}
ex=[int(nF['L'][i])|int(nF['R'][i])<<1|int(nK['L'][i])<<2|int(nK['R'][i])<<3 for i in range(len(recs))]
D=json.load(open('r14data.json'))
for k in ('q','rt'): D.pop(k,None)
D['ref']=[r[0] for r in D['ref']]
D.update(clouds=clouds,pairs=pairs,ex=ex,selfBase=[round(float(r['self']),2) for r in rows],envBase=[round(float(r['env']),2) for r in rows])
json.dump(D,open('r14page.json','w'),separators=(',',':'))
print(len(keys),len(pairs),min(D['selfBase']),max(D['selfBase']),min(D['envBase']),max(D['envBase']))
