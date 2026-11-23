"""Rozpis mezer po dílech pro aktuální revizi a kontrola posunutého serva vůči vlastnímu rámu.

python3 -I kontrola/rozpis.py <výstup.json> [--krok N]

- „dvojice“: nejbližší dvojice nezávislých dílů (různé, nesousední články) v celém výchozím pohybu revize,
  každá dvojice jednou s minimem a časem (FCL nad sítěmi dílů, stejná geometrie jako automatická kontrola).
- „sousedni“: dvojice sousedních článků v kloubech, kterých se týká posun serva (článek kloubu a jeho rodič).
  Ty běžná kontrola vynechává (v kloubu se díly stýkají záměrně), proto se tady porovnávají s předchozí revizí:
  když se posunem nově dotknou nebo se přiblíží pod 2 mm, je to varování (střet serva/vidlice s vlastním rámem).
Meze verdiktu se tím nemění – jen údaje a varování.
"""
import sys,os,json
import numpy as np
TU=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,TU)
import prepocet as PR

NAZVY=['krk','hlava','levá kyčel (otočný díl)','levá kyčel','levé stehno','levá holeň','levý kotník','levé chodidlo','levé rameno','levá paže','levé předloktí','levá ruka',
       'pravá kyčel (otočný díl)','pravá kyčel','pravé stehno','pravá holeň','pravý kotník','pravé chodidlo','pravé rameno','pravá paže','pravé předloktí','pravá ruka','trup']
DRUH={'body':'','cover':' – kryt','sleeve':' – návlek'}
def nazev(k): return NAZVY[k[0]]+DRUH.get(k[1],'')
VAR_MM=2.0     # sousední články: varování, když se nově přiblíží pod tuto mez
CUT=15.0

def pe(M,ed):
    """Čepy P a vektory E jako r14engine.setEdits."""
    P=[list(map(float,p)) for p in M['P']]; E=[[0.0,0.0,0.0] for _ in P]
    for k,e in (ed or {}).items():
        j=int(k); d=[float(x) for x in e.get('d',[0,0,0])]
        for a in range(3):
            P[j][a]+=d[a]; E[j][a]=float(e['E'][a]) if 'E' in e else (d[a] if e.get('carry') else 0.0)
    return np.array(P),np.array(E)

def minima(G,pairs,ws,cut=CUT):
    """Pro každou dvojici minimum vzdálenosti přes polohy (jen pod cut) a index polohy."""
    import fcl
    req=fcl.DistanceRequest(); best={}
    for i,w in ws:
        for (l,k),g in G.items():
            R,t=w[l]; g['obj'].setTransform(fcl.Transform(np.ascontiguousarray(R),np.ascontiguousarray(t))); cw=g['corners']@R.T+t; g['lo']=cw.min(0); g['hi']=cw.max(0)
        for a,b in pairs:
            A,B=G[a],G[b]; lim=min(cut,best.get((a,b),(cut,0))[0])
            if np.maximum(0,np.maximum(A['lo']-B['hi'],B['lo']-A['hi'])).max()>=lim: continue
            d=max(0.0,float(fcl.distance(A['obj'],B['obj'],req,fcl.DistanceResult())))
            if d<lim: best[(a,b)]=(d,i)
    return best

