import sys,json,subprocess,os; HS=[float(x) for x in sys.argv[1].split(',')]; Z=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}; UP=json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
KD='/home/claude/humanoid/kontrola'; sys.path.insert(0,KD); sys.argv=['x']
import numpy as np, prepocet as P, vyvazovani as V
from scipy.ndimage import gaussian_filter1d
G,_=P.nacti_geometrii({}); pid=str(os.getpid())
json.dump({'upravy':UP},open(f'/tmp/plan/vu{pid}.json','w'))
subprocess.run(['node',KD+'/prizpusob.js',KD+'/data/model.json',f'/tmp/plan/vu{pid}.json',f'/tmp/plan/va{pid}.json'],check=True,capture_output=True)
A=json.load(open(f'/tmp/plan/va{pid}.json')); F=A['frames']
ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
cile,nez=V.cile_sil(F,P.M,A['P'],A['E'],A['links'],P.fk)
out=[]
for sh in HS:
    r,_=P.simuluj(F,A['P'],A['E'],A['links'],G,ff,step_h=sh,vyvazovani=dict(trida=Z.pop('trida','Vyvazovani') if 'trida' in Z else 'Vyvazovani',cile=cile,nez=nez,zesileni=Z,ladit=bool(os.environ.get('LADIT'))))
    out.append(f'{sh:.0f}:{"OK" if r["uspech"] else "PÁD@"+str(round(r["pad_s"] or -1,1))}({r["odchylka_konec_mm"]:.0f})')
print(json.dumps(Z),json.dumps(UP)[:30],' '.join(out),flush=True)
