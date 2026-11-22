import sys; args=sys.argv[1:]
exec(open('/tmp/plan/f6hledej.py').read())
import itertools
for spec in args:
    dx,dy=[float(v) for v in spec.split(',')]
    q,rt,smax=pohyb([dx,dy,0.0])
    json.dump(dict(q=q,rt=rt,drift=[0]*n,shift=[0]*n),open('/tmp/plan/fix'+str(os.getpid())+'.json','w'))
    F,ff=ff_of(q,rt); out=[]
    for sh in (210.0,215.0,218.0):
        r,_=P.simuluj(F,P.M['P'] if False else json.load(open('/tmp/plan/a_tmp'+str(os.getpid())+'.json'))['P'],[[0,0,0]]*22,M0['LINKS'],G,ff,step_h=sh)
        out.append(f'{sh:.0f}:{"OK" if r["uspech"] else "PÁD@"+str(round(r["pad_s"] or -1,1))}')
    print(f'f6 posun x {dx:+.0f} y {dy:+.0f}: statika {smax:.3f} ',' '.join(out),flush=True)
