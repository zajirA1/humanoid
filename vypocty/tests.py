import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
import mj, adjacency, json
def midframes(recs):
    out=[]
    for a,b in zip(recs[:-1],recs[1:]):
        sa,sb=a['state'],b['state']; dR=logm(sb.R@sa.R.T); R=expm(0.5*dR)@sa.R
        pel=(sa.pel()+sb.pel())/2; st=State(R,pel-R@PEL,(sa.q+sb.q)/2)
        out.append(dict(state=st,support=a['support']&b['support'],contacts=a['contacts']&b['contacts'],phase=a['phase']))
    return out
def run_all(recs,label,sim=True,log=print):
    T={}
    rows,sp=seq_metrics(recs,exact=True); T['rows']=rows; T['speed']=sp
    def col(k,rws=rows): return np.array([np.nan if r.get(k) is None else r[k] for r in rws],float)
    n=len(recs)
    for mu_,key_ in ((0.10,'mu10'),(0.02,'mu02')):
        c=[]
        for r in recs:
            x=stat(r['state'],r['support'],mu=mu_); c.append(np.nan if x is None else x['s'])
        c=np.array(c); T[key_]=dict(feasible=int((~np.isnan(c)).sum()),n=n,peak=float(np.nanmax(c)),frame=int(np.nanargmax(c)))
    for mu in (50,40,30):
        c=col('s%d'%mu); T['mu%d'%mu]=dict(feasible=int((~np.isnan(c)).sum()),n=n,peak=float(np.nanmax(c)),frame=int(np.nanargmax(c)))
    # heavier robot (+10 %)
    c=[]
    for r in recs:
        x=stat(r['state'],r['support'],mu=0.5,mass_scale=1.10); c.append(np.nan if x is None else x['s'])
    c=np.array(c); T['mass110']=dict(feasible=int((~np.isnan(c)).sum()),peak=float(np.nanmax(c)))
    for k in ('margin','self','env','pad'):
        c=col(k); i=int(np.nanargmin(c)); T[k]=dict(min=float(c[i]),frame=i)
    T['selfpair']=rows[T['self']['frame']]['selfpair']; T['envkey']=rows[T['env']['frame']]['envkey']
    T['pen']=float(col('pen').max()); T['below10']=int((col('self')<10).sum()); T['envbelow5']=int((col('env')<5).sum())
    i=np.unravel_index(sp.argmax(),sp.shape); T['speedmax']=dict(v=float(sp.max()),frame=int(i[0]),joint=JN[i[1]])
    Q=np.array([r['state'].q for r in recs]); T['qlo']=Q.min(0); T['qhi']=Q.max(0)
    T['limit_margin']=float(np.min(np.minimum(Q-QLO,QHI-Q)[:,[j for j in range(22) if j not in (0,1,11,21)]]))
    # mid-interval samples
    mid=midframes(recs); mrows,_=seq_metrics(mid,exact=True)
    c=col('s50',mrows); T['mid']=dict(n=len(mid),feasible=int((~np.isnan(c)).sum()),peak=float(np.nanmax(c)),self=float(col('self',mrows).min()),env=float(col('env',mrows).min()))
    # adjacent frames per joint over the used angle range
    adj=[]
    for j in range(22):
        b,_=adjacency.sweep(j,T['qlo'][j],T['qhi'][j]); adj.append((float(b[0]),b[1],None if b[2] is None else float(b[2])))
    T['adj']=adj; T['adjmin']=min(a[0] for a in adj)
    nr=0.0
    for r in recs:
        st=r['state']
        for (l,k),g in K.G.items():
            R_,t_=st.w[l]; pw=g.v@R_.T+t_; m=(pw[:,1]<-280)&(pw[:,2]<420)
            if m.any(): nr=max(nr,float((-280-pw[m][:,1]).max()))
    T['next_riser_mm']=nr
    log(label,'next riser intrusion',round(nr,1),'mu10',T['mu10'],'mu02',T['mu02'])
    log(label,'statics',T['mu50'],T['mu40'],T['mu30'],'mass110',T['mass110'],'margin',T['margin'],'self',T['self'],T['selfpair'],'env',T['env'],T['envkey'],'pad',T['pad'],'pen',T['pen'],'speed',T['speedmax'],'mid',T['mid'],'adjmin',T['adjmin'],'limit margin',T['limit_margin'])
    if sim:
        states=[r['state'] for r in recs]; S={}
        ff=[]
        for r_ in recs:
            x_=stat(r_['state'],r_['support'],mu=0.02); ff.append(np.zeros(22) if x_ is None else x_['tau'])
        ff=np.array(ff); ff[:,[11,21]]=0; T['ff']=ff
        from scipy.ndimage import gaussian_filter1d
        ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
        variants={'noff':dict(noff=True),'stall':dict(lim_scale=3.0),'nominal':{},'mu035':dict(mu=0.35),'mu070':dict(mu=0.7),'step205':dict(step_h=205.0),'step215':dict(step_h=215.0),'mass110':dict(mass_scale=1.1),
                  'near5':dict(y_offset=-5.0),'far5':dict(y_offset=5.0),'weak85':dict(lim_scale=0.85),'soft60':dict(kp_scale=0.6)}
        for name,kw in variants.items():
            kw=dict(kw); noff=kw.pop('noff',False)
            rec=mj.simulate(states,tau_ff=None if noff else ff,**kw); res=mj.judge(rec,states); S[name]=dict(res=res,rec=rec if name in('nominal','stall') else None)
            tt_=rec['t']; er_=np.linalg.norm(rec['root']-np.array([states[min(n-1,max(0,int(round(t_*HZ))))].t for t_ in tt_]),axis=1); bad_=np.where(er_>60)[0]; res['fall_t']=float(tt_[bad_[0]]) if len(bad_) else None
            log('  sim',name,{k:(round(v,2) if isinstance(v,float) else v) for k,v in res.items()})
        T['sim']=S
        # clearance of the simulated (not the planned) motion
        ss=mj.sim_states(S['nominal']['rec']); tt=S['nominal']['rec']['t']
        srecs=[]
        for st,t in zip(ss,tt):
            i=min(n-1,max(0,int(round(t*HZ)))); srecs.append(dict(state=st,support=recs[i]['support'],contacts=recs[i]['contacts'],phase=recs[i]['phase']))
        srows,_=seq_metrics(srecs,exact=True,mus=(0.5,))
        T['simclear']=dict(self=float(col('self',srows).min()),env=float(col('env',srows).min()),pen=float(col('pen',srows).max()))
        log('  sim clearance',T['simclear'])
    return T
if __name__=='__main__':
    which=sys.argv[1]
    recs=baseline_records() if which=='base' else pickle.load(open(which,'rb'))
    T=run_all(recs,which); pickle.dump(T,open(sys.argv[2],'wb'))
