"""Robustnost polohy: rozdělení svislých sil mezi opory (každá opora stejná celková tuhost, síly nezáporné),
rezerva těžiště ve stojné ploše a předzatížení nezbytných opor (bez nich by rezerva klesla pod NUTNA mm)."""
import math, numpy as np
from scipy.optimize import nnls
from scipy.spatial import ConvexHull
NUTNA=10.0
JMENO={7:'L chodidlo',17:'P chodidlo',5:'L holeň',15:'P holeň',10:'L dlaň',20:'P dlaň'}
def _hull_marg(pts,c):
    if len(pts)<3: return -50.0
    try: h=ConvexHull(np.asarray(pts)); return float(-(h.equations[:,:2]@c[:2]+h.equations[:,2]).max())
    except Exception: return -50.0
def poloha(w,flat,links):
    m=np.array([l[0] for l in links]); c=np.zeros(3)
    for i in range(23): R,t=w[i]; c+=m[i]*(R@np.array(links[i][1:])+t)
    c/=m.sum(); W=m.sum()*9.80665; g={}
    for k in range(0,len(flat),4):
        l=flat[k]; R,t=w[l]; g.setdefault(l,[]).append(R@np.array(flat[k+1:k+4])+t)
    keys=sorted(g); pts=[p[:2] for k in keys for p in g[k]]
    marg=_hull_marg(pts,c)
    pp=np.array([p for k in keys for p in g[k]]); gi=[k for k in keys for _ in g[k]]
    sw=np.array([math.sqrt(len(g[k])) for k in gi])
    A=np.vstack([np.ones(len(pp)),pp[:,0]-c[0],pp[:,1]-c[1]])/sw
    x,_=nnls(np.vstack([1e3*A,np.eye(len(pp))]),np.concatenate([1e3*np.array([W,0,0]),np.zeros(len(pp))])); f=x/sw
    F={k:float(sum(f[i] for i in range(len(pp)) if gi[i]==k)) for k in keys}
    nez=[k for k in keys if len(keys)>=2 and _hull_marg([p[:2] for kk in keys if kk!=k for p in g[kk]],c)<NUTNA]
    return dict(marg=marg,F=F,nez=nez,fnez=min([F[k] for k in nez],default=99.0),slaba=None if not nez else min(nez,key=lambda k:F[k]))
