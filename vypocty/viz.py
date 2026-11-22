import sys; sys.path.insert(0,'/home/claude/sim')
from statics import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
CH_L=[22,2,3,4,5,6,7]; 
def chain_pts(w,side):
    o=0 if side=='L' else 10
    hip=[pt(w,PAR[j],P[j]) for j in (4+o,5+o,6+o)]
    s=1 if side=='L' else -1
    toe=pt(w,7+o,[s*54,-70,0]); heel=pt(w,7+o,[s*54,50,0]); ank=pt(w,7+o,[s*54,0,30])
    leg=np.array(hip+[ank,heel,toe,ank])
    sh=[pt(w,PAR[j],P[j]) for j in (8+o,9+o,10+o)]
    palm=pt(w,10+o,[s*146,-12,205])
    arm=np.array(sh+[palm])
    return leg,arm
def draw(ax,w,contacts=None,title='',forces=None,c=None):
    ax.plot([400,0,0,-300],[0,0,210,210],'k-',lw=1)
    for side,col in (('R','tab:red'),('L','tab:blue')):
        leg,arm=chain_pts(w,side)
        ax.plot(leg[:,1],leg[:,2],'-o',color=col,ms=2,lw=1.2); ax.plot(arm[:,1],arm[:,2],'-o',color=col,ms=2,lw=1.2,alpha=.7)
    tor=np.array([pt(w,22,p) for p in ([0,1,278],[0,0,482],[0,5,518])]); ax.plot(tor[:,1],tor[:,2],'k-',lw=2)
    head=pt(w,1,[0,0,600]); ax.plot(head[1],head[2],'ko',ms=6,mfc='none')
    if c is not None: ax.plot(c[1],c[2],'g*',ms=7); ax.plot([c[1],c[1]],[c[2],0],'g:',lw=.6)
    if forces:
        for k,f in forces.items():
            p=contacts[k]; ax.arrow(p[1],p[2],f[1]*4,f[2]*4,color='m',width=.8,head_width=5)
    ax.set_aspect('equal'); ax.set_xlim(330,-330); ax.set_ylim(-10,720); ax.set_title(title,fontsize=7); ax.axis('off')
def strip(poses,frames,fn,sol=True,ncol=8):
    n=len(frames); nr=(n+ncol-1)//ncol
    fig,axs=plt.subplots(nr,ncol,figsize=(ncol*2.4,nr*2.8)); axs=np.atleast_2d(axs)
    for a in axs.flat: a.axis('off')
    for i,f in enumerate(frames):
        p=poses[f]; w=fk(p['q'],p['rt']); r=solve(w,p['contacts']) if sol else None
        t=f"{f} ph{p['phase']}"
        if r: 
            j=int(np.argmax(np.where(np.isin(np.arange(22),[11,21]),0,r['ratio'])))
            t+=f" s={r['s']:.2f} j{j}"
        draw(axs.flat[i],w,p['contacts'],t,r['forces'] if r else None,com(w))
    fig.tight_layout(); fig.savefig(fn,dpi=70); plt.close(fig)
if __name__=='__main__':
    C=json.load(open(W+'r9ClimbData.json'))
    strip(C['poses'],list(range(0,480,20)),'base_a.png'); strip(C['poses'],list(range(480,911,18)),'base_b.png')
