import sys; sys.path.insert(0,'/home/claude/sim')
from geom import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
def show(keys_links,fn,views=((20,-60),(20,30),(80,-90),(0,0)),others=None):
    fig=plt.figure(figsize=(4.2*len(views),4.2))
    its=[it for it in ITEMS if (it['key'],it['link']) in keys_links]
    oth=[it for it in ITEMS if others and it['link'] in others and (it['key'],it['link']) not in keys_links]
    allv=np.vstack([it['v'] for it in its]); c=(allv.min(0)+allv.max(0))/2; r=(allv.max(0)-allv.min(0)).max()/2*1.1
    for n,(el,az) in enumerate(views):
        ax=fig.add_subplot(1,len(views),n+1,projection='3d')
        for it in oth:
            ax.add_collection3d(Poly3DCollection(it['v'][it['f']],facecolor=(.6,.6,.6,.15),edgecolor=(.4,.4,.4,.08),lw=.2))
        for it in its:
            ax.add_collection3d(Poly3DCollection(it['v'][it['f']],facecolor=(.3,.6,.5,.75),edgecolor=(0,.2,.2,.4),lw=.3))
        ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r); ax.set_zlim(c[2]-r,c[2]+r); ax.view_init(el,az); ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z'); ax.tick_params(labelsize=6)
    fig.tight_layout(); fig.savefig(fn,dpi=65); plt.close(fig)
if __name__=='__main__':
    show({('r11_clear_L_shoulder_pitch_ram',8)},'p_shp.png',others={8})
    show({('r11_clear_L_shoulder_roll_ram',9)},'p_shr.png',others={9})
    show({('r8_L_elbow_ram',10)},'p_elb.png',others={10})
