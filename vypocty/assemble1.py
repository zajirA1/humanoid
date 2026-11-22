import sys; sys.path.insert(0,'/home/claude/sim')
from relax import *
from seqmetrics import *
def build(Vfile,f_end):
    R,supo=setup(); V=np.load(Vfile); n=len(R.src); keys=list(range(0,n,KS))
    vk={f:V[f] for f in keys}; v=interp_v(keys,vk,n)
    seq=full_pass(R,v,0,f_end)
    recs=[dict(state=st,support=set(fr.support),contacts=set(fr.ref.contacts),phase=fr.ref.phase,src=fr.src,rc=fr.rc,rsw=fr.rsw,proj=getattr(fr,'projected',False)) for fr,st in seq]
    return R,recs
if __name__=='__main__':
    Vfile=sys.argv[1]; R,supo=setup(); f_end=int(np.where(R.src==757)[0][0])+2
    R,recs=build(Vfile,f_end); rows,sp=seq_metrics(recs,exact=(len(sys.argv)<4)); pickle.dump((recs,rows,sp),open(sys.argv[2],'wb'))
    summarize(rows,sp,'NEW')
    def col(k): return np.array([np.nan if r.get(k) is None else r[k] for r in rows],float)
    s=col('s50'); print('s>0.5 or nan:',[(i,None if np.isnan(x) else round(x,2)) for i,x in enumerate(s) if not x<=0.5])
    print('rc>0.3:',[(i,round(r['rc'],1)) for i,r in enumerate(recs) if r['rc']>0.3])
    print('projected:',sum(1 for r in recs if r.get('proj')))
    if len(sys.argv)>3: sys.exit()
    print('self<10:',[(i,round(r['self'],1),r['selfpair'][0][0],r['selfpair'][1][0]) for i,r in enumerate(rows) if r['self']<10])
    print('env<5:',[(i,round(r['env'],1),r['envkey'][0]) for i,r in enumerate(rows) if r['env']<5])
    print('pad<3:',[(i,round(r['pad'],1)) for i,r in enumerate(rows) if r['pad']<3])
    print('pen>0.3:',[(i,round(r['pen'],2)) for i,r in enumerate(rows) if r['pen']>0.3])
    print('margin<8:',[(i,round(r['margin'])) for i,r in enumerate(rows) if r['margin']<8])
    print('speed>45:',sorted(set(np.where(sp>45)[0].tolist())))
