import sys; sys.path.insert(0,'/home/claude/sim')
from planner import *
from scipy.optimize import minimize
C=json.load(open(W+'r9ClimbData.json'))
E_L=np.array([54,-30.5,80.3]); E_R=np.array([-54,-30.5,80.3])
def tip_patch(s,name):
    link=LINKOF[name]; e=E_L if link==5 else E_R
    return [s.pt(link,e+np.array([dx,0,0])) for dx in (-6,6)]
def stat(s,support,mu=0.5):
    extra=[]; names=[]
    for n in support:
        if 'Knee' in n: extra+=[(LINKOF[n],p,n) for p in tip_patch(s,n)]
        else: names.append(n)
    return statics(s,names,extra_pts=extra,mu=mu)
def pose_opt(f,var_palms=False,verbose=True,fixpalm=None):
    p=C['poses'][f]; s0=State.from_pose(p); sup=list(p['contacts'])
    r0=stat(s0,sup)
    tgt={}
    for n in sup:
        l=LINKOF[n]
        if 'Knee' in n: tgt[n]=(l,(E_L if l==5 else E_R),s0.pt(l,E_L if l==5 else E_R))
        if 'Palm' in n: tgt[n]=(l,PADC[l],s0.pt(l,PADC[l]))
    pel0=s0.pel(); pit0=s0.pitch()
    def build(v):
        s=s0.copy(); tasks=[]
        for n,(l,pl,pw) in tgt.items():
            pw=pw.copy()
            if var_palms and 'Palm' in n:
                k=6 if n=='leftPalm' else 8; pw[:2]+=v[k:k+2]*10
            tasks.append(T_point(l,pl,pw,200))
        tasks.append(T_pel(pel0+v[:3]*10,30)); 
        tasks.append(T_torso(Rz(v[5]*3)@Ry(v[4]*3)@Rx(pit0+v[3]*5),30))
        wq=np.full(22,0.02); wq[12:18]=2.0 if 'rightFoot' not in sup and 'rightKnee' not in sup else 0.02
        wq[[0,1,11,21]]=5
        solve_ik(s,tasks,qref=s0.q,wq=wq,qlo=QLO,qhi=QHI,iters=25)
        err=0
        for n,(l,pl,pw) in tgt.items():
            pw=pw.copy()
            if var_palms and 'Palm' in n:
                k=6 if n=='leftPalm' else 8; pw[:2]+=v[k:k+2]*10
            err=max(err,np.abs(s.pt(l,pl)-pw).max())
        return s,err
    def cost(v):
        s,err=build(v); r=stat(s,sup)
        c=(r['s'] if r else 3.0)+ (err>0.3)*err*0.5
        return c
    n=10 if var_palms else 6
    res=minimize(cost,np.zeros(n),method='Nelder-Mead',options=dict(xatol=0.03,fatol=0.002,maxiter=600,initial_simplex=np.vstack([np.zeros(n),np.eye(n)])))
    s,err=build(res.x); r=stat(s,sup)
    if verbose:
        print(f,'orig s',None if r0 is None else round(r0['s'],3),JN[r0['jmax']] if r0 else '','-> opt',round(r['s'],3),JN[r['jmax']],'err',round(err,2),'dpel',(res.x[:3]*10).round(0),'dpitch',round(res.x[3]*5,1),'roll/yaw',(res.x[4:6]*3).round(1),'palm shift',(res.x[6:]*10).round(0) if var_palms else '', {k:round(float(v[2]),1) for k,v in r['forces'].items()})
    return s,r
if __name__=='__main__':
    for f in (258,300,330):
        pose_opt(f); pose_opt(f,var_palms=True)
