"""Doladění volných končetin: v úsecích, kde je mezera pod cílem a těsná dvojice patří volné (neopřené) noze nebo ruce,
se klouby té končetiny pootočí o jednu společnou změnu s plynulým náběhem a doběhem (bez skoků). Opory, trup ani opřené
končetiny se nemění; během úseku musí být končetina celou dobu volná. Cíl: nejmenší mezera v celém úseku ≥ cil."""
import numpy as np, fcl
from scipy.optimize import minimize
KONCETINY={'L_noha':dict(j=[2,3,4,5,6,7],links={2,3,4,5,6,7},opora={'leftFoot','leftKnee'}),
           'P_noha':dict(j=[12,13,14,15,16,17],links={12,13,14,15,16,17},opora={'rightFoot','rightKnee'}),
           'L_ruka':dict(j=[8,9,10],links={8,9,10,11},opora={'leftPalm'}),
           'P_ruka':dict(j=[18,19,20],links={18,19,20,21},opora={'rightPalm'})}
MAXD=8.0; NABEH=9   # stupně; náběh/doběh v polohách (1,5 s)
_req=fcl.DistanceRequest()
def volna(k,support): return not (KONCETINY[k]['opora'] & set(support))
def _env(V,STEP):
    x,y,z=V[:,0],V[:,1],V[:,2]; dx=np.maximum(np.abs(x)-330,0); dy=np.maximum(np.maximum(y,-280-y),0); dz=np.maximum(z-STEP,0)
    out=np.sqrt(dx*dx+dy*dy+dz*dz); inside=(dx==0)&(dy==0)&(dz==0)
    return float(min(z.min(),np.where(inside,-np.minimum(np.minimum(-y,y+280),STEP-z),out).min()))
def min_koncetiny(G,mypairs,links,w,STEP,ex,cap,env_posun=0.0):
    """nejmenší rezerva: mezera dílů, nebo odstup od schodu posunutý tak, aby se měřil vůči vlastní mezi"""
    box={}
    for key,g in G.items():
        R,t=w[key[0]]; cw=g['corners']@R.T+t; box[key]=(cw.min(0),cw.max(0),R,t)
    best=cap
    for a,b in mypairs:
        (la,ha,Ra,ta),(lb,hb,Rb,tb)=box[a],box[b]
        if np.maximum(0,np.maximum(la-hb,lb-ha)).max()>=best: continue
        G[a]['obj'].setTransform(fcl.Transform(np.ascontiguousarray(Ra),np.ascontiguousarray(ta)))
        G[b]['obj'].setTransform(fcl.Transform(np.ascontiguousarray(Rb),np.ascontiguousarray(tb)))
        best=min(best,fcl.distance(G[a]['obj'],G[b]['obj'],_req,fcl.DistanceResult()))
    for key,g in G.items():
        if key[0] in links and key not in ex:
            lo,hi,R,t=box[key]
            if lo[2]>best and (lo[1]>best or lo[2]>STEP+best): continue
            best=min(best,_env(g['V']@R.T+t,STEP)+env_posun)
    return best
def dolad(F,M,P_,E_,G,pairs,fk,selfd,cil,STEP,log=print,cil_env=3.5):
    n=len(F); ex_of=lambda i:{k for k,b in (((7,'body'),1),((17,'body'),2),((5,'sleeve'),4),((15,'sleeve'),8)) if M['ex'][i]&b}
    zasah=[]
    for k,K in KONCETINY.items():
        links=K['links']; J=K['j']
        spatne=sorted(i for d,i,bp in selfd if d<cil and bp and volna(k,M['support'][i]) and (bp[0][0] in links or bp[1][0] in links))
        if not spatne: continue
        mypairs=[(a,b) for a,b in pairs if a[0] in links or b[0] in links]
        # úseky: sousední špatné polohy (mezera ≤ 6) spojit
        useky=[[spatne[0],spatne[0]]]
        for i in spatne[1:]:
            if i-useky[-1][1]<=6: useky[-1][1]=i
            else: useky.append([i,i])
        for a,b in useky:
            # rozšířit o náběh, ale jen dokud je končetina volná
            lo=a
            while lo>0 and a-lo<NABEH and volna(k,M['support'][lo-1]): lo-=1
            hi=b
            while hi<n-1 and hi-b<NABEH and volna(k,M['support'][hi+1]): hi+=1
            idx=np.arange(lo,hi+1)
            def vaha(i):
                if i<a: return 0.5-0.5*np.cos(np.pi*(i-lo+1)/(a-lo+1)) if a>lo else 1.0
                if i>b: return 0.5-0.5*np.cos(np.pi*(hi-i+1)/(hi-b+1)) if hi>b else 1.0
                return 1.0
            W=np.array([vaha(i) for i in idx]); W[0]=0 if lo<a else W[0]; W[-1]=0 if hi>b else W[-1]
            vzorek=idx
            q0={i:np.array(F[i]['q'],float) for i in idx}; exs={i:ex_of(i) for i in idx}; wt=dict(zip(idx,W))
            def nejmensi(x):
                m=1e9
                for i in vzorek:
                    q=q0[i].copy(); q[J]+=wt[i]*x; m=min(m,min_koncetiny(G,mypairs,links,fk(q,F[i]['rt'],P_,E_),STEP,exs[i],cil+0.8,cil-cil_env))
                return m
            m0=nejmensi(np.zeros(len(J)))
            r=minimize(lambda x:-nejmensi(x)+0.01*float(x@x),np.zeros(len(J)),method='Powell',bounds=[(-MAXD,MAXD)]*len(J),options=dict(xtol=0.1,ftol=0.02,maxfev=160))
            m1=nejmensi(r.x)
            if m1<=m0+0.05: log(f'{k} {a/6:.1f}–{b/6:.1f} s: doladění nepomohlo ({m0:.2f} mm)'); continue
            for i in idx:
                q=q0[i].copy(); q[J]+=wt[i]*r.x; F[i]['q']=[float(v) for v in q]
            zasah.append(dict(koncetina=k,od=int(lo),do=int(hi),pred=float(m0),po=float(m1),zmena=[round(float(v),2) for v in r.x]))
            log(f'{k} {lo/6:.1f}–{hi/6:.1f} s: rezerva vůči cíli {m0-cil:+.2f} → {m1-cil:+.2f} mm, změna úhlů {np.round(r.x,1).tolist()}°')
    return zasah
