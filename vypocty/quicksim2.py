import sys; sys.path.insert(0,'/home/claude/sim')
from simloop import *
recs=pickle.load(open(sys.argv[1],'rb')); mu_ff=float(sys.argv[2])
rows=[]
for r in recs:
    x=stat(r['state'],r['support'],mu=mu_ff); rows.append(dict(r=x))
pickle.dump(dict(rows=rows),open(sys.argv[1].replace('.pkl',f'_ff.pkl'),'wb'))
for kw,lab in ((dict(),'rated'),(dict(lim_scale=3.0),'stall')):
    run(recs,rows,sig=1.0,label=lab+f' ff@mu{mu_ff}',**kw)
