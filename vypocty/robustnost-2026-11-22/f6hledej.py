import sys,json,subprocess,math,os; sys.argv=['x']
import numpy as np
sys.path.insert(0,'/home/claude/humanoid/kontrola'); import prepocet as P
from scipy.ndimage import gaussian_filter1d
exec(open('/tmp/plan/podmnozina.py').read().split("if __name__=='__main__':")[0])
G,_=P.nacti_geometrii({}); M0=json.load(open('/home/claude/humanoid/kontrola/data/model.json'))
base_off=np.where(okna(['f3'])[:,None],off,0.0)
a6,b6=int(round(47.2*6)),int(round(54.7*6)); lo,hi=a6-12,b6+12
def okno(i):
    if a6<=i<=b6: return 1.0
    if lo<=i<a6: return 0.5-0.5*math.cos(math.pi*(i-lo)/(a6-lo))
    if b6<i<=hi: return 0.5-0.5*math.cos(math.pi*(hi-i)/(hi-b6))
    return 0.0
def pohyb(d):
    o=base_off.copy()
    for i in range(lo,hi+1): o[i]=np.array([d[0],d[1],d[2]])*okno(i)
    idx=[i for i in range(n) if np.abs(o[i]).max()>1e-6]; tag='_'.join(str(int(v)) for v in d)
    json.dump([{'i':i,'off':o[i].tolist()} for i in idx],open(f'/tmp/plan/f6_{tag}.rq','w'))
    subprocess.run(['node','/tmp/plan/posun.js','/home/claude/humanoid/kontrola/data/model.json',f'/tmp/plan/f6_{tag}.rq',f'/tmp/plan/f6_{tag}.rs'],check=True)
    R={r['i']:r for r in json.load(open(f'/tmp/plan/f6_{tag}.rs'))}
    q=[R[i]['q'] if i in R else M0['q'][i] for i in range(n)]; rt=[R[i]['rt'] if i in R else M0['rt'][i] for i in range(n)]
    return q,rt,max(R[i]['s50'] or 9 for i in idx)
def ff_of(q,rt):
    # statika μ=0,02 pro předkorekci ze stejného jádra
    M=dict(M0); M['q']=q; M['rt']=rt; json.dump(M,open('/tmp/plan/m_tmp'+str(os.getpid())+'.json','w'),separators=(',',':')); json.dump({'upravy':{}},open('/tmp/plan/u0'+str(os.getpid())+'.json','w'))
    subprocess.run(['node','/home/claude/humanoid/kontrola/prizpusob.js','/tmp/plan/m_tmp'+str(os.getpid())+'.json','/tmp/plan/u0'+str(os.getpid())+'.json','/tmp/plan/a_tmp'+str(os.getpid())+'.json','/tmp/plan/fix'+str(os.getpid())+'.json'],check=True,capture_output=True)
    F=json.load(open('/tmp/plan/a_tmp'+str(os.getpid())+'.json'))['frames']; ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0
    return F,gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
d=[float(x) for x in sys.argv[1:4]] if len(sys.argv)>3 else None
