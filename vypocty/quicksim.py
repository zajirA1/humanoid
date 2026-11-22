import sys; sys.path.insert(0,'/home/claude/sim')
from simloop import *
recs=pickle.load(open(sys.argv[1],'rb')); rows,sp=seq_metrics(recs,exact=False,mus=(0.5,))
s=np.array([np.nan if r['s50'] is None else r['s50'] for r in rows]); print('statics nan',int(np.isnan(s).sum()),'peak',np.nanmax(s),'speed',sp.max())
pickle.dump(dict(rows=rows),open(sys.argv[1].replace('.pkl','_q.pkl'),'wb'))
for kw,lab in ((dict(),'rated'),(dict(lim_scale=3.0),'stall')):
    run(recs,rows,sig=float(sys.argv[2]) if len(sys.argv)>2 else 0,label=lab,**kw)
