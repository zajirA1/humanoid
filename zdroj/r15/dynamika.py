"""Jmenovitá dynamika hotového pohybu R15 pro stránku: špička momentu serva v každé poloze.
python3 -I dynamika.py <pohyb.json> <výstup.json>"""
import sys,os,json,subprocess
KD=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','kontrola'); sys.path.insert(0,KD)
import numpy as np, prepocet as P
from scipy.ndimage import gaussian_filter1d
src,out=sys.argv[1],sys.argv[2]; tmp=out+'.tmp'
Q=json.load(open(src)); fix=dict(q=Q['q'],rt=Q['rt'],drift=[0]*len(Q['q']),shift=[0]*len(Q['q']))
json.dump(fix,open(tmp+'f','w')); json.dump({},open(tmp+'u','w'))
subprocess.run(['node',os.path.join(KD,'prizpusob.js'),os.path.join(KD,'data','model.json'),tmp+'u',tmp,tmp+'f'],check=True,capture_output=True)
A=json.load(open(tmp)); F=A['frames']
for x in (tmp,tmp+'f',tmp+'u'): os.remove(x)
G,_=P.nacti_geometrii({})
ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
r,_=P.simuluj(F,A['P'],A['E'],A['links'],G,ff,momenty=True); sn=r.pop('_snimky')
n=len(F); t=np.array(sn['t']); pom=np.array(sn['pomer']); mom=np.array(sn['moment'])
idx=[int(np.argmin(np.abs(t-i/P.HZ))) for i in range(n)]
json.dump(dict(souhrn=r,pomer=[round(float(pom[k]),4) for k in idx],moment=[[round(float(x),4) for x in mom[k]] for k in idx]),open(out,'w'))
print('dynamika',r['uspech'],round(r['odchylka_konec_mm'],1),'max',round(float(pom.max()),3))
