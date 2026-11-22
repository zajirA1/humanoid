"""Rozdělení svislých sil mezi skupiny opor (nejmenší čtverce = stejná tuhost) a rezerva těžiště."""
import sys,json,math; sys.path.insert(0,'/home/claude/humanoid/kontrola'); sys.argv=['x']
import numpy as np, prepocet as P
from scipy.spatial import ConvexHull
M=P.M; LINK2N={7:'L chodidlo',17:'P chodidlo',5:'L holeň',15:'P holeň',10:'L dlaň',20:'P dlaň'}
def mass_com(w,links):
    m=np.array([l[0] for l in links]); c=np.zeros(3)
    for i in range(23): R,t=w[i]; c+=m[i]*(R@np.array(links[i][1:])+t)
    return c/m.sum(), m.sum()
def rozbor(q,rt,flat,P_=None,E_=None,links=None):
    P_=P_ or M['P']; E_=E_ or [[0,0,0]]*22; links=links or M['LINKS']
    w=P.fk(q,rt,P_,E_); c,mt=mass_com(w,links)
    groups={}
    for k in range(0,len(flat),4):
        l=flat[k]; R,t=w[l]; groups.setdefault(l,[]).append(R@np.array(flat[k+1:k+4])+t)
    keys=sorted(groups); pts=np.array([p[:2] for g in groups.values() for p in g])
    try: h=ConvexHull(pts); marg=float(-(h.equations[:,:2]@c[:2]+h.equations[:,2]).max())
    except Exception: marg=-50.0
    # rozdělení přes jednotlivé body opor, každá opora (skupina) má stejnou celkovou tuhost
    from scipy.optimize import nnls
    W=mt*9.80665; pp=[];gi=[]
    for k in keys:
        for p in groups[k]: pp.append(p); gi.append(k)
    pp=np.array(pp); ng={k:len(groups[k]) for k in keys}; sw=np.array([math.sqrt(ng[k]) for k in gi])
    A=np.vstack([np.ones(len(pp)),pp[:,0]-c[0],pp[:,1]-c[1]])/sw; b=np.array([W,0,0])
    BIG=1e3; g,_=nnls(np.vstack([BIG*A,np.eye(len(pp))]),np.concatenate([BIG*b,np.zeros(len(pp))])); f=g/sw
    x=[float(sum(f[i] for i in range(len(pp)) if gi[i]==k)) for k in keys]
    return dict(c=c,marg=marg,F={k:float(v) for k,v in zip(keys,x)},keys=keys)
if __name__=='__main__':
    out=[]
    for i in range(len(M['q'])):
        r=rozbor(M['q'][i],M['rt'][i],M['contacts'][i]); out.append(r)
    json.dump([dict(marg=r['marg'],F=r['F']) for r in out],open('/tmp/plan/r13_metriky.json','w'))
    # slabé úseky
    slabe=[]
    for i,r in enumerate(out):
        fmin=min(r['F'].values()) if len(r['F'])>=2 else 99
        if r['marg']<20 or (len(r['F'])>=3 and fmin<5): slabe.append(i)
    print('slabých poloh',len(slabe))
    us=[]
    for i in slabe:
        if us and i-us[-1][1]<=3: us[-1][1]=i
        else: us.append([i,i])
    for a,b in us:
        rr=out[a:b+1]; mm=min(r['marg'] for r in rr); fm=min(min(r['F'].values()) for r in rr if len(r['F'])>=3) if any(len(r['F'])>=3 for r in rr) else None
        print(f'{a/6:6.1f}–{b/6:6.1f} s fáze {M["phase"][a]+1}-{M["phase"][b]+1} opory {"/".join(LINK2N[k] for k in out[a]["keys"])}: rezerva min {mm:5.1f} mm, nejslabší opora {fm if fm is None else round(fm,1)} N')

def marg_bez(groups_xy,c,vynech):
    pts=np.array([p for k,g in groups_xy.items() if k!=vynech for p in g])
    if len(pts)<3: return -50.0
    try: h=ConvexHull(pts); return float(-(h.equations[:,:2]@c[:2]+h.equations[:,2]).max())
    except Exception: return -50.0
def robust(q,rt,flat,P_=None,E_=None,links=None,FMIN=5.0,NUTNA=10.0):
    """nezbytná opora = bez ní by rezerva těžiště klesla pod NUTNA mm; vrací nejmenší sílu nezbytné opory a rezervu"""
    P_=P_ or M['P']; E_=E_ or [[0,0,0]]*22; links=links or M['LINKS']
    r=rozbor(q,rt,flat,P_,E_,links); w=P.fk(q,rt,P_,E_)
    g={}
    for k in range(0,len(flat),4):
        l=flat[k]; R,t=w[l]; g.setdefault(l,[]).append((R@np.array(flat[k+1:k+4])+t)[:2])
    nez=[k for k in g if len(g)>=2 and marg_bez(g,r['c'],k)<NUTNA]
    fnez=min([r['F'][k] for k in nez],default=99.0)
    return dict(marg=r['marg'],fnez=fnez,nezbytne=nez,F=r['F'])
