import sys,json,subprocess,math,os; sys.argv=['x']
exec(open('/tmp/plan/metriky.py').read().replace("if __name__=='__main__':","if False:"))
n=len(M['q']); pid=str(os.getpid())
def node(reqs):
    json.dump(reqs,open(f'/tmp/plan/b{pid}.rq','w')); subprocess.run(['node','/tmp/plan/posun2.js','/home/claude/humanoid/kontrola/data/model.json',f'/tmp/plan/b{pid}.rq',f'/tmp/plan/b{pid}.rs'],check=True)
    return json.load(open(f'/tmp/plan/b{pid}.rs'))
def plants(name):
    on=[name in s for s in M['support']]; iv=[]
    for i,o in enumerate(on):
        if o and (i==0 or not on[i-1]): st=i
        if o and (i==n-1 or not on[i+1]): iv.append((st,i))
    return iv
RAMP=12
def vaha(i,a,b):
    if a<=i<=b: return 1.0
    if a-RAMP<=i<a: return 0.5-0.5*math.cos(math.pi*(i-(a-RAMP))/RAMP)
    if b<i<=b+RAMP: return 0.5-0.5*math.cos(math.pi*((b+RAMP)-i)/RAMP)
    return 0.0
shift=np.zeros((n,2,2))   # [frame][palm 0=L,1=P][dx,dy]
def pen(o,s50,drift):
    if s50 is None or s50>0.8 or drift>0.5: return 50.0
    return max(0,5-o['fnez'])+max(0,(15-o['marg'])/3)
G=[(dx,dy) for dx in (-30,-15,0,15,30) for dy in (-30,-15,0,15,30)]
vysl=[]
for pi,(name,link) in enumerate((('leftPalm',10),('rightPalm',20))):
    for a,b in plants(name):
        fr=list(range(a,b+1,4))
        reqs=[]
        for dx,dy in G:
            for i in fr:
                sh={'10':(shift[i,0]).tolist()+[0],'20':(shift[i,1]).tolist()+[0]}; sh[str(link)]=[dx,dy,0]
                reqs.append({'i':i,'shift':sh,'tag':[dx,dy]})
        res=node(reqs); tot={}
        for rq,r in zip(reqs,res):
            o=robust(r['q'],r['rt'],M['contacts'][r['i']]); k=tuple(rq['tag']); tot[k]=tot.get(k,0)+pen(o,r['s50'],r['drift'])
        best=min(tot,key=lambda k:tot[k]+0.01*math.hypot(*k)*len(fr))
        for i in range(max(0,a-RAMP),min(n,b+RAMP+1)):
            w=vaha(i,a,b)
            if w>0: shift[i,pi]=shift[i,pi]*(1-w)+np.array(best)*w
        vysl.append((name,a/6,b/6,best,round(tot[(0,0)],1),round(tot[best],1)))
        print(f'{name} {a/6:.1f}–{b/6:.1f} s: posun {best} mm, penalizace {tot[(0,0)]:.1f} → {tot[best]:.1f}',flush=True)
np.save('/tmp/plan/shift.npy',shift)
# celý pohyb
res=node([{'i':i,'shift':{'10':shift[i,0].tolist()+[0],'20':shift[i,1].tolist()+[0]}} for i in range(n)])
Q=[r['q'] for r in res]; RT=[r['rt'] for r in res]; DR=max(r['drift'] for r in res); S=max(r['s50'] or 9 for r in res)
json.dump(dict(q=Q,rt=RT),open('/tmp/plan/novyB.json','w'))
N=[robust(Q[i],RT[i],M['contacts'][i]) for i in range(n)]
w2=[i for i,o in enumerate(N) if o['marg']<15 or o['fnez']<5]
print('posun opory max',round(DR,2),'statika max',round(S,3),'slabých poloh R13 239 →',len(w2),'rezerva min',round(min(o['marg'] for o in N),1),'nezbytná min',round(min(o['fnez'] for o in N),1),'pod 3 N:',sum(1 for o in N if o['fnez']<3))
