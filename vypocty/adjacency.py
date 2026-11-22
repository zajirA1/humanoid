"""Adjacent-link frame clearance as a function of the joint angle (frames / non-mating printed parts only)."""
import sys; sys.path.insert(0,'/home/claude/sim')
import numpy as np, fcl, math
from geom import ITEMS
from emil import PAR,P,AX,JN,rot
def is_frame(k): return ('ram' in k) or ('knee_index' in k) or k=='r11_climb_TPU'
PARTS={}
for it in ITEMS:
    if is_frame(it['key']):
        m=fcl.BVHModel(); m.beginModel(len(it['v']),len(it['f'])); m.addSubModel(np.ascontiguousarray(it['v']),np.ascontiguousarray(it['f'],np.int32)); m.endModel()
        PARTS.setdefault(it['link'],[]).append((it['key'],fcl.CollisionObject(m,fcl.Transform())))
_req=fcl.DistanceRequest()
def joint_clear(j,q):
    R,t=rot(AX[j],q,P[j]); best=(1e9,None)
    for kb,ob in PARTS.get(j,[]):
        ob.setTransform(fcl.Transform(np.ascontiguousarray(R),np.ascontiguousarray(t)))
        for ka,oa in PARTS.get(PAR[j],[]):
            oa.setTransform(fcl.Transform())
            res=fcl.DistanceResult(); d=fcl.distance(oa,ob,_req,res)
            if d<best[0]: best=(d,(ka,kb))
    return best
MATING={}
def sweep(j,qlo,qhi,step=1.0):
    """min clearance over the angle range, ignoring part pairs that mate (touch) at q=0"""
    R0,t0=rot(AX[j],0,P[j]); mating=set()
    for kb,ob in PARTS.get(j,[]):
        ob.setTransform(fcl.Transform(np.ascontiguousarray(R0),np.ascontiguousarray(t0)))
        for ka,oa in PARTS.get(PAR[j],[]):
            oa.setTransform(fcl.Transform()); res=fcl.DistanceResult()
            if fcl.distance(oa,ob,_req,res)<0.3: mating.add((ka,kb))
    best=(1e9,None,None)
    for q in np.arange(math.floor(qlo),math.ceil(qhi)+0.5,step):
        R,t=rot(AX[j],q,P[j])
        for kb,ob in PARTS.get(j,[]):
            ob.setTransform(fcl.Transform(np.ascontiguousarray(R),np.ascontiguousarray(t)))
            for ka,oa in PARTS.get(PAR[j],[]):
                if (ka,kb) in mating: continue
                oa.setTransform(fcl.Transform()); res=fcl.DistanceResult(); d=fcl.distance(oa,ob,_req,res)
                if d<best[0]: best=(d,(ka,kb),q)
    return best,mating
if __name__=='__main__':
    import json
    C=json.load(open('/home/claude/work/r9ClimbData.json')); Q=np.array([p['q'] for p in C['poses']])
    for j in range(22):
        b,m=sweep(j,Q[:,j].min(),Q[:,j].max())
        print(j,JN[j],'range',Q[:,j].min().round(1),Q[:,j].max().round(1),'min',round(b[0],3),b[1],'at',b[2],'mating',len(m))
