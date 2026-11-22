"""Automatická kontrola úpravy kloubů: přizpůsobení pohybu, statika, přesné mezery, dynamická simulace, verdikt.
python3 -I kontrola/prepocet.py <upravy.json> <výstupní složka> [--rychle]"""
import sys,os,json,gzip,math,subprocess,time,hashlib
import numpy as np
TU=os.path.dirname(os.path.abspath(__file__)); DATA=os.path.join(TU,'data'); sys.path.insert(0,TU)
MEZE=dict(max_vyuziti=0.85,mezera_dilu_mm=9.0,odstup_schod_mm=3.0,posun_opory_mm=0.5)
CIL_DOLADENI=9.5
ROBUST=dict(rezerva_mm=15.0,predzatizeni_N=5.0)   # slabé místo: rezerva těžiště nebo zatížení nezbytné opory pod touto hodnotou   # doladění volných končetin míří s rezervou 0,5 mm nad mez
M=json.load(open(os.path.join(DATA,'model.json')))
PAR=M['PAR']; AX=np.array(M['AX'],float); JN=M['JN']; LIM=np.array(M['LIM']); HZ=M['hz']; STEP=M['step_h']
def rot(axis,ang,pt):
    x,y,z=axis; a=math.radians(ang); s,c=math.sin(a),math.cos(a); v=1-c
    R=np.array([[c+x*x*v,x*y*v-z*s,x*z*v+y*s],[y*x*v+z*s,c+y*y*v,y*z*v-x*s],[z*x*v-y*s,z*y*v+x*s,c+z*z*v]])
    return R,np.asarray(pt)-R@np.asarray(pt)
def rt2T(rt): rt=np.asarray(rt,float); return rt[:9].reshape(3,3).T,rt[9:]
def fk(q,rt,P,E):
    w=[None]*23; w[22]=rt2T(rt)
    for i in range(22):
        Rp,tp=w[PAR[i]]; R,t=rot(AX[i],q[i],P[i]); t=t+R@E[i]; w[i]=(Rp@R,Rp@t+tp)
    return w
# ---------- geometrie a přesné mezery (FCL) ----------
def nacti_geometrii(edits):
    import fcl
    items=json.load(gzip.open(os.path.join(DATA,'geometrie.json.gz'),'rt'))
    G={}
    def bvh(v,f):
        m=fcl.BVHModel(); m.beginModel(len(v),len(f)); m.addSubModel(np.ascontiguousarray(v,float),np.ascontiguousarray(f,np.int32)); m.endModel(); return m
    groups={}
    for it in items:
        v=np.array(it['v'],float).reshape(-1,3); f=np.array(it['f'],int).reshape(-1,3); j=it['owner']; e=edits.get(str(j)) if isinstance(j,int) else None
        if e and it['kind']=='cad' and not it['frame'] and j<22:
            d=np.array(e['d'],float)
            if e.get('rot'):
                Rr,tr=rot(AX[j],e['rot'],M['P'][j])
                if it['link']==PAR[j]: v=v@Rr.T+tr
            if not (e.get('carry') and it['link']==j): v=v+d
        kind='sleeve' if it['key']=='r11_climb_TPU' else ('cover' if it['kind']=='cover' else 'body')
        groups.setdefault((it['link'],kind),[]).append((v,f))
    for k,parts in groups.items():
        vs=[];fs=[];o=0
        for v,f in parts: vs.append(v); fs.append(f+o); o+=len(v)
        V=np.vstack(vs); F=np.vstack(fs); lo,hi=V.min(0),V.max(0)
        corners=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
        G[k]=dict(V=V,obj=fcl.CollisionObject(bvh(V,F),fcl.Transform()),corners=corners)
    adj=lambda a,b:(a<22 and PAR[a]==b) or (b<22 and PAR[b]==a)
    keys=list(G); pairs=[]
    for i in range(len(keys)):
        for j in range(i+1,len(keys)):
            (la,ka),(lb,kb)=keys[i],keys[j]
            if la==lb: continue
            if adj(la,lb) and ka!='cover' and kb!='cover': continue
            pairs.append((keys[i],keys[j]))
    return G,pairs
