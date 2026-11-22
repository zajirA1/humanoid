import sys; sys.path.insert(0,'/home/claude/sim')
from retarget import *
from geom import ITEMS
from scipy.spatial import ConvexHull
# coarse clouds for fast environment clearance (functional geometry removed)
def _sample(v,f,h=3.0):
    pts=[v]
    tri=v[f]; e=np.maximum.reduce([np.linalg.norm(tri[:,0]-tri[:,1],axis=1),np.linalg.norm(tri[:,1]-tri[:,2],axis=1),np.linalg.norm(tri[:,2]-tri[:,0],axis=1)])
    for t,L in zip(tri[e>h],e[e>h]):
        n=int(min(40,math.ceil(L/h))); 
        for i in range(n+1):
            for j in range(n+1-i):
                pts.append((t[0]*i+t[1]*j+t[2]*(n-i-j))[None]/n)
    return np.vstack(pts)
CL={}; CLS={}
for it in ITEMS:
    (CLS if it['key']=='r11_climb_TPU' else CL).setdefault(it['link'],[]).append(_sample(it['v'],it['f']))
CL={k:np.unique(np.round(np.vstack(v)/1.5)*1.5,axis=0) for k,v in CL.items()}
CLS={k:np.unique(np.round(np.vstack(v)/1.5)*1.5,axis=0) for k,v in CLS.items()}
def _dist(pw):
    y=pw[:,1]; z=pw[:,2]; dy=np.maximum(y,-280-y); dz=z-STEP_H
    out=np.where((dy>0)&(dz>0),np.hypot(dy,dz),np.maximum(dy,dz))
    return min(z.min(),out.min())
def env_fast(st,fr):
    best=1e9; bl=None
    for l,v in CL.items():
        if l in (7,17):
            sd='L' if l==7 else 'R'; foot=('leftFoot' if sd=='L' else 'rightFoot')
            if leg_mode(sd,fr.src)=='foot' and any(a-8<=fr.src<=b+8 for a,b in IV[foot]): continue
        R,t=st.w[l]; d=_dist(v@R.T+t)
        if d<best: best=d; bl=l
    for l,v in CLS.items():
        sd='L' if l==5 else 'R'; k0,k1=KNEE[sd]
        if k0-14<=fr.src<=k1+14: continue
        R,t=st.w[l]; d=_dist(v@R.T+t)
        if d<best: best=d; bl=(l,'sleeve')
    return best,bl
def margin(st,support):
    names,extra=support_pts(st,support); pts=[p[:2] for n in names for p in patch(st,n)]+[p[1][:2] for p in extra]
    if len(pts)<3: return -50.0
    P=np.array(pts); c=st.com()[:2]
    try: h=ConvexHull(P)
    except Exception: return -50.0
    # hull equations: n.x + d <= 0 inside
    return float(-(h.equations[:,:2]@c+h.equations[:,2]).max())
SC=np.array([10,10,10,4,4,4.0])
def make_state(fr,v,st_init):
    r=fr.ref; st=st_init.copy(); e=euler(r.R)+v[3:6]*SC[3:]; R=Reul(e); pel=r.pel+v[:3]*SC[:3]
    st.R=R; st.t=pel-R@PEL; st.update()
    return st
def evaluate(fr,v,st_init,mu=0.4,full=False,arm_free=None):
    st=make_state(fr,v,st_init); rc,rsw=limb_ik(st,fr,arm_free=arm_free,both=True); res=rc
    r=stat(st,fr.support,mu=mu); env,el=env_fast(st,fr); m=margin(st,fr.support)
    J=(r['s'] if r else 3.0+max(0,-m)/50.0)+0.02*max(0,6-env)**2+0.5*max(0,rc-0.15)+0.02*max(0,rsw-1.0)+0.004*max(0,12-m)**2
    if full: return dict(J=J,st=st,r=r,env=env,envlink=el,res=res,rsw=rsw,margin=m)
    return J
def optimise(fr,v0,st_init,vprev=None,lam=0.0,reg=2e-4,maxiter=220,step=0.6,arm_free=None,extra=None):
    def cost(v):
        J=evaluate(fr,v,st_init,arm_free=arm_free)+reg*float(v@v)
        if vprev is not None: J+=lam*float((v-vprev)@(v-vprev))
        if extra is not None: J+=extra(fr,v,st_init)
        return J
    sim=np.vstack([v0]+[v0+step*np.eye(6)[k] for k in range(6)])
    res=minimize(cost,v0,method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.001,maxiter=maxiter,initial_simplex=sim))
    return res.x,res.fun
