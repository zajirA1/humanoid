import sys; sys.path.insert(0,'/home/claude/sim')
from run_retarget import *
KA=pickle.load(open('key_A.pkl','rb'))
cands={'A':((0,0),(0,0)),'B':((38,0),(0,0)),'F':((38,0),(36,-46)),'G':((38,0),(0,-30)),'H':((38,0),(-20,10)),'I':((0,30),(0,0)),'J':((38,40),(0,0))}
frames=[int(a) for a in sys.argv[1].split(',')]; sup={'leftKnee','leftPalm','rightPalm'}
for name,(lo,ro) in cands.items():
    out=[]
    for i in frames:
        fr=Frame(i,sup,palm_off={'L':np.array([lo[0],lo[1],0.]),'R':np.array([ro[0],ro[1],0.])})
        st0=REFS[i].st; best=None
        for v0 in (np.array([4,0,0.5,0,0,0.]),np.array([3,-1,2,1,-1,-2.])):
            v,J=optimise(fr,v0,st0,maxiter=200,step=0.8)
            if best is None or J<best[1]: best=(v,J)
        e=evaluate(fr,best[0],st0,full=True); out.append((i,round(e['r']['s'],3) if e['r'] else None,e['r']['jmax'] if e['r'] else None,round(e['res'],1),round(e['rsw'],1),round(e['margin']),round(e['env'],1),round(e['J'],3)))
    print(name,lo,ro,'max s',max(o[1] or 9 for o in out),out,flush=True)
