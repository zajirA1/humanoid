"""Doladění volných končetin: v úsecích, kde je mezera pod cílem a těsná dvojice patří volné (neopřené) noze nebo ruce,
se klouby té končetiny pootočí o jednu společnou změnu s plynulým náběhem a doběhem (bez skoků). Opory, trup ani opřené
končetiny se nemění; během úseku musí být končetina celou dobu volná. Cíl: nejmenší mezera v celém úseku ≥ cil."""
import os, numpy as np, fcl
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
def dolad(F,M,P_,E_,G,pairs,fk,selfd,cil,STEP,log=print,cil_env=3.5,envd=None):
    n=len(F); ex_of=lambda i:{k for k,b in (((7,'body'),1),((17,'body'),2),((5,'sleeve'),4),((15,'sleeve'),8)) if M['ex'][i]&b}
    zasah=[]
    for k,K in KONCETINY.items():
        links=K['links']; J=K['j']
        spatne=set(i for d,i,bp in selfd if d<cil and bp and volna(k,M['support'][i]) and (bp[0][0] in links or bp[1][0] in links))
        if envd: spatne|=set(i for e,i,ek in envd if e<cil_env and ek and ek[0] in links and volna(k,M['support'][i]))
        spatne=sorted(spatne)
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


def dolad_po_polohach(F,M,P_,E_,G,pairs,fk,selfd,envd,cil,STEP,log=print,cil_env=3.5,MAXP=10.0):
    """Záloha, když jedna společná změna úseku nestačí (dlouhý švih přes hranu schodu): těsné polohy volné končetiny
    se dolaďují jednotlivě (≤ MAXP °) v několika kolech, změny se vyhlazují v čase (bez skoků) a ponechají se jen tehdy,
    když se celé okno zlepší. Odstup od schodu se zvedá k cil_env + 1,5 mm, mezera dílů nesmí klesnout pod min(dosavadní, cil)."""
    from scipy.ndimage import gaussian_filter1d
    n=len(F); ex_of=lambda i:{k for k,b in (((7,'body'),1),((17,'body'),2),((5,'sleeve'),4),((15,'sleeve'),8)) if M['ex'][i]&b}
    zasah=[]; cilm=cil+1.0
    for k,K in KONCETINY.items():
        links=K['links']; J=K['j']; nJ=len(J)
        spatne=set(i for d,i,bp in selfd if d<cil and bp and volna(k,M['support'][i]) and (bp[0][0] in links or bp[1][0] in links))
        spatne|=set(i for e,i,ek in envd if e<cil_env and ek and ek[0] in links and volna(k,M['support'][i]))
        if not spatne: continue
        mypairs=[(a,b) for a,b in pairs if a[0] in links or b[0] in links]
        lo=max(0,min(spatne)-12); hi=min(n-1,max(spatne)+12)
        idx=[i for i in range(lo,hi+1) if volna(k,M['support'][i])]
        q0={i:list(F[i]['q']) for i in range(lo,hi+1)}
        m_=lambda i,X:min_koncetiny(G,mypairs,links,fk(_q(q0[i],J,X[i-lo]),F[i]['rt'],P_,E_),STEP,ex_of(i),cilm+1,cil-cil_env)
        sam=lambda i,x:min_koncetiny(G,mypairs,links,fk(_q(q0[i],J,x),F[i]['rt'],P_,E_),STEP,ex_of(i),cil+3,1e3)
        okoli=lambda i,x:min_koncetiny(G,[],links,fk(_q(q0[i],J,x),F[i]['rt'],P_,E_),STEP,ex_of(i),cil_env+3,0.0)
        mask=np.array([1.0 if (lo+t) in idx else 0.0 for t in range(hi-lo+1)]); mk=(gaussian_filter1d(mask,1.0,mode='constant')*mask)[:,None]
        X=np.zeros((hi-lo+1,nJ)); okno=lambda X:min(m_(i,X) for i in idx)
        pred=okno(X); best=(pred,X.copy())
        Z=np.zeros(nJ)
        for kolo in range(3):
            # všechny polohy okna; spojitost se sousedy (předchozí z tohoto kola, následující z minulého) místo vyhlazení
            Y=X.copy()
            for i in idx:
                t=i-lo; pv=Y[t-1] if t>0 and (i-1) in idx else Z; nx=X[t+1] if t+1<len(X) and (i+1) in idx else Z
                s0=min(sam(i,Z),cil); te=cil_env+1.5; potreba=okoli(i,Z)<te or sam(i,Z)<cil
                f=lambda x:-min(okoli(i,x),te)+10*max(0.0,s0-sam(i,x))+(0.005 if potreba else 0.03)*float(x@x)+0.06*(float((x-pv)@(x-pv))+float((x-nx)@(x-nx)))
                Y[t]=minimize(f,X[t] if kolo else pv,method='Powell',bounds=[(-MAXP,MAXP)]*nJ,options=dict(xtol=0.05,maxfev=300)).x
            for t in range(len(Y)):
                if not mask[t]: Y[t]=0
            X=np.clip(Y,-MAXP,MAXP)
            m=okno(X)
            if m>best[0]+0.02: best=(m,X.copy())
            if best[0]>=cilm-0.5: break
        if best[0]<=pred+0.05:
            log(f'{k} {lo/6:.1f}–{hi/6:.1f} s po polohách: nepomohlo ({pred-cil:+.2f} mm)'); continue
        X=best[1]
        for i in range(lo,hi+1): F[i]['q']=list(map(float,_q(q0[i],J,X[i-lo])))
        zasah.append(dict(koncetina=k,od=int(lo),do=int(hi),pred=float(pred),po=float(best[0]),zmena=[round(float(v),2) for v in np.abs(X).max(axis=0)],po_polohach=True))
        log(f'{k} {lo/6:.1f}–{hi/6:.1f} s po polohách: rezerva okna vůči cíli {pred-cil:+.2f} → {best[0]-cil:+.2f} mm, největší změna {float(np.abs(X).max()):.1f}°')
    return zasah
def _q(q,J,x):
    q=np.array(q,float); q[J]+=x; return q