def mezery(G,pairs,w,exbits,cut=14.0):
    import fcl
    req=fcl.DistanceRequest()
    for (l,k),g in G.items():
        R,t=w[l]; g['obj'].setTransform(fcl.Transform(np.ascontiguousarray(R),np.ascontiguousarray(t))); cw=g['corners']@R.T+t; g['lo']=cw.min(0); g['hi']=cw.max(0)
    best=cut; bp=None
    for a,b in pairs:
        A,B=G[a],G[b]; gap=np.maximum(0,np.maximum(A['lo']-B['hi'],B['lo']-A['hi'])).max()
        if gap>=best: continue
        d=fcl.distance(A['obj'],B['obj'],req,fcl.DistanceResult())
        if d<best: best=d; bp=(a,b)
    ex=set()
    if exbits&1: ex.add((7,'body'))
    if exbits&2: ex.add((17,'body'))
    if exbits&4: ex.add((5,'sleeve'))
    if exbits&8: ex.add((15,'sleeve'))
    env=25.0; ek=None
    for key,g in G.items():
        if key in ex: continue
        R,t=w[key[0]]; V=g['V']@R.T+t
        if g['lo'][2]>env and (g['lo'][1]>env or g['lo'][2]>STEP+env): continue
        z=V[:,2]; dfloor=z.min()
        y=V[:,1]; x=V[:,0]
        dx=np.maximum(np.abs(x)-330,0); dy=np.maximum(np.maximum(y,-280-y),0); dz=np.maximum(z-STEP,0)
        out=np.sqrt(dx*dx+dy*dy+dz*dz); inside=(dx==0)&(dy==0)&(dz==0)
        dstep=np.where(inside,-np.minimum(np.minimum(-y,y+280),STEP-z),out).min()
        d=min(dfloor,dstep)
        if d<env: env=float(d); ek=key
    return float(best),bp,float(env),ek
