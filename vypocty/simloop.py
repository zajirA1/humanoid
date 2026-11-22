import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
import mj
from scipy.ndimage import gaussian_filter1d
def run(recs,rows,sig=1.2,label='',verbose=True,**kw):
    states=[r['state'] for r in recs]; n=len(states)
    Q=np.array([s.q for s in states]); ff=np.array([np.zeros(22) if r_['r'] is None else r_['r']['tau'] for r_ in rows]); ff[:,[11,21]]=0
    if sig>0:
        Qs=gaussian_filter1d(Q,sig,axis=0,mode='nearest'); ffs=gaussian_filter1d(ff,sig*1.5,axis=0,mode='nearest')
        st2=[State(s.R,s.t,q) for s,q in zip(states,Qs)]
    else: st2=states; ffs=ff
    rec=mj.simulate(st2,tau_ff=ffs,**kw); res=mj.judge(rec,states)
    tt=rec['t']; er=np.linalg.norm(rec['root']-np.array([states[min(n-1,max(0,int(round(t*HZ))))].t for t in tt]),axis=1)
    bad=np.where(er>40)[0]; ft=float(tt[bad[0]]) if len(bad) else None
    ratio=rec['taupk']/rec['lim']; ratio[:,[11,21]]=0
    if verbose:
        print(label,'fall_t',ft,'frame',None if ft is None else int(ft*HZ),'success',res['success'],'end err',round(res['root_err_end'],1),'tilt',round(res['tilt_err_end'],1),'sat_frac',round(res['sat_frac'],3),'max err before fall',round(float(er[:bad[0]].max()) if len(bad) else float(er.max()),1))
        seg=np.array_split(np.arange(len(tt)),24)
        print('   err/seg',[round(float(er[s_].max())) for s_ in seg]); print('   ratio/seg',[round(float(ratio[s_].max()),2) for s_ in seg])
    return rec,res,ft
if __name__=='__main__':
    recs=pickle.load(open(sys.argv[1],'rb')); T=pickle.load(open(sys.argv[2],'rb')); rows=T['rows']
    for sig in (0,1.2,2.0):
        run(recs,rows,sig=sig,label=f'sig {sig} rated')
    run(recs,rows,sig=1.2,label='sig 1.2 stall',lim_scale=3.0)
