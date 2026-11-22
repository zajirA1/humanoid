import sys,json,subprocess,math; sys.argv=['x']
exec(open('/tmp/plan/metriky.py').read().replace("if __name__=='__main__':","if False:"))
from scipy.ndimage import gaussian_filter1d
n=len(M['q']); R13=json.load(open('/tmp/plan/r13_robust.json'))
FMIN,MMIN,SMAX=5.0,15.0,0.78
def skore(o,s50,drift):
    if s50 is None or s50>SMAX or drift>0.3: return -99
    return min(o['fnez']-FMIN,(o['marg']-20.0)/2.0,3.0)
weak=[i for i,o in enumerate(R13) if o['marg']<MMIN or o['fnez']<FMIN]
us=[]
for i in weak:
    if us and i-us[-1][1]<=6: us[-1][1]=i
    else: us.append([i,i])
PAD=12; grid=[(dx,dy) for dx in range(-24,25,4) for dy in range(-24,25,4)]
def node(reqs):
    json.dump(reqs,open('/tmp/plan/rq.json','w')); subprocess.run(['node','/tmp/plan/posun.js','/home/claude/humanoid/kontrola/data/model.json','/tmp/plan/rq.json','/tmp/plan/rs.json'],check=True)
    return json.load(open('/tmp/plan/rs.json'))
off=np.zeros((n,3)); log=[]
for a,b in us:
    keys=list(range(a,b+1,3)) or [a]
    if keys[-1]!=b: keys.append(b)
    res=node([{'i':i,'off':[dx,dy,0]} for i in keys for dx,dy in grid])
    best={}
    for r in res:
        o=robust(r['q'],r['rt'],M['contacts'][r['i']]); sc=skore(o,r['s50'],r['drift'])-0.004*math.hypot(*r['off'][:2])
        if r['i'] not in best or sc>best[r['i']][0]: best[r['i']]=(sc,r['off'])
    K=np.array([best[i][1] for i in keys],float)
    if len(K)>2: K[:,0]=gaussian_filter1d(K[:,0],1.0,mode='nearest'); K[:,1]=gaussian_filter1d(K[:,1],1.0,mode='nearest')
    lo=max(0,a-PAD); hi=min(n-1,b+PAD)
    for i in range(lo,hi+1):
        v=np.array([np.interp(i,keys,K[:,0]),np.interp(i,keys,K[:,1]),0.0])
        wt=1.0 if a<=i<=b else (0.5-0.5*math.cos(math.pi*(i-lo)/max(1,a-lo)) if i<a else 0.5-0.5*math.cos(math.pi*(hi-i)/max(1,hi-b)))
        # překrývající se náběhy: ponechat větší posun
        cand=v*wt
        if np.linalg.norm(cand)>np.linalg.norm(off[i]): off[i]=cand
    log.append((a,b,[round(best[i][0],2) for i in keys][:6],K.max(0).round(1).tolist(),K.min(0).round(1).tolist()))
    print(f'{a/6:.1f}–{b/6:.1f} s: posun trupu x {K[:,0].min():+.0f}…{K[:,0].max():+.0f} mm, y {K[:,1].min():+.0f}…{K[:,1].max():+.0f} mm',flush=True)
json.dump(off.tolist(),open('/tmp/plan/off.json','w'))
# vygenerovat celý pohyb
idx=[i for i in range(n) if np.abs(off[i]).max()>1e-6]
res=node([{'i':i,'off':off[i].tolist()} for i in idx]); byi={r['i']:r for r in res}
Q=[byi[i]['q'] if i in byi else M['q'][i] for i in range(n)]; RT=[byi[i]['rt'] if i in byi else M['rt'][i] for i in range(n)]
S50=[byi[i]['s50'] for i in idx]; DR=max(byi[i]['drift'] for i in idx)
json.dump(dict(q=Q,rt=RT),open('/tmp/plan/novy.json','w'))
N=[robust(Q[i],RT[i],M['contacts'][i]) for i in range(n)]
w2=[i for i,o in enumerate(N) if o['marg']<MMIN or o['fnez']<FMIN]
print('poloh posunuto',len(idx),'max statika v nich',round(max(S50),3),'max posun opory',round(DR,3))
print('slabých poloh: R13',len(weak),'→ nový',len(w2))
for nm,L in (('R13',R13),('nový',N)):
    print(nm,'nejmenší rezerva',round(min(o['marg'] for o in L),1),'mm; nezbytná opora min',round(min(o['fnez'] for o in L),1),'N; poloh s nezbytnou oporou < 3 N:',sum(1 for o in L if o['fnez']<3))
json.dump([dict(marg=o['marg'],fnez=o['fnez']) for o in N],open('/tmp/plan/novy_robust.json','w'))