# ---------- dynamika (MuJoCo) ----------
def mj_xml(P,E,links,mu=0.5,step_h=STEP,mass_scale=1.0,lim_scale=1.0,kp_scale=1.0,G=None):
    MM=1e-3; children={i:[] for i in range(23)}
    for j in range(22): children[PAR[j]].append(j)
    box={}
    for (l,k),g in G.items():
        lo,hi=g['V'].min(0),g['V'].max(0); a,b=box.get(l,(lo,hi)); box[l]=(np.minimum(a,lo),np.maximum(b,hi))
    def inertial(l):
        m=links[l][0]*mass_scale; c=np.array(links[l][1:])*MM; lo,hi=box[l]; d=(hi-lo)*MM*0.75
        I=np.maximum(m/12*np.array([d[1]**2+d[2]**2,d[0]**2+d[2]**2,d[0]**2+d[1]**2]),1e-7)
        return f'<inertial pos="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" mass="{m:.6f}" diaginertia="{I[0]:.3e} {I[1]:.3e} {I[2]:.3e}"/>'
    def geoms(l):
        if l in (7,17): s=1 if l==7 else -1; return f'<geom name="sole{l}" type="box" pos="{s*57*MM:.4f} {-10*MM:.4f} {4*MM:.4f}" size="{38.5*MM:.4f} {60*MM:.4f} {4*MM:.4f}" class="foot"/>'
        if l in (5,15): s=1 if l==5 else -1; return f'<geom name="sleeve{l}" type="capsule" fromto="{s*54*MM:.4f} {-24*MM:.4f} {85*MM:.4f} {s*54*MM:.4f} {-24*MM:.4f} {122*MM:.4f}" size="{8*MM:.4f}" class="pad"/>'
        if l in (10,20): s=1 if l==10 else -1; return f'<geom name="palm{l}" type="sphere" pos="{s*146*MM:.4f} {-12*MM:.4f} {205*MM:.4f}" size="{12*MM:.4f}" class="pad"/>'
        return ''
    def body(j):
        e=np.array(E[j])*MM; a=(np.array(P[j])-np.array(E[j]))*MM
        s=f'<body name="b{j}" pos="{e[0]:.5f} {e[1]:.5f} {e[2]:.5f}">{inertial(j)}<joint name="j{j}" type="hinge" pos="{a[0]:.5f} {a[1]:.5f} {a[2]:.5f}" axis="{AX[j][0]:g} {AX[j][1]:g} {AX[j][2]:g}" damping="0.03" armature="0.004" frictionloss="0.01"/>{geoms(j)}'
        for c in children[j]: s+=body(c)
        return s+'</body>'
    kp={j:(45.0 if LIM[j]>1.2 else 28.0 if LIM[j]>0.5 else 3.0)*kp_scale for j in range(22)}
    act=''.join(f'<position name="a{j}" joint="j{j}" kp="{kp[j]}" kv="{0.02*kp[j]+0.05:.3f}" forcerange="{-LIM[j]*lim_scale:.4f} {LIM[j]*lim_scale:.4f}"/>' for j in range(22))
    return f'''<mujoco model="emil"><compiler angle="degree" inertiafromgeom="false"/>
<option timestep="0.001" integrator="implicitfast" cone="elliptic" impratio="10" noslip_iterations="4"/>
<default><geom condim="4" friction="{mu} 0.005 0.0001" solref="0.004 1" solimp="0.95 0.99 0.0005" contype="1" conaffinity="1"/>
<default class="env"><geom contype="1" conaffinity="2"/></default><default class="foot"><geom contype="2" conaffinity="1"/></default><default class="pad"><geom contype="2" conaffinity="1"/></default></default>
<worldbody><geom name="floor" type="plane" size="2 2 .1" class="env"/><geom name="step" type="box" pos="0 -0.14 {step_h*MM/2:.5f}" size="0.33 0.14 {step_h*MM/2:.5f}" class="env"/>
<body name="b22" pos="0 0 0"><freejoint name="root"/>{inertial(22)}{''.join(body(c) for c in children[22])}</body></worldbody><actuator>{act}</actuator></mujoco>'''
def simuluj(frames,P,E,links,G,ff,mu=0.5,step_h=STEP,mass_scale=1.0,lim_scale=1.0,y_offset=0.0,settle=1.0,tail=3.0,vyvazovani=None):
    import mujoco
    MM=1e-3; m=mujoco.MjModel.from_xml_string(mj_xml(P,E,links,mu,step_h,mass_scale,lim_scale,G=G)); d=mujoco.MjData(m)
    Q=np.radians(np.array([f['q'] for f in frames])); n=len(frames); T=(n-1)/HZ
    kpv=np.array([m.actuator_gainprm[j,0] for j in range(22)]); Q=Q+ff/kpv
    R0,t0=rt2T(frames[0]['rt']); quat=np.zeros(4); mujoco.mju_mat2Quat(quat,np.ascontiguousarray(R0).reshape(-1))
    d.qpos[:3]=(t0+np.array([0,y_offset,0.3]))*MM; d.qpos[3:7]=quat; d.qpos[7:29]=np.radians(frames[0]['q']); d.ctrl[:]=Q[0]; mujoco.mj_forward(m,d)
    dt=m.opt.timestep; nst=int(round((settle+T+tail)/dt)); every=int(round(1/(6*dt))); lim=LIM*lim_scale
    pk=np.zeros(22); tt=[];root=[];qs=[];taupk=[]; div=None; nsat=0; ntot=0; VV=None; oprava=np.zeros(22)
    usej=[j for j in range(22) if j not in (11,21)]
    for k in range(nst):
        t=k*dt-settle; u=min(max(t,0),T)*HZ; i=min(int(u),n-2); a=u-i; d.ctrl[:]=Q[i]*(1-a)+Q[i+1]*a
        if vyvazovani is not None:
            if VV is None:
                import vyvazovani as _v; VV=getattr(_v,vyvazovani.get('trida','Vyvazovani'))(m,vyvazovani['cile'],vyvazovani.get('nez'),**vyvazovani.get('zesileni',{})); VV.ladit=vyvazovani.get('ladit',False); oprava=np.zeros(22)
            if t>=0 and k%20==0:
                fi=min(n-1,max(0,int(round(u)))); oprava=VV.krok(d,fi,rt2T(frames[fi]['rt'])[0],0.02,frames[fi].get('com'))
            d.ctrl[:]+=oprava
        mujoco.mj_step(m,d); af=np.abs(d.actuator_force); pk=np.maximum(pk,af)
        if t>=0: ntot+=1; nsat+=bool((af[usej]>=lim[usej]*0.999).any())
        if (k+1)%every==0: tt.append(t); root.append(d.qpos[:7].copy()); qs.append(np.degrees(d.qpos[7:29])); taupk.append(pk.copy()); pk=np.zeros(22)
        if not np.all(np.isfinite(d.qpos)): div=t; break
    tt=np.array(tt); ok=tt>=0; plan=np.array([rt2T(frames[min(n-1,max(0,int(round(t*HZ))))]['rt'])[1] for t in tt])
    err=np.linalg.norm(np.array(root)[:,:3]/MM-plan,axis=1)
    Rl=[];tilt=[]
    for r,t in zip(root,tt):
        R=np.zeros(9); mujoco.mju_quat2Mat(R,r[3:7]); R=R.reshape(3,3); Rp=rt2T(frames[min(n-1,max(0,int(round(t*HZ))))]['rt'])[0]
        tilt.append(math.degrees(math.acos(max(-1,min(1,(np.trace(R@Rp.T)-1)/2))))); Rl.append(R)
    ratio=np.array(taupk)/lim; ratio[:,[11,21]]=0
    bad=np.where(err>60)[0]
    res=dict(uspech=bool(err[-1]<25 and tilt[-1]<8 and div is None),odchylka_konec_mm=float(err[-1]),odchylka_max_mm=float(err[ok].max()),naklon_konec_deg=float(tilt[-1]),
             moment_max=float(ratio[ok].max()),moment_kloub=JN[int(np.unravel_index(ratio[ok].argmax(),ratio[ok].shape)[1])],pad_s=None if not len(bad) else float(tt[bad[0]]),na_mezi=float(nsat/max(1,ntot)))
    states=[(Rl[i],np.array(root[i][:3])/MM,qs[i],tt[i]) for i in range(len(tt))]
    return res,states
