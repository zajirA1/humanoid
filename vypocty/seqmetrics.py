"""Uniform records + metrics for baseline / new sequences."""
import sys; sys.path.insert(0,'/home/claude/sim')
from fullpass import *
import fcl
FOOTN={'L':'leftFoot','R':'rightFoot'}; KNEEN={'L':'leftKnee','R':'rightKnee'}; PALMN={'L':'leftPalm','R':'rightPalm'}
def near_mask(recs,name,pad):
    on=np.array([name in r['contacts'] for r in recs]); out=on.copy()
    idx=np.where(on)[0]
    for i in idx: out[max(0,i-pad):i+pad+1]=True
    return out
def contact_points(st,contacts):
    """representative world contact point per touching end effector (for the viewer)"""
    out={}
    for n in contacts:
        l=LINKOF[n]
        if 'Palm' in n: c=st.pt(l,PADC[l]); out[n]=[round(float(c[0]),2),round(float(c[1]),2),STEP_H]
        elif 'Knee' in n: c=st.pt(l,C1[l]); out[n]=[round(float(c[0]),2),round(float(c[1]),2),STEP_H]
        else:
            pp=patch(st,n,tol=1.5)
            if not pp:
                sp=np.array([st.pt(l,p) for p in SOLEP[l]]); pp=[p for p in sp if p[2]<=sp[:,2].min()+1.0]
            c=np.mean(pp,axis=0); h=STEP_H if c[2]>100 else 0.0; out[n]=[round(float(c[0]),2),round(float(c[1]),2),h]
    return out
def seq_metrics(recs,exact=True,mus=(0.5,0.4,0.3),verbose=False):
    n=len(recs); nearF={sd:near_mask(recs,FOOTN[sd],8) for sd in 'LR'}; nearK={sd:near_mask(recs,KNEEN[sd],14) for sd in 'LR'}; nearP={sd:near_mask(recs,PALMN[sd],6) for sd in 'LR'}
    rows=[]
    for i,rec in enumerate(recs):
        st=rec['state']; sup=rec['support']; row=dict(phase=rec['phase'])
        for mu in mus:
            r=stat(st,sup,mu=mu); row['s%d'%round(mu*100)]=None if r is None else r['s']
            if mu==mus[0]: row['r']=r
        row['margin']=margin(st,sup)
        if exact:
            K.place(st); d,pair,pts=K.min_dist(st,cutoff=14,placed=True); row['self']=d; row['selfpair']=pair; row['selfpts']=pts
            ex=set()
            for sd in 'LR':
                if nearF[sd][i]: ex.add((FOOT[sd],'body'))
                if nearK[sd][i]: ex.add((SHIN[sd],'sleeve'))
            e,ek,ep=K.env_dist(st,exclude=ex,cutoff=25,placed=True); row['env']=e; row['envkey']=ek; row['envpt']=ep
            pad=1e9
            for sd in 'LR':
                if nearP[sd][i]: continue
                c=st.pt(ARM[sd],refpt(sd,'P')); dz=c[2]-STEP_H; dy=max(c[1],-280-c[1]); d_=(math.hypot(dy,dz) if (dy>0 and dz>0) else max(dy,dz))-PAD_R; pad=min(pad,d_,c[2]-PAD_R)
            row['pad']=pad
            # functional geometry must not sink into its surface / hit the riser
            pen=0.0
            for sd in 'LR':
                g=K.G[(FOOT[sd],'body')]; R_,t_=st.w[FOOT[sd]]; pw=g.v@R_.T+t_
                y=pw[:,1]; z=pw[:,2]; inside=(y<0)&(y>-280)&(z<STEP_H)
                if inside.any(): pen=max(pen,float(np.minimum(-y[inside],STEP_H-z[inside]).max()))
                pen=max(pen,float(-z.min()))
            row['pen']=pen
        rows.append(row)
    q=np.array([r['state'].q for r in recs]); sp=np.abs(np.diff(q,axis=0))*HZ
    return rows,sp
def summarize(rows,sp,label=''):
    def col(k): return np.array([np.nan if r.get(k) is None else r[k] for r in rows],float)
    out={}
    for k in ('s50','s40','s30'):
        c=col(k); out[k]=(float(np.nanmax(c)),int(np.nanargmax(c)),int(np.isnan(c).sum()))
    for k in ('margin','self','env','pad'):
        if k in rows[0]:
            c=col(k); out[k]=(float(np.nanmin(c)),int(np.nanargmin(c)))
    if 'pen' in rows[0]: c=col('pen'); out['pen']=(float(np.nanmax(c)),int(np.nanargmax(c)))
    i=np.unravel_index(sp.argmax(),sp.shape); out['speed']=(float(sp.max()),int(i[0]),JN[i[1]])
    print(label,{k:(tuple(round(x,3) if isinstance(x,float) else x for x in v)) for k,v in out.items()})
    return out
def baseline_records():
    return [dict(state=REFS[i].st,support=set(REFS[i].contacts),contacts=set(REFS[i].contacts),phase=REFS[i].phase) for i in range(NO)]
if __name__=='__main__':
    recs=baseline_records(); t=time.time(); rows,sp=seq_metrics(recs); print('t',time.time()-t)
    pickle.dump((rows,sp),open('base_metrics.pkl','wb')); summarize(rows,sp,'BASELINE')
