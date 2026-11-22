# test QP regulace: python3 qpt.py výšky [zesílení JSON] [do_s]
import sys,json,subprocess,os; HS=[float(x) for x in sys.argv[1].split(',')]; Z=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}; TEND=float(sys.argv[3]) if len(sys.argv)>3 else None
KD='/home/claude/humanoid/kontrola'; sys.path.insert(0,KD); sys.argv=['x']
import numpy as np, prepocet as P, vyvazovani as V
from scipy.ndimage import gaussian_filter1d
G,_=P.nacti_geometrii({}); pid=str(os.getpid())
def pohyb(h):
    u={'upravy':{}}
    dh=h-210+float(os.environ.get('CHYBA','0'))
    if abs(dh)>1e-6: u['vyska_dh']=dh
    json.dump(u,open(f'/tmp/plan/qu{pid}.json','w'))
    subprocess.run(['node',KD+'/prizpusob.js',os.environ.get('MODEL',KD+'/data/model.json'),f'/tmp/plan/qu{pid}.json',f'/tmp/plan/qa{pid}.json'],check=True,capture_output=True)
    A=json.load(open(f'/tmp/plan/qa{pid}.json')); F=A['frames']
    if TEND: F=F[:int(TEND*6)]
    ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
    return A,F,ff
out=[]
for sh in HS:
    A,F,ff=pohyb(sh); cile,nez=V.cile_sil(F,P.M,A['P'],A['E'],A['links'],P.fk)
    z=dict(Z); tr=z.pop('trida','SilyQP')
    vv=None if tr=='zadna' else dict(trida=tr,cile=cile,nez=nez,zesileni=z,ladit=bool(os.environ.get('LADIT')))
    r,_=P.simuluj(F,A['P'],A['E'],A['links'],G,ff,step_h=sh,vyvazovani=vv)
    out.append(f'{sh:.0f}:{"OK" if r["uspech"] else "PÁD@"+str(round(r["pad_s"] or -1,1))}({r["odchylka_konec_mm"]:.0f},{r["moment_max"]*100:.0f}%)')
print(json.dumps(Z),' '.join(out),flush=True)
