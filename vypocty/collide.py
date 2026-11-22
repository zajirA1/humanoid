"""Mesh clearance checks with FCL: link-vs-link (non-adjacent), adjacent pairs, robot-vs-step."""
import numpy as np, fcl
from geom import ITEMS, PAD, PAD_R
from emil import PAR
NL=23
def _bvh(v,f):
    m=fcl.BVHModel(); m.beginModel(len(v),len(f)); m.addSubModel(np.ascontiguousarray(v,float),np.ascontiguousarray(f,np.int32)); m.endModel(); return m
class LinkGeom:
    def __init__(s,items,name):
        vs=[];fs=[];o=0; s.parts=[]
        for it in items:
            vs.append(it['v']); fs.append(it['f']+o); s.parts.append((o,o+len(it['v']),it['key'],it['idx'])); o+=len(it['v'])
        s.v=np.vstack(vs); s.f=np.vstack(fs); s.name=name
        s.model=_bvh(s.v,s.f); s.obj=fcl.CollisionObject(s.model,fcl.Transform())
        s.lo=s.v.min(0); s.hi=s.v.max(0)
        c=np.array([[x,y,z] for x in (s.lo[0],s.hi[0]) for y in (s.lo[1],s.hi[1]) for z in (s.lo[2],s.hi[2])]); s.corners=c
    def set(s,R,t):
        s.obj.setTransform(fcl.Transform(np.ascontiguousarray(R),np.ascontiguousarray(t)))
        cw=s.corners@R.T+t; s.wlo=cw.min(0); s.whi=cw.max(0)
COVER_KEYS=lambda k: ('thigh' in k or 'chest' in k or 'back' in k or 'face' in k or 'visor' in k or 'vent' in k or 'rib' in k or 'light' in k)
# geometry groups: per link "frame+hardware" and per link "covers"
G={}
for l in range(NL):
    its=[it for it in ITEMS if it['link']==l and it['kind']!='cover' and it['key']!='r11_climb_TPU']
    cov=[it for it in ITEMS if it['link']==l and it['kind']=='cover']
    sl=[it for it in ITEMS if it['link']==l and it['key']=='r11_climb_TPU']
    if its: G[(l,'body')]=LinkGeom(its,f'L{l}')
    if cov: G[(l,'cover')]=LinkGeom(cov,f'L{l}cov')
    if sl: G[(l,'sleeve')]=LinkGeom(sl,f'L{l}sleeve')
def adjacent(a,b): return (a<22 and PAR[a]==b) or (b<22 and PAR[b]==a)
PAIRS=[]; ADJ=[]
keys=list(G)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        (la,ka),(lb,kb)=keys[i],keys[j]
        if la==lb: continue
        if adjacent(la,lb):
            if ka=='cover' or kb=='cover': PAIRS.append((keys[i],keys[j]))   # covers are checked against the neighbour too
            else: ADJ.append((keys[i],keys[j]))
        else: PAIRS.append((keys[i],keys[j]))
# gripper internals excluded: links 11 & 21 vs their parents are adjacent -> in ADJ only
_req=fcl.DistanceRequest(enable_nearest_points=True)
def place(st):
    for (l,k),g in G.items(): R,t=st.w[l]; g.set(R,t)
def _gap(a,b): return np.maximum(0,np.maximum(a.wlo-b.whi,b.wlo-a.whi)).max()
def min_dist(st,pairs=PAIRS,cutoff=15.0,placed=False):
    """returns (min distance, pair) over pairs whose boxes are closer than cutoff"""
    if not placed: place(st)
    best=(cutoff,None,None)
    for ka,kb in pairs:
        a,b=G[ka],G[kb]
        if _gap(a,b)>=best[0]: continue
        res=fcl.DistanceResult(); d=fcl.distance(a.obj,b.obj,_req,res)
        if d<best[0]: best=(d,(ka,kb),(np.array(res.nearest_points[0]),np.array(res.nearest_points[1])))
    return best
def part_of(key,pt_local):
    g=G[key]; i=np.argmin(((g.v-pt_local)**2).sum(1))
    for a,b,name,idx in g.parts:
        if a<=i<b: return name
# ---- environment: floor slab and the step block ----
_floor=fcl.CollisionObject(fcl.Box(2000,2000,100),fcl.Transform(np.array([0,0,-50.0])))
_step=fcl.CollisionObject(fcl.Box(660,280,210),fcl.Transform(np.array([0,-140.0,105.0])))
def env_dist(st,exclude=(),cutoff=30.0,placed=False,detail=False):
    """min distance of robot geometry to floor/step. exclude: set of (link,kind) geometry keys to skip"""
    if not placed: place(st)
    best=(cutoff,None,None); allv=[]
    for key,g in G.items():
        if key in exclude: continue
        for name,ob,lo,hi in (('floor',_floor,np.array([-1000,-1000,-100.]),np.array([1000,1000,0.])),('step',_step,np.array([-330,-280,0.]),np.array([330,0,210.]))):
            gap=np.maximum(0,np.maximum(g.wlo-hi,lo-g.whi)).max()
            if gap>=(cutoff if detail else best[0]): continue
            res=fcl.DistanceResult(); d=fcl.distance(g.obj,ob,_req,res)
            if detail: allv.append((d,key,name,np.array(res.nearest_points[0]),np.array(res.nearest_points[1])))
            if d<best[0]: best=(d,(key,name),np.array(res.nearest_points[0]))
    return (best,allv) if detail else best