def nacti_dily(edits,odkazy=None):
    """Jednotlivé díly (ne skupiny) se stejným posunem jako PR.nacti_geometrii."""
    import fcl,gzip
    import ram
    items=json.load(gzip.open(os.path.join(PR.DATA,'geometrie.json.gz'),'rt')); out=[]
    items=[dict(it,v=np.array(it['v'],float).reshape(-1,3)) for it in items]; ram.prizpusob(items,edits,PR.PAR)
    for it in items:
        v=it['v']; f=np.array(it['f'],int).reshape(-1,3); j=it['owner']; e=edits.get(str(j)) if isinstance(j,int) else None; zm=bool(it.get('_ram'))
        if e and it['kind']=='cad' and not it['frame'] and j<22:
            d=np.array(e['d'],float)
            if e.get('rot'):
                Rr,tr=PR.rot(PR.AX[j],e['rot'],PR.M['P'][j])
                if it['link']==PR.PAR[j]: v=v@Rr.T+tr
            if 'E' in e: v=v+(d-np.array(e['E'],float) if it['link']==j else d)
            elif not (e.get('carry') and it['link']==j): v=v+d
            zm=True
        m=fcl.BVHModel(); m.beginModel(len(v),len(f)); m.addSubModel(np.ascontiguousarray(v,float),np.ascontiguousarray(f,np.int32)); m.endModel()
        lo,hi=v.min(0),v.max(0); c=np.array([[x,y,zz] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for zz in (lo[2],hi[2])])
        out.append(dict(key=it['key'],link=it['link'],owner=j,kind=it['kind'],frame=bool(it['frame']),zm=zm,obj=fcl.CollisionObject(m,fcl.Transform()),corners=c))
    return out
def jmeno_dilu(d):
    k=d['key']; o=d['owner']
    if d['frame']: t='rám'
    elif d['kind']=='cover': t='kryt '+k.replace('r12_r8_','').replace('r8_','')
    elif k.startswith(('ST','XL','r8_ST','r8_XL')): t='servo'+(' '+PR.JN[o] if isinstance(o,int) and o<22 else '')
    elif k.startswith('r8_horn'): t='páka serva'+(' '+PR.JN[o] if isinstance(o,int) and o<22 else '')
    else: t=k
    return NAZVY[d['link']]+': '+t+f' ({k})'
def dily_minima(D,pairs,ws,cut):
    import fcl
    req=fcl.DistanceRequest(); best={}; need=sorted({x for p in pairs for x in p})
    for i,w in ws:
        for n in need:
            d=D[n]; R,t=w[d['link']]; d['obj'].setTransform(fcl.Transform(np.ascontiguousarray(R),np.ascontiguousarray(t))); cw=d['corners']@R.T+t; d['lo']=cw.min(0); d['hi']=cw.max(0)
        for a,b in pairs:
            A,B=D[a],D[b]; lim=min(cut,best.get((a,b),(cut,0))[0])
            if np.maximum(0,np.maximum(A['lo']-B['hi'],B['lo']-A['hi'])).max()>=lim: continue
            dd=max(0.0,float(fcl.distance(A['obj'],B['obj'],req,fcl.DistanceResult())))
            if dd<lim: best[(a,b)]=(dd,i)
    return best

