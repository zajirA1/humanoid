import sys; sys.path.insert(0,'/home/claude/sim')
from run_retarget import *
from scipy.interpolate import PchipInterpolator
def logm(R):
    c=(np.trace(R)-1)/2; th=math.acos(max(-1,min(1,c)))
    if th<1e-9: return np.zeros(3)
    return th/(2*math.sin(th))*np.array([R[2,1]-R[1,2],R[0,2]-R[2,0],R[1,0]-R[0,1]])
def interp_v(keys,vk,n):
    keys=np.array(keys); V=np.array([vk[k] for k in keys]); out=np.zeros((n,6))
    for c in range(6): out[:,c]=PchipInterpolator(keys,V[:,c],extrapolate=True)(np.clip(np.arange(n),keys[0],keys[-1]))
    return out
def limb_residuals(st,fr):
    """target-minus-actual vectors of the contact end effectors that are off target"""
    r=fr.ref; out=[]
    for sd in 'LR':
        mode=leg_mode(sd,fr.src)
        if mode=='foot' and ('leftFoot' if sd=='L' else 'rightFoot') in r.contacts:
            d=(r.foot[sd][1]+fr.foot_off[sd])-st.pt(FOOT[sd],refpt(sd,'A'))
            if np.linalg.norm(d)>0.08: out.append(d)
        if mode=='knee':
            k=SHIN[sd]; d=(r.c1[sd]+fr.knee_off[sd])-st.pt(k,C1[k])
            if np.linalg.norm(d)>0.08: out.append(d)
        if fr.src<=PALM_END[sd] and ('leftPalm' if sd=='L' else 'rightPalm') in r.contacts:
            d=(r.palm[sd]+fr.palm_off[sd])-st.pt(ARM[sd],refpt(sd,'P'))
            if np.linalg.norm(d)>0.08: out.append(d)
    return out
def full_pass(R,v,f0,f1,st0=None):
    """IK for every frame f0..f1 with decaying offsets at leg-mode switches. returns list of (Frame,State)"""
    st=REFS[int(R.src[f0])].st.copy() if st0 is None else st0.copy(); out=[]
    dec={sd:None for sd in 'LR'}; prev_mode={sd:leg_mode(sd,int(R.src[f0])) for sd in 'LR'}
    for f in range(f0,f1+1):
        fr=R.frame(f); i=fr.src
        for sd in 'LR':
            o=0 if sd=='L' else 10; m=leg_mode(sd,i)
            if m!=prev_mode[sd] and out:
                pf,ps=out[-1]; pr=pf.ref
                if m=='approach' and False:
                    k=SHIN[sd]; dec[sd]=dict(kind='approach',t0=f,dp=ps.pt(k,C1[k])-(pr.c1[sd]+pf.knee_off[sd]),dz=ps.vec(k,EZ)-pr.shz[sd],dq=ps.q[[6+o,7+o]]-pr.q[[6+o,7+o]])
                elif m=='foot' and prev_mode[sd]=='knee' and False:
                    fo=FOOT[sd]; Rf,pA=pr.foot[sd]
                    dec[sd]=dict(kind='foot',t0=f,dp=ps.pt(fo,refpt(sd,'A'))-pA,dr=logm(ps.w[fo][0]@Rf.T))
                else: dec[sd]=None
            prev_mode[sd]=m
            d=dec[sd]
            if d is not None:
                u=(f-d['t0']+1)/NDEC
                if u>=1: dec[sd]=None
                else:
                    w=1-smooth(u)
                    if d['kind']=='approach' and m=='approach':
                        fr.knee_off[sd]=fr.knee_off[sd]+d['dp']*w; z=fr.ref.shz[sd]+d['dz']*w; fr.shz[sd]=z/np.linalg.norm(z)
                        fr.q_off[[6+o,7+o]]=d['dq']*w
                    elif d['kind']=='foot' and m=='foot':
                        fr.foot_off[sd]=fr.foot_off[sd]+d['dp']*w; fr.foot_rot[sd]=expm(d['dr']*w)
        st=make_state(fr,v[f],fr.ref.st); rc,rsw=limb_ik(st,fr,both=True,iters=40)
        vsave=v[f].copy()
        if rc>0.12:
            # reachability projection: slide the pelvis by the contact residuals (a straight limb cannot reach)
            for it in range(8):
                res_=limb_residuals(st,fr)
                if not res_ or max(np.linalg.norm(r_) for r_ in res_)<0.08: break
                d=np.sum(res_,axis=0)*1.1; nd=np.linalg.norm(d)
                if nd>5: d*=5/nd
                vt=v[f].copy(); vt[:3]+=d/SC[:3]; st2=make_state(fr,vt,fr.ref.st); rc2,rsw2=limb_ik(st2,fr,both=True,iters=40)
                if rc2>=rc or np.linalg.norm((vt-vsave)[:3]*SC[:3])>16: break
                v[f]=vt; st=st2; rc=rc2; rsw=rsw2
            fr.projected=True
        out.append((fr,st.copy())); fr.rc=rc; fr.rsw=rsw; fr.v=v[f].copy()
    return out
def metrics(seq,exact=True,mus=(0.5,0.4,0.3)):
    rows=[]
    for n,(fr,st) in enumerate(seq):
        row=dict(src=fr.src,phase=fr.ref.phase,rc=fr.rc,rsw=fr.rsw,support=sorted(fr.support))
        for mu in mus:
            r=stat(st,fr.support,mu=mu); row['s%d'%round(mu*100)]=None if r is None else r['s']
            if mu==mus[0]: row['r']=r
        row['margin']=margin(st,fr.support)
        if exact:
            K.place(st); d,pair,pts=K.min_dist(st,cutoff=14,placed=True); row['self']=d; row['selfpair']=pair
            da,paira,_=K.min_dist(st,pairs=K.ADJ,cutoff=6,placed=True); row['adj']=da; row['adjpair']=paira
            ex=set(); riser=1e9
            for sd in 'LR':
                foot=('leftFoot' if sd=='L' else 'rightFoot'); knee=('leftKnee' if sd=='L' else 'rightKnee')
                if leg_mode(sd,fr.src)=='foot' and foot in fr.ref.contacts:
                    ex.add((FOOT[sd],'body'))
                    # a planted foot may still not touch the riser / sink into the surface
                    g=K.G[(FOOT[sd],'body')]; R_,t_=st.w[FOOT[sd]]; pw=g.v@R_.T+t_
                    if pw[:,1].min()>0: riser=min(riser,pw[pw[:,2]<STEP_H][:,1].min() if np.any(pw[:,2]<STEP_H) else 1e9)
                k0,k1=KNEE[sd]
                if k0-10<=fr.src<=k1+10: ex.add((SHIN[sd],'sleeve'))
            e,ek,_=K.env_dist(st,exclude=ex,cutoff=25,placed=True); row['env']=e; row['envkey']=ek; row['riser']=riser
            # palm pads (spheres r=12) while not in contact
            pad=1e9
            for sd in 'LR':
                c=st.pt(ARM[sd],refpt(sd,'P')); name=('leftPalm' if sd=='L' else 'rightPalm')
                if name not in fr.ref.contacts:
                    dz=c[2]-STEP_H; dy=max(c[1],-280-c[1]); d=(math.hypot(dy,dz) if (dy>0 and dz>0) else max(dy,dz))-PAD_R; pad=min(pad,d,c[2]-PAD_R)
            row['pad']=pad
        rows.append(row)
    return rows
