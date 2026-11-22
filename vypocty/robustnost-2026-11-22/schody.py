import sys,json,subprocess; KD=sys.argv[1]; sys.path.insert(0,KD); sys.argv=['x']
import numpy as np, prepocet as P
from scipy.ndimage import gaussian_filter1d
G,_=P.nacti_geometrii({})
def priprav(up):
    json.dump({'upravy':up},open('/tmp/plan/u.json','w'))
    subprocess.run(['node',KD+'/prizpusob.js',KD+'/data/model.json','/tmp/plan/u.json','/tmp/plan/a.json'],check=True,capture_output=True)
    A=json.load(open('/tmp/plan/a.json')); F=A['frames']
    ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
    return A,F,ff
cases={'bez úprav':{},'úprava ramen':{'8':{'posun_mm':[-40,5.5,4.5]},'18':{'posun_mm':[40,5.5,4.5]}}}
for name,up in cases.items():
    A,F,ff=priprav(up); print(name,'max statika',max(f['s50'] for f in F if f['s50']),flush=True)
    for sh in (202.0,205.0,210.0,215.0,218.0):
        r,_=P.simuluj(F,A['P'],A['E'],A['links'],G,ff,step_h=sh)
        print(f'  schod {sh:.0f}: {"OK " if r["uspech"] else "PÁD"} konec {r["odchylka_konec_mm"]:6.1f} mm  pád {r["pad_s"]}  na mezi {r["na_mezi"]*100:.1f} %',flush=True)