def rozpis(M,ed,ed_base,krok=1,log=print,polohy=None):
    """polohy = [(q, rt), …] (výchozí: pohyb z modelu); ed = posuny nové geometrie, ed_base = předchozí revize."""
    Q=polohy or list(zip(M['q'],M['rt'])); n=len(Q); idx=list(range(0,n,krok)); hz=M['hz']; PAR=M['PAR']
    G,pairs=PR.nacti_geometrii(ed); P,E=pe(M,ed)
    ws=[(i,PR.fk(Q[i][0],Q[i][1],P,E)) for i in idx]
    log('rozpis: dvojic',len(pairs),'poloh',len(idx))
    m=minima(G,pairs,ws)
    dv=sorted(((d,i,a,b) for (a,b),(d,i) in m.items()),key=lambda x:x[0])[:15]
    dvojice=[dict(a=nazev(a),b=nazev(b),mm=round(d,2),cas_s=round(i/hz,1)) for d,i,a,b in dv]
    # posunutá serva × vlastní rám: po jednotlivých dílech, nová geometrie × předchozí revize
    zmena=sorted({int(k) for k in set(ed)|set(ed_base or {}) if json.dumps(ed.get(k),sort_keys=True)!=json.dumps((ed_base or {}).get(k),sort_keys=True)})
    sousedni=[];varovani=[]
    if zmena:
        D1=nacti_dily(ed); D0=nacti_dily(ed_base or {}); P0,E0=pe(M,ed_base)
        par=lambda l:PAR[l] if l<22 else None
        stat=[];poh=[]
        for j in zmena:
            L=PAR[j]
            for LL in (L,j):
                mov=[i for i,d in enumerate(D1) if d['link']==LL and (d['zm'] or D0[i]['zm'])]
                stat+=[(a,b) for a in mov for b,d in enumerate(D1) if d['link']==LL and b!=a and not (b in mov and b<a)]
            poh+=[(a,b) for a,d in enumerate(D1) if d['link']==j for b,e in enumerate(D1) if e['link']==L]
            poh+=[(a,b) for a,d in enumerate(D1) if d['link']<22 and par(d['link'])==j for b,e in enumerate(D1) if e['link']==j]
        stat=list(dict.fromkeys(stat)); poh=list(dict.fromkeys(poh))
        I=np.eye(3); z=np.zeros(3); w_id=[(I,z)]*23
        s1=dily_minima(D1,stat,[(0,w_id)],cut=10.0); s0=dily_minima(D0,stat,[(0,w_id)],cut=10.0)
        ws0=[(i,PR.fk(Q[i][0],Q[i][1],P0,E0)) for i in idx]
        p1=dily_minima(D1,poh,ws,cut=10.0); p0=dily_minima(D0,poh,ws0,cut=10.0)
        for pairs_,m1,m0,druh in ((stat,s1,s0,'pevně na rámu'),(poh,p1,p0,'v pohybu kloubu')):
            for a,b in pairs_:
                d1,i1=m1.get((a,b),(10.0,0)); d0,i0=m0.get((a,b),(10.0,0))
                if d1>=10.0 and d0>=10.0: continue
                r=dict(a=jmeno_dilu(D1[a]),b=jmeno_dilu(D1[b]),druh=druh,mm=round(d1,2),mm_pred=round(d0,2),cas_s=round(i1/hz,1) if druh!='pevně na rámu' else None)
                r['stav']='beze změny' if abs(d1-d0)<0.05 else ('dál' if d1>d0 else 'blíž')
                if d1<VAR_MM and d1<d0-0.05:
                    r['stav']='nový dotyk' if d1<=0.0 else 'blíž pod 2 mm'
                    varovani.append(f"{r['a']} × {r['b']} ({druh}): {('dotyk' if d1<=0 else str(round(d1,1))+' mm')}"+(f" v {r['cas_s']} s" if r['cas_s'] is not None else '')+f" (předtím {round(d0,1)} mm) – zkontrolovat úchyt serva vůči rámu")
                sousedni.append(r)
        sousedni.sort(key=lambda r:(r['stav'] not in ('nový dotyk','blíž pod 2 mm'),r['stav']=='beze změny',r['mm']))
        log('posunutá serva: dvojic dílů',len(stat),'+',len(poh))
    log('rozpis hotový: nejmenší',dvojice[0]['mm'] if dvojice else None,'sousední varování',len(varovani))
    return dict(revize=M.get('revize'),krok=krok,poloh=len(idx),dvojice=dvojice,sousedni=sousedni,varovani=varovani,
                poznamka='Jmenovitá geometrie sítí dílů v polohách výchozího pohybu (6 Hz); mezi polohami může být mezera menší. Rám je přizpůsobený posunu serva plynulým přetvořením (kontrola/ram.py) – skutečný díl bude jiný, výsledek je odhad.')

if __name__=='__main__':
    out=sys.argv[1]; krok=int(sys.argv[sys.argv.index('--krok')+1]) if '--krok' in sys.argv else 1
    M=PR.M; H=(M.get('historie') or [{}])[-1]
    r=rozpis(M,M.get('zaklad') or {},H.get('zaklad_z',{}),krok)
    json.dump(r,open(out,'w'),ensure_ascii=False,indent=1)
