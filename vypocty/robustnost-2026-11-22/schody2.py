import sys,json,subprocess; KD=sys.argv[1]; HS=[float(x) for x in sys.argv[2].split(',')]; sys.path.insert(0,KD); sys.argv=['x']
import numpy as np, prepocet as P
from scipy.ndimage import gaussian_filter1d
G,_=P.nacti_geometrii({})
json.dump({'upravy':{}},open(KD+'/u.json','w'))
subprocess.run(['node',KD+'/prizpusob.js',KD+'/data/model.json',KD+'/u.json',KD+'/a.json'],check=True,capture_output=True)
A=json.load(open(KD+'/a.json')); F=A['frames']
ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
out=[]
for sh in HS:
    r,_=P.simuluj(F,A['P'],A['E'],A['links'],G,ff,step_h=sh); out.append(f'{sh:.0f}:{"OK" if r["uspech"] else "PÁD@"+str(round(r["pad_s"] or -1,1))}')
print(KD.split('/')[-1],'statika',round(max(f['s50'] for f in F if f['s50']),3),' '.join(out),flush=True)
