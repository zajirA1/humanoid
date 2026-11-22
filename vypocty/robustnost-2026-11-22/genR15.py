# sestaví pohyb R15 z R13: poloviční posun trupu (snímky 74–192) + volitelný posun cíle volné levé nohy
import json,subprocess,sys,math
dy,dz,a,b=map(float,sys.argv[1:5]); out=sys.argv[5]; f=float(sys.argv[6]) if len(sys.argv)>6 else 1.0
M=json.load(open('/tmp/plan/model_R13.json')); off=json.load(open('/tmp/plan/off.json'))
def okno(i):  # plynulý náběh/doběh 12 snímků
    if i<a-12 or i>b+12: return 0.0
    if i<a: return 0.5-0.5*math.cos(math.pi*(i-a+12)/12)
    if i>b: return 0.5+0.5*math.cos(math.pi*(i-b)/12)
    return 1.0
rq=[]
for i in range(74,193):
    w=okno(i); r={"i":i,"off":[0.5*x*(1-(1-f)*w) for x in off[i]]}
    if w>0: r['shift']={'7':[0,dy*w,dz*w]}
    rq.append(r)
json.dump(rq,open(out+'.rq','w'))
subprocess.run(['node','/tmp/plan/posun2.js','/tmp/plan/model_R13.json',out+'.rq',out+'.rs'],check=True)
R=json.load(open(out+'.rs')); dmax=0
for r in R: M['q'][r['i']]=r['q']; M['rt'][r['i']]=r['rt']; dmax=max(dmax,r['drift'])
cur=json.load(open('/home/claude/humanoid/kontrola/data/model.json'))
for k in ('revize','revize_popis','vyska_od_s','vyska_nabeh_s'): M[k]=cur[k]
json.dump(M,open(out,'w'),separators=(',',':')); print('drift',round(dmax,3))
