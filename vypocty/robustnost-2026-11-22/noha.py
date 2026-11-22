# plán R15: volná levá noha ve fázi 3 – po polohách pootočit klouby tak, aby koleno/holeň minuly hranu schodu
# o >= CIL mm, změny vyhladit v čase (bez skoků), opory/trup beze změny
import sys,json,numpy as np
sys.path.insert(0,'/home/claude/humanoid/kontrola')
import prepocet as pp, doladeni as dl
from scipy.optimize import minimize
from scipy.ndimage import gaussian_filter1d
src,out=sys.argv[1],sys.argv[2]; a,b=int(sys.argv[3]),int(sys.argv[4]); CIL=float(sys.argv[5]) if len(sys.argv)>5 else 6.0
M=json.load(open(src)); A=json.load(open('/tmp/plan/_A.json')); P,E=A['P'],A['E']
G,pairs=pp.nacti_geometrii({}); J=[2,3,4,5,6,7]; links=set(J)
mypairs=[(x,y) for x,y in pairs if x[0] in links or y[0] in links]
ex_of=lambda i:{k for k,bb in (((7,'body'),1),((17,'body'),2),((5,'sleeve'),4),((15,'sleeve'),8)) if M['ex'][i]&bb}
idx=[i for i in range(a,b+1) if dl.volna('L_noha',M['support'][i])]
X=np.zeros((b-a+1,6))
def m(i,x):
    q=np.array(M['q'][i],float); q[J]+=x
    return dl.min_koncetiny(G,mypairs,links,pp.fk(q,M['rt'][i],P,E),pp.STEP,ex_of(i),CIL+2)
for i in idx:
    m0=m(i,np.zeros(6))
    if m0>=CIL: continue
    r=minimize(lambda x:-min(m(i,x),CIL)+0.02*float(x@x),X[i-a-1] if i>a else np.zeros(6),method='Powell',bounds=[(-10,10)]*6,options=dict(xtol=0.05,maxfev=300))
    X[i-a]=r.x; print(i,round(m0,2),'->',round(m(i,r.x),2),np.round(r.x,1).tolist(),flush=True)
# vyhladit a zúžit na volné polohy
mask=np.array([1.0 if (a+k) in idx else 0.0 for k in range(b-a+1)])
Xs=gaussian_filter1d(X,2,axis=0,mode="constant")*1.3
Xs*=gaussian_filter1d(mask,1.0,mode='constant')[:,None]*mask[:,None]
for k in range(b-a+1):
    i=a+k; q=np.array(M['q'][i],float); q[J]+=Xs[k]; M['q'][i]=q.tolist()
print('max změna',round(float(np.abs(Xs).max()),2),'°')
json.dump(M,open(out,'w'),separators=(',',':'))
