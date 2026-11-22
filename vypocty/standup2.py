import sys; sys.path.insert(0,'/home/claude/sim')
from standup import *
st_init=r0.st
def costA(x,yp,full=False):
    y,z,pitch=x[0]*10,x[1]*10,x[2]*5
    palms={'L':np.array([146,yp,STEP_H+PAD_R]),'R':np.array([-146,yp,STEP_H+PAD_R])}
    st,res=pose(z,y,pitch,0,0,st_init,palms)
    r=stat(st,SUP,mu=0.4); m=margin(st,SUP)
    J=(r['s'] if r else 3+max(0,-m)/50)+0.1*max(0,res-0.2)+0.004*max(0,15-m)**2
    if full: return J,st,r,m,res
    return J
for yp in (-150,-125,-100,-75):
    best=None
    for x0 in ([-4,38,10],[-2,36,8],[-6,40,12],[0,37,6]):
        sim=np.vstack([x0]+[np.array(x0)+np.eye(3)[k] for k in range(3)])
        rs=minimize(lambda v:costA(v,yp),np.array(x0,float),method='Nelder-Mead',options=dict(xatol=0.02,fatol=0.001,maxiter=200,initial_simplex=sim))
        if best is None or rs.fun<best.fun: best=rs
    J,st,r,m,res=costA(best.x,yp,full=True)
    print('palms y',yp,'J',round(J,3),'s',round(r['s'],3) if r else None,JN[r['jmax']] if r else '','pel y,z',(best.x[:2]*10).round(0),'pitch',round(best.x[2]*5),'m',round(m),'res',round(res,2),'knee',round(st.q[5]),'hip',round(-st.q[4]),'ank',round(st.q[6]),'elbow',round(-st.q[10]),'sh',round(st.q[8]),flush=True)
