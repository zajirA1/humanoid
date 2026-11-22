"""Vytvoří pohyb jen s vybranými úseky posunu a otestuje výšky schodu."""
import sys,json,subprocess,math,os; sys.argv=[sys.argv[0]]+sys.argv[1:]
import numpy as np
n=1141; off=np.array(json.load(open('/tmp/plan/off.json')))
USEKY={'f3':(14.3,30.0),'f4':(35.3,35.7),'f5':(39.8,44.3),'f6':(47.2,54.7),'f7':(69.8,71.7),'f8a':(77.3,78.2),'f8b':(82.7,86.8),'f8c':(91.3,92.0),'f9':(97.2,101.0),'f12':(130.3,133.2)}
def okna(vyber):
    keep=np.zeros(n,bool)
    for k in vyber:
        a,b=USEKY[k]; keep[max(0,int(round(a*6))-12):min(n,int(round(b*6))+13)]=True
    return keep
def vyrob(vyber,cil):
    M=json.load(open('/home/claude/humanoid/kontrola/data/model.json')); keep=okna(vyber); o=np.where(keep[:,None],off,0)
    idx=[i for i in range(n) if np.abs(o[i]).max()>1e-6]
    json.dump([{'i':i,'off':o[i].tolist()} for i in idx],open(cil+'.rq','w'))
    subprocess.run(['node','/tmp/plan/posun.js','/home/claude/humanoid/kontrola/data/model.json',cil+'.rq',cil+'.rs'],check=True)
    R={r['i']:r for r in json.load(open(cil+'.rs'))}
    for i in idx: M['q'][i]=[round(v,6) for v in R[i]['q']]; M['rt'][i]=[round(v,9) for v in R[i]['rt']]
    os.makedirs(cil+'/data',exist_ok=True)
    for f in ('prepocet.py','doladeni.py','prizpusob.js','r14engine.js'): subprocess.run(['cp','/home/claude/humanoid/kontrola/'+f,cil+'/'])
    for f in ('geometrie.json.gz','vychozi-R13.json'): subprocess.run(['ln','-sf','/home/claude/humanoid/kontrola/data/'+f,cil+'/data/'])
    json.dump(M,open(cil+'/data/model.json','w'),separators=(',',':'))
if __name__=='__main__':
    vyber=sys.argv[2].split(',') if sys.argv[2] else []; vyrob(vyber,sys.argv[1])
