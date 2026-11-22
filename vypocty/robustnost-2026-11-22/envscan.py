import sys,json,numpy as np
sys.path.insert(0,'/home/claude/humanoid/kontrola')
import prepocet as pp
D=json.load(open(sys.argv[1])); A=json.load(open('/tmp/plan/_A.json')); P,E=A['P'],A['E']
G,pairs=pp.nacti_geometrii({})
res=[]
for i in range(int(sys.argv[2]),int(sys.argv[3])):
    w=pp.fk(D['q'][i],D['rt'][i],P,E); d,bp,e,k=pp.mezery(G,pairs,w,D['ex'][i]); res.append((e,i,k,d))
m=min(res); print('env min',round(m[0],2),'@',m[1],m[2],'self min',round(min(r[3] for r in res),2))
