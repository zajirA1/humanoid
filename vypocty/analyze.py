import sys; sys.path.insert(0,'/home/claude/sim')
from planner import *
from geom import ITEMS
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
# subsampled vertex clouds per link for quick environment clearance
CLOUD={}
for it in ITEMS:
    CLOUD.setdefault(it['link'],[]).append(it['v'])
CLOUD={k:np.unique(np.round(np.vstack(v),0),axis=0) for k,v in CLOUD.items()}
for l in (10,20):  # palm pads
    pass
def env_dist(pw):
    """distance of world points to solid (floor z<0 ; step y<=0 & z<=210). negative = inside"""
    y=pw[:,1]; z=pw[:,2]
    dfloor=z
    dy=y; dz=z-STEP_H            # outside step if y>0 or z>210
    out=np.where((dy>0)&(dz>0),np.hypot(dy,dz),np.maximum(dy,dz))
    return np.minimum(dfloor,out)
FUNC={'leftFoot':[7],'rightFoot':[17],'leftKnee':[5],'rightKnee':[15],'leftPalm':[10],'rightPalm':[20]}
def env_clear(st,ignore_links=()):
    best=(1e9,None)
    for l,v in CLOUD.items():
        if l in ignore_links: continue
        R,t=st.w[l]; d=env_dist(v@R.T+t).min()
        if d<best[0]: best=(d,l)
    return best
def side_pts(st,side):
    o=0 if side=='L' else 10; s=1 if side=='L' else -1
    hip=[st.piv[j] for j in (4+o,5+o,6+o)]
    toe=st.pt(7+o,[s*54,-70,0]); heel=st.pt(7+o,[s*54,50,0]); ank=st.pt(7+o,[s*54,0,30])
    leg=np.array(hip+[ank,heel,toe,ank]); arm=np.array([st.piv[j] for j in (8+o,9+o,10+o)]+[st.pt(10+o,[s*146,-12,205])])
    sl=np.array([st.pt(5+o,[s*54,-32,82]),st.pt(5+o,[s*54,-32,122])])
    return leg,arm,sl
def draw(ax,st,title='',res=None,view='side'):
    a,b=(1,2) if view=='side' else (0,2)
    if view=='side': ax.plot([400,0,0,-280,-280],[0,0,210,210,150],'k-',lw=1)
    else: ax.plot([-330,330],[210,210],'k-',lw=1); ax.plot([-330,330],[0,0],'k-',lw=.5)
    for side,col in (('R','tab:red'),('L','tab:blue')):
        leg,arm,sl=side_pts(st,side)
        ax.plot(leg[:,a],leg[:,b],'-o',color=col,ms=2,lw=1.2); ax.plot(arm[:,a],arm[:,b],'-o',color=col,ms=2,lw=1.2,alpha=.7)
        ax.plot(sl[:,a],sl[:,b],'-',color='orange',lw=3,alpha=.8)
    tor=np.array([st.pt(22,p) for p in ([0,1,278],[0,0,482],[0,5,518])]); ax.plot(tor[:,a],tor[:,b],'k-',lw=2)
    head=st.pt(1,[0,0,600]); ax.plot(head[a],head[b],'ko',ms=6,mfc='none')
    c=st.com(); ax.plot(c[a],c[b],'g*',ms=7); ax.plot([c[a],c[a]],[c[b],0],'g:',lw=.6)
    if res:
        for k,f in res['forces'].items():
            pp=patch(st,k); 
            if pp: p=np.mean(pp,axis=0); ax.arrow(p[a],p[b],f[a]*4,f[b]*4,color='m',width=.8,head_width=5)
    ax.set_aspect('equal'); 
    if view=='side': ax.set_xlim(330,-330)
    else: ax.set_xlim(-330,330)
    ax.set_ylim(-10,720); ax.set_title(title,fontsize=7); ax.axis('off')
def strip(frames,idx,fn,ncol=8,view='side'):
    n=len(idx); nr=(n+ncol-1)//ncol
    fig,axs=plt.subplots(nr,ncol,figsize=(ncol*2.4,nr*2.8)); axs=np.atleast_2d(axs)
    for a in axs.flat: a.axis('off')
    for i,f in enumerate(idx):
        fr=frames[f]; st=fr['state']; r=statics(st,sorted(fr['support']))
        t=f"{f} ph{fr['phase']} "+('X' if r is None else f"s={r['s']:.2f} j{r['jmax']}")
        draw(axs.flat[i],st,t,r,view)
    fig.tight_layout(); fig.savefig(fn,dpi=70); plt.close(fig)
def report(frames,phases,quiet=False):
    out=[]
    for f,fr in enumerate(frames):
        st=fr['state']; r=statics(st,sorted(fr['support']))
        miss=[n for n in fr['support'] if not patch(st,n)]
        func=[l for n in fr['support'] for l in FUNC[n]]
        ec=env_clear(st,ignore_links=())
        out.append(dict(f=f,ph=fr['phase'],s=None if r is None else r['s'],j=None if r is None else r['jmax'],miss=miss,env=ec,res=r))
    if not quiet:
        ph=np.array([o['ph'] for o in out]); ss=np.array([o['s'] if o['s'] is not None else np.nan for o in out])
        for k,name in enumerate(phases):
            m=np.where(ph==k)[0]; 
            if len(m)==0: continue
            bad=[i for i in m if out[i]['s'] is None]; mi=[i for i in m if out[i]['miss']]
            sm=ss[m]; 
            if np.all(np.isnan(sm)): print(k,name,'ALL INFEASIBLE'); continue
            i=m[np.nanargmax(sm)]; e=min(out[j]['env'][0] for j in m)
            print(f"{k:2d} {name:28s} f{m[0]}-{m[-1]} peak {np.nanmax(sm):.3f} @f{i} {JN[out[i]['j']]:30s} infeas {len(bad)} miss {len(mi)} envmin {e:.1f}")
        print('PEAK',np.nanmax(ss),'infeasible',int(np.isnan(ss).sum()))
    return out
if __name__=='__main__':
    import pickle; fr,ph=pickle.load(open(sys.argv[1],'rb'))
    report(fr,ph)
    n=len(fr); idx=list(range(0,n,max(1,n//40)))
    strip(fr,idx,sys.argv[1].replace('.pkl','_side.png'))