# ---------- hlavní běh ----------
def main():
    src,outdir=sys.argv[1],sys.argv[2]; rychle='--rychle' in sys.argv; os.makedirs(outdir,exist_ok=True); t0=time.time()
    U=json.load(open(src)); tmp=os.path.join(outdir,'prizpusobeni.json')
    subprocess.run(['node',os.path.join(TU,'prizpusob.js'),os.path.join(DATA,'model.json'),src,tmp],check=True)
    A=json.load(open(tmp)); os.remove(tmp)
    ed={str(k):v for k,v in A['edits'].items()}; P=A['P']; E=A['E']; links=A['links']; F=A['frames']; n=len(F)
    REV=M.get('revize','R13'); vychozi='--vychozi' in sys.argv
    ref=json.load(open(os.path.join(DATA,'vychozi.json')))
    log=lambda *a:print(f'[{time.time()-t0:6.0f} s]',*a,flush=True)
    log('statika hotová, upraveno kloubů:',len(ed))
    s50=[f['s50'] for f in F]; bad=[i for i,s in enumerate(s50) if s is None]
    bad4=[i for i,f in enumerate(F) if f['s40'] is None]; bad3=[i for i,f in enumerate(F) if f['s30'] is None]
    fin=[s for s in s50 if s is not None]; pk=max(fin) if fin else None; pki=s50.index(pk) if fin else None
    drift=max(f['drift'] for f in F); shift=max(f['shift'] for f in F)
    G,pairs=nacti_geometrii(ed); log('geometrie',len(G),'skupin,',len(pairs),'dvojic')
    krok=3 if rychle else 1
    def projdi():
        sd=[];en=[]
        for i in range(0,n,krok):
            w=fk(F[i]['q'],F[i]['rt'],P,E); d,bp,e,k=mezery(G,pairs,w,M['ex'][i]); sd.append((d,i,bp)); en.append((e,i,k))
        return sd,en
    selfd,envd=projdi(); log('mezery po přizpůsobení',round(min(x[0] for x in selfd),2),round(min(x[0] for x in envd),2))
    # doladění volných končetin v polohách pod cílem (až 3 kola), pak znovu statika ze stejného jádra
    import doladeni
    zasahy=[]; q_puv=[list(f['q']) for f in F]
    for kolo in range(3):
        if min(x[0] for x in selfd)>=CIL_DOLADENI and min(x[0] for x in envd)>=MEZE['odstup_schod_mm']+0.5: break
        z=doladeni.dolad(F,M,P,E,G,pairs,fk,selfd,CIL_DOLADENI,STEP,log=log,cil_env=MEZE['odstup_schod_mm']+0.5,envd=envd)
        if not z: break
        zasahy+=z; selfd,envd=projdi(); log('kolo',kolo+1,'mezery',round(min(x[0] for x in selfd),2),round(min(x[0] for x in envd),2))
    if zasahy:
        fix=dict(q=[f['q'] for f in F],rt=[f['rt'] for f in F],drift=[f['drift'] for f in F],shift=[f['shift'] for f in F])
        fp=os.path.join(outdir,'_polohy.json'); json.dump(fix,open(fp,'w'))
        subprocess.run(['node',os.path.join(TU,'prizpusob.js'),os.path.join(DATA,'model.json'),src,tmp,fp],check=True)
        F=json.load(open(tmp))['frames']; os.remove(tmp); os.remove(fp)
        s50=[f['s50'] for f in F]; bad=[i for i,s in enumerate(s50) if s is None]
        bad4=[i for i,f in enumerate(F) if f['s40'] is None]; bad3=[i for i,f in enumerate(F) if f['s30'] is None]
        fin=[s for s in s50 if s is not None]; pk=max(fin) if fin else None; pki=s50.index(pk) if fin else None
        log('statika po doladění',pk)
    doladeno=sorted(set(i for z in zasahy for i in range(z['od'],z['do']+1))); dq_max=0.0
    if zasahy:
        dq_max=float(max(abs(np.array(F[i]['q'])-np.array(q_puv[i])).max() for i in range(n)))
    smin=min(selfd,key=lambda x:x[0]); emin=min(envd,key=lambda x:x[0])
    below10=sum(1 for x in selfd if x[0]<10)*krok; below5=sum(1 for x in envd if x[0]<5)*krok
    log('mezery hotové',round(smin[0],2),round(emin[0],2))
    import robustnost
    rob=[robustnost.poloha(fk(F[i]['q'],F[i]['rt'],P,E),M['contacts'][i],links) for i in range(n)]
    ref_rob=json.load(open(os.path.join(DATA,'vychozi-robustnost.json')))
    slab=lambda L:[i for i,o in enumerate(L) if o['marg']<ROBUST['rezerva_mm'] or o['fnez']<ROBUST['predzatizeni_N']]
    sl=slab(rob); sl0=slab(ref_rob)
    useky_sl=[]
    for i in sl:
        if useky_sl and i-useky_sl[-1][1]<=6: useky_sl[-1][1]=i
        else: useky_sl.append([i,i])
    robust_souhrn=dict(slabych=len(sl),slabych_R13=len(sl0),rezerva_min=min(o['marg'] for o in rob),rezerva_min_R13=min(o['marg'] for o in ref_rob),
        predzatizeni_min=min(o['fnez'] for o in rob),predzatizeni_min_R13=min(o['fnez'] for o in ref_rob),
        useky=[dict(od=a/HZ,do=b/HZ,rezerva=min(rob[i]['marg'] for i in range(a,b+1)),predzatizeni=min(rob[i]['fnez'] for i in range(a,b+1)),
               opora=robustnost.JMENO.get(min((rob[i] for i in range(a,b+1)),key=lambda o:o['fnez'])['slaba'],'')) for a,b in useky_sl])
    log('robustnost: slabých poloh',len(sl),f'(výchozí {REV}',len(sl0),')')
    from scipy.ndimage import gaussian_filter1d
    ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
    varianty={'nominal':{},'schod 205 mm':dict(step_h=205.0),'schod 215 mm':dict(step_h=215.0),'tření 0,35':dict(mu=0.35),'hmotnost +10 %':dict(mass_scale=1.1),'o 5 mm blíž':dict(y_offset=-5.0),'serva 85 %':dict(lim_scale=0.85),'schod 202 mm':dict(step_h=202.0),'schod 218 mm':dict(step_h=218.0)}
    POVINNE=('nominal','schod 205 mm','schod 215 mm')
    if rychle: varianty={'nominal':{}}
    dyn={}; simstates=None
    def pohyb_pro_vysku(h):
        # robot změří výšku schodu a od M['vyska_od_s'] přelez přizpůsobí (stejné jádro, stejné úpravy)
        if 'vyska_od_s' not in M or abs(h-STEP)<1e-6: return F,ff
        uv=dict(U); uv['vyska_dh']=h-STEP; up=os.path.join(outdir,'_vyska.json'); json.dump(uv,open(up,'w'))
        subprocess.run(['node',os.path.join(TU,'prizpusob.js'),os.path.join(DATA,'model.json'),up,tmp],check=True,capture_output=True)
        Fh=json.load(open(tmp))['frames']; os.remove(tmp); os.remove(up)
        fh=np.array([f['ff'] if f['ff'] else [0]*22 for f in Fh]); fh[:,[11,21]]=0
        return Fh,gaussian_filter1d(fh,1.5,axis=0,mode='nearest')
    for name,kw in varianty.items():
        if bad: dyn[name]=dict(uspech=False,poznamka='nespuštěno – chybí rovnováha'); continue
        Fv,ffv=pohyb_pro_vysku(kw.get('step_h',STEP))
        r,st=simuluj(Fv,P,E,links,G,ffv,**kw); dyn[name]=r
        if name=='nominal': simstates=st
        log('dynamika',name,r['uspech'],round(r['odchylka_konec_mm'],1))
    simclr=None
    if simstates:
        sd=[];se=[]
        for R,t,q,tt in simstates[::2 if not rychle else 6]:
            i=min(n-1,max(0,int(round(tt*HZ)))); w=fk(q,list(R.T.reshape(-1))+list(t),P,E); d,_,e,_=mezery(G,pairs,w,M['ex'][i]); sd.append(d); se.append(e)
        simclr=dict(mezera_dilu_mm=float(min(sd)),odstup_schod_mm=float(min(se)))
    kontroly=[
      ('Rovnováha ve všech polohách (tření 0,5 / 0,4 / 0,3)',not bad and not bad4 and not bad3,f'bez rovnováhy {len(bad)} / {len(bad4)} / {len(bad3)} z {n}'),
      (f'Nejvyšší využití serva ≤ {MEZE["max_vyuziti"]*100:.0f} %',pk is not None and pk<=MEZE['max_vyuziti'],'—' if pk is None else f'{pk*100:.1f} % ({JN[F[pki]["j50"]]}, {pki/HZ:.1f} s)'),
      (f'Mezera mezi díly ≥ {MEZE["mezera_dilu_mm"]:.0f} mm',smin[0]>=MEZE['mezera_dilu_mm'],f'{smin[0]:.2f} mm ({smin[1]/HZ:.1f} s)'),
      (f'Odstup od podlahy a schodu ≥ {MEZE["odstup_schod_mm"]:.0f} mm',emin[0]>=MEZE['odstup_schod_mm'],f'{emin[0]:.2f} mm ({emin[1]/HZ:.1f} s)'),
      (f'Opory zůstávají na místě (≤ {MEZE["posun_opory_mm"]} mm)',drift<=MEZE['posun_opory_mm'],f'{drift:.3f} mm'),
      ('Dynamická simulace doběhne (nominální)',dyn.get('nominal',{}).get('uspech',False),'—' if 'odchylka_konec_mm' not in dyn.get('nominal',{}) else f'odchylka na konci {dyn["nominal"]["odchylka_konec_mm"]:.1f} mm'),
      ('Schod o ±5 mm jiný (205 a 215 mm) – dynamika doběhne',all(dyn.get(k,{}).get('uspech',False) for k in ('schod 205 mm','schod 215 mm')) or rychle,'rychlá kontrola – nepočítáno' if rychle else ', '.join(f'{k[6:]}: {"OK" if dyn.get(k,{}).get("uspech") else "pád"}' for k in ('schod 205 mm','schod 215 mm'))),
    ]
    proslo=all(k[1] for k in kontroly)
    r13dyn=json.load(open(os.path.join(DATA,'vychozi-dynamika.json')))
    varovani=[f'Dynamická simulace ve variantě „{k}“ nedoběhla (robot se odchýlil o {v.get("odchylka_konec_mm",0):.0f} mm). ' + (f'Výchozí {REV} ji zvládá – úprava rezervu zhoršila.' if r13dyn.get(k) else f'Nezvládá ji ani výchozí {REV} – slabina přelezu, ne úpravy.') for k,v in dyn.items() if k not in POVINNE and not v.get('uspech',True)]
    if robust_souhrn['slabych']>robust_souhrn['slabych_R13']+12 or robust_souhrn['rezerva_min']<robust_souhrn['rezerva_min_R13']-2 or robust_souhrn['predzatizeni_min']<robust_souhrn['predzatizeni_min_R13']-1:
        varovani.append(f"Robustnost je horší než u výchozího {REV}: slabých poloh {robust_souhrn['slabych']} ({REV} {robust_souhrn['slabych_R13']}), nejmenší rezerva těžiště {robust_souhrn['rezerva_min']:.1f} mm ({REV} {robust_souhrn['rezerva_min_R13']:.1f}), nejmenší zatížení nezbytné opory {robust_souhrn['predzatizeni_min']:.1f} N ({REV} {robust_souhrn['predzatizeni_min_R13']:.1f}).")
    R=dict(verze_kontroly=4,revize=REV,robustnost=robust_souhrn,proslo=proslo,varovani=varovani,rychla=rychle,meze=MEZE,upravy=U.get('upravy',{}),kontroly=[dict(nazev=a,ok=bool(b),hodnota=c) for a,b,c in kontroly],
      statika=dict(max=pk,max_s=None if pki is None else pki/HZ,max_kloub=None if pki is None else JN[F[pki]['j50']],vychozi_max=max(x for x in ref['s50'] if x is not None),bez_rovnovahy=bad[:50],posun_trupu_mm=shift,posun_opory_mm=drift),
      mezery=dict(dily_mm=smin[0],dily_s=smin[1]/HZ,dily_par=[f'L{a[0]} {a[1]}' for a in (smin[2] or [])],pod_10mm=below10,schod_mm=emin[0],schod_s=emin[1]/HZ,schod_dil=None if not emin[2] else f'L{emin[2][0]} {emin[2][1]}',pod_5mm=below5,
        vychozi_dily_mm=min(x for x in ref['self'] if x is not None),vychozi_schod_mm=min(x for x in ref['env'] if x is not None)),
      doladeni=dict(polohy=len(doladeno),useky=zasahy,max_zmena_deg=dq_max,cil_mm=CIL_DOLADENI),
      dynamika=dyn,mezery_v_simulaci=simclr,cas_s=round(time.time()-t0),polohy=n,
      hash_upravy=hashlib.sha256(json.dumps(U.get('upravy',{}),sort_keys=True).encode()).hexdigest()[:12])
    json.dump(R,open(os.path.join(outdir,'vysledek.json'),'w'),ensure_ascii=False,indent=1)
    json.dump(dict(upravy=U.get('upravy',{}),q=[f['q'] for f in F],rt=[f['rt'] for f in F],s50=s50),open(os.path.join(outdir,'pohyb.json'),'w'))
    md=[f'# Kontrola úpravy kloubů – {"PROŠLO" if proslo else "NEPROŠLO"}','',f'Úprava `{R["hash_upravy"]}` · {n} poloh přelezu 21 cm · {R["cas_s"]} s výpočtu'+(' · **rychlá kontrola (mezery každá 3. poloha, jen nominální dynamika)**' if rychle else ''),'','## Úprava','']
    for j,e in sorted(U.get('upravy',{}).items(),key=lambda x:int(x[0])):
        d=np.array(e.get('posun_mm',[0,0,0]),float); a=AX[int(j)]/np.linalg.norm(AX[int(j)]); al=abs(float(d@a)); pe=float(np.linalg.norm(d-(d@a)*a))
        md.append(f'- {JN[int(j)]}: posun {e.get("posun_mm")} mm' + (', nese další díly' if e.get('nese_dalsi_dily') else '') + f' – podél osy kloubu {al:.1f} mm, napříč {pe:.1f} mm')
        if al>1 and pe<1 and not e.get('nese_dalsi_dily'): md.append(f'  - ⚠️ Posun vede jen podél osy: pohyb a síly se téměř nemění, mění se poloha a hmotnost serva a vidlice se musí prodloužit o {al:.0f} mm.')
    md+=['','## Kontroly','','| Kontrola | Výsledek | Hodnota |','|---|---|---|']+[f'| {a} | {"✅" if b else "❌"} | {c} |' for a,b,c in kontroly]
    if varovani: md+=['','## ⚠️ Varování (verdikt neovlivňují)','']+[f'- {v}' for v in varovani]
    md+=['',f'## Srovnání s výchozím {REV}','',f'| | {REV} | Po úpravě |','|---|---|---|',
      f'| Nejvyšší využití serva (tření 0,5) | {R["statika"]["vychozi_max"]*100:.1f} % | {"—" if pk is None else f"{pk*100:.1f} %"} |',
      f'| Nejmenší mezera mezi díly | {R["mezery"]["vychozi_dily_mm"]:.2f} mm | {smin[0]:.2f} mm |',
      f'| Polohy s mezerou pod 10 mm | {sum(1 for x in ref["self"] if x is not None and x<10)} | {below10} |',
      f'| Nejmenší odstup od schodu | {R["mezery"]["vychozi_schod_mm"]:.2f} mm | {emin[0]:.2f} mm |',
      f'| Největší posun trupu oproti {REV} | 0 mm | {shift:.1f} mm |','','## Doladění volných končetin','',
      (f'Doladěné úseky švihu: {len(zasahy)} ({len(doladeno)} poloh), klouby volné končetiny pootočeny nejvýš o {dq_max:.1f}° s plynulým náběhem; cíl {CIL_DOLADENI} mm. Opory a trup beze změny.' if zasahy else 'Nebylo potřeba.'),*[f'- {z["koncetina"].replace("_"," ")} {z["od"]/HZ:.1f}–{z["do"]/HZ:.1f} s: nejtěsnější místo úseku {z["pred"]-CIL_DOLADENI:+.2f} mm vůči cíli → ' + (f'{z["po"]-CIL_DOLADENI:+.2f} mm' if z["po"]<CIL_DOLADENI+0.79 else 'aspoň +0,8 mm') + f', změna úhlů {z["zmena"]}°' for z in zasahy],'','## Dynamická simulace','','| Varianta | Doběhne | Odchylka na konci | Špička momentu |','|---|---|---|---|']
    for k,v in dyn.items():
        md.append(f'| {k} | {"✅" if v.get("uspech") else "❌"} | {v.get("odchylka_konec_mm",float("nan")):.1f} mm | {v.get("moment_max",float("nan"))*100:.0f} % ({v.get("moment_kloub","")}), na mezi {v.get("na_mezi",0)*100:.1f} % času |' if 'odchylka_konec_mm' in v else f'| {k} | ❌ | {v.get("poznamka","")} | |')
    md+=['','## Robustnost (rezerva těžiště a předzatížení opor)','',f'Slabé místo = rezerva těžiště pod {ROBUST["rezerva_mm"]:.0f} mm nebo opora, bez které by robot nestál, nese méně než {ROBUST["predzatizeni_N"]:.0f} N.','',
      f'| | {REV} | Po úpravě |','|---|---|---|',f'| Slabých poloh | {robust_souhrn["slabych_R13"]} | {robust_souhrn["slabych"]} |',
      f'| Nejmenší rezerva těžiště | {robust_souhrn["rezerva_min_R13"]:.1f} mm | {robust_souhrn["rezerva_min"]:.1f} mm |',f'| Nejmenší zatížení nezbytné opory | {robust_souhrn["predzatizeni_min_R13"]:.1f} N | {robust_souhrn["predzatizeni_min"]:.1f} N |','']
    md+=[f'- {u["od"]:.1f}–{u["do"]:.1f} s: rezerva {u["rezerva"]:.1f} mm, nejslabší nezbytná opora {u["opora"]} {u["predzatizeni"]:.1f} N' for u in robust_souhrn['useky'] if u['do']-u['od']>=1.0]
    if simclr: md+=['',f'Mezery v simulovaném pohybu: díly {simclr["mezera_dilu_mm"]:.1f} mm, schod {simclr["odstup_schod_mm"]:.1f} mm (informativní).']
    md+=['','## Co tato kontrola nedělá','','- Pohyb se přizpůsobí nové geometrii a doladí se jen švih volných končetin; trup ani rozložení sil se znovu neoptimalizují.',
      '- Rámy a vidlice v modelu se nepřekreslují – posouvá se servo a osa. Střet serva s vlastním rámem se nekontroluje.',
      '- Chůze, sed a další pohyby se v této kontrole nepočítají (přepočítá je simulátor v prohlížeči).',
      f'- Dynamika je předkorigovaná podle statiky (jako u R13); bez předkorekce přelez nedoběhne. Krátké špičky na mezi serva má i výchozí {REV}.','- Zkoušky jiné výšky schodu počítají s tím, že robot výšku změří přesně a od 30. s přelez přizpůsobí (chyba měření ±2 mm toleranci zužuje; doladění švihu se u nich neopakuje).','- Robot se v simulaci řídí jen předem spočítanými povely bez zpětné vazby (bez IMU); skutečný robot s vyvažováním bude robustnější, bez něj méně.','- Fyzicky nic neověřeno.']
    open(os.path.join(outdir,'protokol.md'),'w').write('\n'.join(md)+'\n')
    if vychozi:
        # srovnávací hodnoty výchozího pohybu (spouštět bez úprav a bez --rychle): python3 -I prepocet.py nula.json výstup --vychozi
        assert not U.get('upravy') and not rychle, 'srovnávací hodnoty jen z výchozího pohybu bez úprav a bez --rychle'
        sv=[None]*n; ev=[None]*n
        for d,i,_ in selfd: sv[i]=round(d,3)
        for e,i,_ in envd: ev[i]=round(e,3)
        json.dump(dict(revize=REV,self=sv,env=ev,s50=s50,s40=[f['s40'] for f in F],s30=[f['s30'] for f in F]),open(os.path.join(DATA,'vychozi.json'),'w'))
        json.dump(rob,open(os.path.join(DATA,'vychozi-robustnost.json'),'w'))
        json.dump({k:bool(v.get('uspech')) for k,v in dyn.items()},open(os.path.join(DATA,'vychozi-dynamika.json'),'w'),ensure_ascii=False,indent=1)
        log('srovnávací hodnoty zapsány',REV)
    log('HOTOVO', 'PROŠLO' if proslo else 'NEPROŠLO')
    return 0
if __name__=='__main__': sys.exit(main())
