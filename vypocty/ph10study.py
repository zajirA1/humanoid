import sys; sys.path.insert(0,'/home/claude/sim')
from run_retarget import *
frames=[625,627,630,634]; sup={'rightFoot','leftPalm','rightPalm'}
for name,(lo,ro) in {'P0':((0,0),(0,0)),'P1':((0,30),(0,30)),'P2':((0,60),(0,60)),'P3':((0,90),(0,90)),'P4':((-20,45),(20,45))}.items():
    out=[]
    for i in frames:
        fr=Frame(i,sup,palm_off={'L':np.array([lo[0],lo[1],0.]),'R':np.array([ro[0],ro[1],0.])})
        st0=REFS[i].st; best=None
        for v0 in (np.array([1,1,-1,-2,0,0.]),np.array([-1,-1,1,1,-1,-2.]),np.array([2,2,0,-2,1,2.])):
            v,J=optimise(fr,v0,st0,maxiter=220,step=0.8)
            if best is None or J<best[1]: best=(v,J)
        e=evaluate(fr,best[0],st0,full=True); out.append((i,round(e['r']['s'],3) if e['r'] else None,e['r']['jmax'] if e['r'] else None,round(e['res'],1),round(e['rsw'],1),round(e['margin']),round(e['env'],1),round(e['J'],3)))
    print(name,lo,ro,'max s',max(o[1] or 9 for o in out),'max J',max(o[-1] for o in out),out,flush=True)
