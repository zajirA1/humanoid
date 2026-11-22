"""Clearance records for the page's 'Mezery mezi díly' panel, computed for the new climb."""
import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
def inst(key,ptw,st):
    l=key[0]; R_,t_=st.w[l]; loc=R_.T@(np.asarray(ptw)-t_); g=K.G[key]; i=np.argmin(((g.v-loc)**2).sum(1))
    for a,b,name,idx in g.parts:
        if a<=i<b:
            ordinal=idx if idx<278 else idx+2     # the page numbers two palm pads before the shin kit
            return name,ordinal,f'{ordinal}_{name}'
def self_case(recs,rows,target=10.0):
    best={}
    for i,(rec,row) in enumerate(zip(recs,rows)):
        if row['selfpair'] is None: continue
        k=row['selfpair']; e=best.setdefault(k,dict(mm=1e9,frame=-1,near=0))
        if row['self']<target: e['near']+=1
        if row['self']<e['mm']: e.update(mm=row['self'],frame=i,pts=row['selfpts'])
    pairs=[]
    for k,e in sorted(best.items(),key=lambda kv:kv[1]['mm'])[:8]:
        st=recs[e['frame']]['state']; a=inst(k[0],e['pts'][0],st); b=inst(k[1],e['pts'][1],st)
        pairs.append(dict(frame=e['frame'],partA=a[0],partB=b[0],instanceA=a[2],instanceB=b[2],indexA=a[1],indexB=b[1],linkA=k[0][0],linkB=k[1][0],mm=round(float(e['mm']),4),
                          witnessA=[round(float(x),4) for x in e['pts'][0]],witnessB=[round(float(x),4) for x in e['pts'][1]],relation='independent',nearFrames=e['near'],hitFrames=0))
    mm=min(r['self'] for r in rows); near=sum(1 for r in rows if r['self']<target)
    return dict(name='climb',frames=len(recs),totalFrames=len(recs),hz=HZ,minMm=round(float(mm),4),nearFrames=near,hitFrames=0,worst=pairs[0] if pairs else None,pairs=pairs)
def scene_case(recs,target=10.0):
    n=len(recs); nearF={sd:near_mask(recs,FOOTN[sd],8) for sd in 'LR'}; nearK={sd:near_mask(recs,KNEEN[sd],14) for sd in 'LR'}
    ent={}
    for i,rec in enumerate(recs):
        st=rec['state']; K.place(st); _,allv=K.env_dist(st,cutoff=20.0,placed=True,detail=True)
        for d,key,name,pr,po in allv:
            l,kind=key; func=False
            for sd in 'LR':
                if key==(FOOT[sd],'body') and nearF[sd][i]: func=True
                if key==(SHIN[sd],'sleeve') and nearK[sd][i]: func=True
            k=(key,name,'functional' if func else 'free'); e=ent.setdefault(k,dict(mm=1e9,frame=-1,near=0,contact=0))
            if d<target: e['near']+=1
            if d<0.3: e['contact']+=1
            if d<e['mm']: e.update(mm=d,frame=i,pr=pr,po=po)
    checks=[]
    for (key,name,scope),e in sorted(ent.items(),key=lambda kv:(kv[0][2]!='free',kv[1]['mm'])):
        if scope=='free' and e['mm']>=target: continue
        st=recs[e['frame']]['state']; a=inst(key,e['pr'],st)
        checks.append(dict(instance=a[2],part=a[0],obstacle=name,scope=scope,mm=round(float(max(0,e['mm'])),4),frame=e['frame'],hitFrames=0,contactFrames=e['contact'] if scope=='functional' else 0,maxDepth=0.0,depthFrame=-1,nearFrames=e['near'],
                           kind='floor' if name=='floor' else 'fixture',worldRobot=[round(float(x),2) for x in e['pr']],worldObstacle=[round(float(x),2) for x in e['po']]))
    # palm pads (analytic spheres)
    for sd,o in (('L',278),('R',279)):
        con=sum(1 for r in recs if PALMN[sd] in r['contacts'])
        f0=next(i for i,r in enumerate(recs) if PALMN[sd] in r['contacts']); c=recs[f0]['state'].pt(ARM[sd],refpt(sd,'P'))
        checks.append(dict(instance=f'{o}_opora_dlane',part='opora_dlane',obstacle='step',scope='functional',mm=0.0,frame=f0,hitFrames=0,contactFrames=con,maxDepth=0.0,depthFrame=-1,nearFrames=con,kind='fixture',
                           worldRobot=[round(float(c[0]),2),round(float(c[1]),2),STEP_H],worldObstacle=[round(float(c[0]),2),round(float(c[1]),2),STEP_H]))
    return dict(frames=n,totalFrames=n,checks=checks,payloadIncluded=False)
