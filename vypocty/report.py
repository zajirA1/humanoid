import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
import json, html as H, fork
def cz(x,d=1): return (f'{x:.{d}f}').replace('.',',')
def pct(x,d=0): return cz(100*x,d)+' %'
C12='#c2571a'; C13='#2a78d6'
SERVO={0.104:'XL330',0.980665:'STS3215',1.569064:'STS3250',2.24152:'2× STS3250'}
def chart(sB,sN,recs,phases):
    W_,H_=980,300; ml,mr,mt,mb=46,16,26,34; tmax=max(len(sB),len(sN))/HZ; ymax=1.0
    X=lambda t:ml+(W_-ml-mr)*t/tmax; Y=lambda v:mt+(H_-mt-mb)*(1-v/ymax)
    def path(sv): return 'M'+' L'.join(f'{X(i/HZ):.1f},{Y(min(v,ymax)):.1f}' for i,v in enumerate(sv))
    o=[f'<svg id="r13Chart" viewBox="0 0 {W_} {H_}" role="img" aria-label="Využití nejzatíženějšího serva během přelezu, R12 a R13">']
    ph=np.array([r['phase'] for r in recs])
    for k in range(int(ph.max())+1):
        idx=np.where(ph==k)[0]
        if len(idx)==0: continue
        x0,x1=X(idx[0]/HZ),X((idx[-1]+1)/HZ)
        if k%2==0: o.append(f'<rect x="{x0:.1f}" y="{mt}" width="{x1-x0:.1f}" height="{H_-mt-mb}" fill="#eef1ea"/>')
        o.append(f'<text x="{(x0+x1)/2:.1f}" y="{mt-8}" text-anchor="middle" font-size="10" fill="#5d6f67">{k+1}</text>')
    for v in (0,0.25,0.5,0.75,1.0):
        o.append(f'<line x1="{ml}" x2="{W_-mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#c9d3cb" stroke-width="1"/><text x="{ml-6}" y="{Y(v)+4:.1f}" text-anchor="end" font-size="11" fill="#4c655a">{int(v*100)} %</text>')
    for t in range(0,int(tmax)+1,20):
        o.append(f'<text x="{X(t):.1f}" y="{H_-mb+16}" text-anchor="middle" font-size="11" fill="#4c655a">{t} s</text>')
    o.append(f'<path d="{path(sB)}" fill="none" stroke="{C12}" stroke-width="2" stroke-linejoin="round"/>')
    o.append(f'<path d="{path(sN)}" fill="none" stroke="{C13}" stroke-width="2" stroke-linejoin="round"/>')
    iB=int(np.argmax(sB)); iN=int(np.argmax(sN))
    o.append(f'<circle cx="{X(iB/HZ):.1f}" cy="{Y(sB[iB]):.1f}" r="4" fill="{C12}" stroke="#fffdf6" stroke-width="2"/><text x="{X(iB/HZ)+8:.1f}" y="{Y(sB[iB])-6:.1f}" font-size="12" fill="#193733">R12 · {pct(sB[iB],1)}</text>')
    o.append(f'<circle cx="{X(iN/HZ):.1f}" cy="{Y(sN[iN]):.1f}" r="4" fill="{C13}" stroke="#fffdf6" stroke-width="2"/><text x="{X(iN/HZ)-8:.1f}" y="{Y(sN[iN])-8:.1f}" text-anchor="end" font-size="12" fill="#193733">R13 · {pct(sN[iN],1)}</text>')
    o.append(f'<line id="r13Cross" x1="0" x2="0" y1="{mt}" y2="{H_-mb}" stroke="#193733" stroke-width="1" visibility="hidden"/><rect id="r13Hit" x="{ml}" y="{mt}" width="{W_-ml-mr}" height="{H_-mt-mb}" fill="transparent"/></svg>')
    return '\n'.join(o),dict(ml=ml,mr=mr,W=W_,tmax=tmax)
def build_report(recs,rows,brecs,brows,TN,TB,scen,G,sN,sB,tauN,tauB,selfc,oldcase):
    n=len(recs); nb=len(brecs); lim=LIM
    phases=[p['name'] for p in __import__('export').PH]
    svg,geo=chart(sB,sN,recs,phases)
    # ---- per-joint table
    rN=np.abs(tauN).max(0); rB=np.abs(tauB).max(0)
    oth=np.zeros(22); othname=['']*22
    for k,v in scen.items():
        if not isinstance(v,dict): continue
        for j in range(22):
            if v['maxTau'][j]>oth[j]: oth[j]=v['maxTau'][j]; othname[j]=k
    lab={'sit':'sed a vstávání','walk':'chůze','dance':'tanec','home':'stoj'}
    def sname(k):
        if k.startswith('pickup'):
            p=k.split('/'); return 'zvedání · '+{'mug':'hrnek','sock':'ponožka','box':'krabička'}.get(p[1],p[1])
        if k.startswith('stairs'): return 'schody s opěrami '+k.split('/')[1][:2]+' cm'
        if k.startswith('turn'): return 'otočení'
        return lab.get(k,k)
    jr=[]
    for j in [2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20]:
        allmax=max(rN[j],oth[j]); cls=SERVO[min(SERVO,key=lambda x:abs(x-lim[j]))]
        weaker=0.980665 if lim[j]>1.2 else None
        verdict='ponechat'
        if weaker and allmax<=0.6*weaker: verdict='STS3215 by stačilo (≤ 60 %)'
        elif weaker and allmax<=0.8*weaker: verdict='STS3215 jen s malou rezervou'
        jr.append(f'<tr><th scope="row">{H.escape(JN[j])}</th><td>{cls}<br><small>{cz(lim[j],2)} N·m</small></td><td>{cz(rB[j],2)}<br><small>{pct(rB[j]/lim[j])}</small></td><td><b>{cz(rN[j],2)}</b><br><small>{pct(rN[j]/lim[j])}</small></td><td>{cz(oth[j],2)}<br><small>{H.escape(sname(othname[j]))}</small></td><td>{verdict}</td></tr>')
    # ---- per-phase table
    phB=np.array([r['phase'] for r in brecs]); phN=np.array([r['phase'] for r in recs]); bn=[p['name'] for p in json.load(open(W+'r9ClimbData.json'))['phases']]
    pr=[]
    for k,name in enumerate(phases):
        iN=np.where(phN==k)[0]
        if k<=12: iB=np.where(phB==k)[0]; bl=pct(sB[iB].max())
        elif k==13: bl='—'
        else: iB=np.where(phB==k-1)[0]; bl=pct(sB[iB].max())+f' <small>({H.escape(bn[k-1])})</small>'
        kk=iN[int(sN[iN].argmax())]; pr.append(f'<tr><th scope="row">{k+1}. {H.escape(name)}</th><td>{bl}</td><td><b>{pct(sN[kk])}</b></td><td>{H.escape(JN[rows[kk]["r"]["jmax"]])}</td><td>{cz(len(iN)/HZ,0)} s</td></tr>')
    # ---- shoulders over palms, shin loading
    def sh_off(rcs,rws):
        d=[]
        for rec,row in zip(rcs,rws):
            F=row['r']['forces']
            for sd,nm,j in (('L','leftPalm',9),('R','rightPalm',19)):
                if nm in F and F[nm][2]>2.0:
                    st=rec['state']; c=st.pt(ARM[sd],refpt(sd,'P')); d.append((float(np.hypot(*(st.piv[j][:2]-c[:2]))),float(F[nm][2])))
        d=np.array(d); return float((d[:,0]*d[:,1]).sum()/d[:,1].sum()),float(d[:,0].max())
    offB=sh_off(brecs,brows); offN=sh_off(recs,rows)
    def shin_lead(rcs,rws):
        lift=next(i for i,r in enumerate(rcs) if i>150 and 'rightFoot' not in r['contacts'] and 'leftKnee' in r['contacts'])
        k=lift
        while k>0 and rws[k-1]['r']['forces'].get('leftKnee',np.zeros(3))[2]>=10.0: k-=1
        return (lift-k)/HZ,float(rws[lift]['r']['forces'].get('leftKnee',np.zeros(3))[2]),lift
    leadB=shin_lead(brecs,brows); leadN=shin_lead(recs,rows)
    jB=18; fB=int(np.argmax(np.abs(tauB[:,jB]))); 
    # ---- fork table
    bN,aN,_=fork.loads(recs,rows); bB,aB,_=fork.loads(brecs,brows)
    fr=[]
    for j in (8,9,10,2,3,4,5,6,7):
        g=G.get(j); jj=[j,j+10]
        bmB=bB[:,jj].max(); bmN=bN[:,jj].max(); axB=aB[:,jj].max(); axN=aN[:,jj].max()
        if g and g['bridge']:
            t=min(g['t']); I=g['width']*t**3/12; k=3*fork.E_PETG*I/g['bridge']**3; dfl=axN/k
            geo_=f'{cz(g["t"][0],1)} / {cz(g["t"][1],1)} mm · rozteč {cz(g["span"],1)} mm · osa–můstek {cz(g["bridge"],1)} mm'; dtx=f'{cz(dfl,2)} mm'; cpl=f'{cz(bmN/(g["span"]/1000),0)} N'
        else: geo_='dvojice serv proti sobě, bez tištěné vidlice'; dtx='—'; cpl='—'
        fr.append(f'<tr><th scope="row">{H.escape(JN[j].replace(" · L",""))}</th><td>{geo_}</td><td>{cz(bmB,2)} → <b>{cz(bmN,2)}</b> N·m</td><td>{cz(axB,1)} → <b>{cz(axN,1)}</b> N</td><td>{cpl}</td><td>{dtx}</td></tr>')
    # ---- tests
    def ok(c): return '<span class="r13-ok">✓ splněno</span>' if c else '<span class="r13-no">✗ nesplněno</span>'
    S=TN.get('sim',{}); SB=TB.get('sim',{})
    def simrow(name,label):
        a=S.get(name,{}).get('res'); b=SB.get(name,{}).get('res')
        def one(r):
            if r is None: return '—'
            if r['success']: return f'<span class="r13-ok">✓ dokončeno</span><br><small>odchylka pánve na konci {cz(r["root_err_end"],0)} mm</small>'
            return f'<span class="r13-no">✗ pád</span><br><small>v čase {cz(r["fall_t"] or 0,0)} s</small>'
        return f'<tr><th scope="row">{label}</th><td>{one(b)}</td><td>{one(a)}</td></tr>'
    simrows=''.join(simrow(k,l) for k,l in (('nominal','Jmenovité podmínky (tření 0,50, moment omezen na pracovní hodnotu)'),('stall','Moment omezen až na blokovací hodnotu (3×)'),('noff','Bez předkorekce povelů'),('mu035','Tření 0,35'),('mu070','Tření 0,70'),('step205','Schod o 5 mm nižší (205 mm)'),('step215','Schod o 5 mm vyšší (215 mm)'),('mass110','Robot o 10 % těžší'),('near5','Start o 5 mm blíž ke schodu'),('far5','Start o 5 mm dál od schodu'),('weak85','Serva o 15 % slabší'),('soft60','Serva o 40 % poddajnější')))
    nsim_ok=sum(1 for v in S.values() if v['res']['success']); nsim=len(S)
    envB=0.25
    tests=[('Rovnováha ve všech polohách, tření 0,50',f'{TN["mu50"]["feasible"]} / {n} poloh, špička {pct(TN["mu50"]["peak"],1)}',f'{TB["mu50"]["feasible"]} / {nb}, špička {pct(TB["mu50"]["peak"],1)}',TN['mu50']['feasible']==n and TN['mu50']['peak']<1),
           ('Totéž při tření 0,40 a 0,30',f'{TN["mu40"]["feasible"]} a {TN["mu30"]["feasible"]} poloh, špičky {pct(TN["mu40"]["peak"],1)} a {pct(TN["mu30"]["peak"],1)}',f'špičky {pct(TB["mu40"]["peak"],1)} a {pct(TB["mu30"]["peak"],1)}',TN['mu30']['feasible']==n and TN['mu30']['peak']<1),
           ('Tření 0,10 a téměř žádné (0,02): opory tlačí jen svisle',f'{TN["mu10"]["feasible"]} a {TN["mu02"]["feasible"]} poloh, špičky {pct(TN["mu10"]["peak"],1)} a {pct(TN["mu02"]["peak"],1)}',f'špičky {pct(TB["mu10"]["peak"],1)} a {pct(TB["mu02"]["peak"],1)}',TN['mu02']['feasible']==n and TN['mu02']['peak']<1),
           ('Robot o 10 % těžší',f'špička {pct(TN["mass110"]["peak"],1)}',f'špička {pct(TB["mass110"]["peak"],1)}',TN['mass110']['peak']<1),
           ('Polohy v polovině mezi snímky',f'{TN["mid"]["feasible"]} / {TN["mid"]["n"]} s rovnováhou, špička {pct(TN["mid"]["peak"],1)}',f'{TB["mid"]["feasible"]} / {TB["mid"]["n"]}',TN['mid']['feasible']==TN['mid']['n']),
           ('Těžiště uvnitř opor (nejmenší rezerva)',f'{cz(TN["margin"]["min"],1)} mm',f'{cz(TB["margin"]["min"],1)} mm',TN['margin']['min']>3),
           ('Díly mimo opěrné plochy vůči schodu a podlaze, cíl ≥ 5 mm',f'nejméně {cz(TN["env"]["min"],1)} mm, pod 5 mm v {TN["envbelow5"]} polohách','0,25 mm (rám bérce, poloha 231)',TN['env']['min']>=5),
           ('Nesousední díly robota mezi sebou, cíl ≥ 10 mm',f'nejméně {cz(TN["self"]["min"],1)} mm, pod 10 mm v {TN["below10"]} polohách; mezi snímky {cz(TN["mid"]["self"],1)} mm',f'nejméně {cz(TB["self"]["min"],1)} mm, pod 10 mm v {TB["below10"]} polohách',TN['self']['min']>=10 and TN['mid']['self']>=10),
           ('Sousední rámy v kloubech (rozsah použitých úhlů)',f'nejméně {cz(TN["adjmin"],2)} mm',f'{cz(TB["adjmin"],2)} mm',TN['adjmin']>=2.0),
           ('Rychlost kloubů',f'nejvýše {cz(TN["speedmax"]["v"],0)} °/s ({H.escape(TN["speedmax"]["joint"])})',f'{cz(TB["speedmax"]["v"],0)} °/s',TN['speedmax']['v']<120),
           ('Opěrné plochy se nezabořují do schodu',f'nejvýše {cz(TN["pen"],2)} mm',f'{cz(TB["pen"],2)} mm',TN['pen']<0.5)]
    if 'simclear' in TN: tests.append(('Odstupy v simulovaném (ne plánovaném) pohybu',f'od schodu {cz(max(0,TN["simclear"]["env"]),1)} mm, mezi díly {cz(TN["simclear"]["self"],1)} mm','—',TN['simclear']['env']>=3))
    trs=''.join(f'<tr><th scope="row">{a}</th><td>{c}</td><td><b>{b}</b></td><td>{ok(d)}</td></tr>' for a,b,c,d in tests)
    simnote=''
    if S:
        nomN=S['nominal']['res']; nomB=SB['nominal']['res'] if SB else None
        simnote=(f'<p>Dynamická simulace přehrává povely serv v otevřené smyčce, tedy bez zpětné vazby z čidel. Každý povel je předem posunutý o očekávaný moment kloubu dělený tuhostí serva (moment počítaný pro svislé reakce opor); bez této předkorekce se tělo prověsí a přelez nedoběhne. '
                 +(f'Nový přelez v ní za jmenovitých podmínek doběhl do stoje na schodu.' if nomN['success'] else f'Nový přelez v ní za jmenovitých podmínek <b>nedoběhl</b>: robot se zřítil v čase {cz(nomN["fall_t"] or 0,0)} s.')
                 +(f' Původní přelez R12 ve stejném modelu spadl v čase {cz(nomB["fall_t"] or 0,0)} s.' if nomB and not nomB['success'] else (' Původní přelez R12 ve stejném modelu doběhl.' if nomB else ''))
                 +f' Z {nsim} variant doběhlo {nsim_ok}. Model používá zjednodušená kontaktní tělesa (plocha chodidla, válec návleku, koule dlaně) a tuhost serv odhadem, takže výsledek ber jako přísnou zkoušku citlivosti, ne jako předpověď.</p>')
    simk=('doběhl' if (S and S['nominal']['res']['success']) else 'nedoběhl') if S else '—'
    simkb=('doběhl' if (SB and SB['nominal']['res']['success']) else 'pád') if SB else '—'
    Qz=np.array([rc_['state'].q for rc_ in recs]); dz=np.diff(Qz,axis=0); nzz=int(((dz[1:]*dz[:-1]<0)&(np.abs(dz[1:])>1.2)&(np.abs(dz[:-1])>1.2)).sum())
    kpi=[('Nejvyšší využití serva',pct(sB.max(),1),pct(sN.max(),1),'statika, tření 0,50'),
         ('Pravé rameno předozadně',f'{cz(rB[18],2)} N·m',f'{cz(rN[18],2)} N·m',f'{pct(rB[18]/lim[18])} → {pct(rN[18]/lim[18])} z 0,98 N·m'),
         ('Odstup dílů od schodu',f'{cz(envB,2)} mm',f'{cz(TN["env"]["min"],1)} mm','díly, které se dotýkat nemají'),
         ('Dynamická simulace',simkb,simk,f'{nsim_ok} z {nsim} variant doběhlo')]
    kp=''.join(f'<div class="r13-kpi"><span>{a}</span><b>{c}</b><small>R12: {b} · {d}</small></div>' for a,b,c,d in kpi)
    data=json.dumps(dict(b=[round(float(x),3) for x in sB],n=[round(float(x),3) for x in sN],ph=[int(r['phase']) for r in recs],names=phases,jn=[JN[r['r']['jmax']] for r in rows],jb=[JN[r['r']['jmax']] for r in brows],geo=geo,hz=HZ,peak=int(np.argmax(sN)),lift=int(leadN[2])),ensure_ascii=False,separators=(',',':'))
    css='''<style id="r13Styles">#r13{border:1px solid #b4c8bc;border-radius:13px;background:#fffdf6;padding:clamp(14px,2vw,26px);margin:0 0 22px}#r13 h2{font:normal clamp(24px,3vw,36px)/1.12 Georgia,serif;letter-spacing:-.02em;margin:2px 0 8px}#r13 h3{font:600 15px/1.3 "Segoe UI",system-ui,sans-serif;margin:18px 0 6px}#r13 p{max-width:95ch;margin:6px 0}#r13 .r13-lead{font-size:16px}#r13 .r13-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:14px 0}.r13-kpi{border:1px solid #cfdbd1;border-radius:9px;padding:10px 12px;background:#f6f4ee}.r13-kpi span{display:block;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:#53756c}.r13-kpi b{display:block;font:normal 30px/1.15 Georgia,serif;color:#193733;font-variant-numeric:tabular-nums}.r13-kpi small{color:#4c655a;font-size:12.5px}#r13 .r13-chartwrap{position:relative;border:1px solid #cfdbd1;border-radius:9px;background:#fcfcfb;padding:8px 8px 2px;margin:8px 0}#r13Chart{width:100%;height:auto;display:block}#r13 .r13-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#274f46;padding:2px 6px 6px}#r13 .r13-legend i{display:inline-block;width:18px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}#r13Tip{position:absolute;pointer-events:none;background:#193733;color:#fff;font-size:12.5px;line-height:1.35;padding:6px 9px;border-radius:6px;white-space:nowrap;transform:translate(-50%,-110%);visibility:hidden;z-index:2}#r13 table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0}#r13 th,#r13 td{border-bottom:1px solid #dbe4dc;padding:5px 8px;text-align:left;vertical-align:top}#r13 thead th{font-weight:600;color:#3d5a50;border-bottom:1px solid #9fb5a9}#r13 td small,#r13 th small{color:#5d6f67;font-weight:400}#r13 details{border-top:1px solid #cfdbd1;padding:9px 0}#r13 details:last-of-type{border-bottom:1px solid #cfdbd1}#r13 summary{cursor:pointer;font-weight:600;font-size:15px}#r13 .r13-scroll{overflow-x:auto}.r13-ok{color:#1c6b45;font-weight:600}.r13-no{color:#a13a22;font-weight:600}#r13 .r13-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 4px}#r13 .r13-note{background:#f3ece0;border-left:3px solid #ad653a;padding:8px 12px;border-radius:0 7px 7px 0;margin:10px 0}#r13 ul{margin:6px 0;padding-left:20px;max-width:95ch}#r13 li{margin:3px 0}</style>'''
    simok=bool(S) and S['nominal']['res']['success']
    htmlr=f'''{css}<section id="r13" aria-labelledby="r13Title">
<div class="brand">R13 · SIMULACE, FYZICKÝ PŘELEZ ZATÍM NEPOTVRZEN</div>
<h2 id="r13Title">Emil s podepřením kloubů jako Kondo a přepočítaný přelez schodu 21 cm</h2>
<p class="r13-lead">Rozměry Emila, pohony i opěry bérců zůstaly. Změnil se pohyb: trup se při přelezu staví tak, aby ramena byla nad dlaněmi a váha přešla na opěru bérce dřív, než se zadní noha odlepí. Nejvyšší statické využití serva kleslo z {pct(sB.max(),1)} na <b>{pct(sN.max(),1)}</b> a rovnováha vychází ve všech {n} polohách i při tření 0,30.</p>
<div class="r13-kpis">{kp}</div>
<div class="r13-chartwrap"><div class="r13-legend"><span><i style="background:{C12}"></i>R12 · původní přelez ({cz(nb/HZ,0)} s)</span><span><i style="background:{C13}"></i>R13 · nový přelez ({cz(n/HZ,0)} s)</span><span style="color:#5d6f67">Využití nejzatíženějšího serva, 100 % = pracovní moment. Čísla nahoře jsou fáze R13.</span></div>{svg}<div id="r13Tip"></div></div>
<div class="r13-actions"><button type="button" class="mainbtn" id="r13Play">Přehrát nový přelez v modelu</button><button type="button" id="r13Peak">Skočit na nejtěžší polohu</button><button type="button" id="r13Lift">Skočit na odlepení zadní nohy</button></div>
<div class="r13-note">{'Dynamická simulace: nový přelez doběhl do stoje na schodu. ' if simok else 'Dynamická simulace s povely v otevřené smyčce nový přelez nedokončila. '}Statické výsledky platí pro pomalý pohyb a nejvýhodnější rozdělení sil mezi opory. Podrobnosti a slabá místa jsou níž v oddílu Zkoušky.</div>
<details open><summary>Co se v pohybu změnilo</summary>
<ul>
<li><b>Ramena nad dlaněmi.</b> Místa dlaní ve střední části zůstala, mění se poloha a natočení trupu. Vodorovná vzdálenost ramene od zatížené dlaně (vážená silou) klesla z {cz(offB[0],0)} mm na <b>{cz(offN[0],0)} mm</b>.</li>
<li><b>Váha na opěře bérce dřív.</b> V okamžiku odlepení pravé špičky nese levá holeň {cz(leadN[1],0)} N (R12: {cz(leadB[1],0)} N) a alespoň 10 N na ní leží už {cz(leadN[0],1)} s předem (R12: {cz(leadB[0],1)} s). Špička se odlepuje z dřívější polohy odvalu, ve které je odlehčení levnější.</li>
<li><b>Menší závislost na tření.</b> I kdyby opory tlačily jen svisle (tření 0,02), zůstane využití serv pod pracovním momentem: {pct(TN['mu02']['peak'],1)}. Původní přelez by v téže situaci potřeboval {pct(TB['mu02']['peak'],0)}.</li>
<li><b>Bezpečnější místa dlaní.</b> První opora levé dlaně je 40 mm za hranou místo 10 mm. V kleku jsou dlaně 234 mm za hranou místo 264 mm, tedy 46 mm od zadní hrany nášlapu místo 16 mm.</li>
<li><b>Nový závěr.</b> Před vzpřímením Emil přenese dlaně těsně před špičky (160 mm za hranu), dřepne si nad paty a teprve pak ruce zvedne. Odlehčení dlaní tak stojí {pct(sN[phN>=14].max())} místo {pct(sB[phB>=13].max())}.</li>
<li><b>Větší odstupy.</b> Chodidlo se při přešlapu zvedá o 12 mm místo 5 mm. Rám bérce a ostatní díly drží od hrany schodu nejméně {cz(TN["env"]["min"],1)} mm místo 0,25 mm.</li>
</ul>
<p>Přelez je delší ({cz(n/HZ,0)} s místo {cz(nb/HZ,0)} s), protože před každým odlehčením opory trup nejdřív přejde do polohy, ve které zbylé opory váhu unesou.</p></details>
<details><summary>Zatížení po fázích</summary><div class="r13-scroll"><table><thead><tr><th>Fáze R13</th><th>R12</th><th>R13</th><th>Nejzatíženější kloub v R13</th><th>Trvání</th></tr></thead><tbody>{''.join(pr)}</tbody></table></div></details>
<details><summary>Zatížení po kloubech a volba serv</summary>
<p>Špičky statického momentu při přelezu a největší moment z ostatních pohybů uložených v modelu (chůze, otočení, sed a vstávání, zvedání hrnku, ponožky a krabičky, schody s opěrami). Slabší servo dává smysl jen tam, kde by i nejtěžší pohyb zůstal pod 60 % jeho pracovního momentu.</p>
<div class="r13-scroll"><table><thead><tr><th>Kloub</th><th>Pohon dnes</th><th>Přelez R12</th><th>Přelez R13</th><th>Ostatní pohyby</th><th>Závěr</th></tr></thead><tbody>{''.join(jr)}</tbody></table></div>
<p>Pravé rameno předozadně, které v R12 vyšlo na {cz(rB[18],2)} N·m, teď potřebuje {cz(rN[18],2)} N·m. Mezi XL330 (0,10 N·m) a STS3215 (0,98 N·m) model žádné chytré servo nemá, takže u paží a kyčelního otáčení není kam sestoupit; nový pohyb tam dává rezervu, ne lehčí pohon. U os se STS3250 rozhoduje sloupec Závěr.</p></details>
<details><summary>Podepření kloubů podle Konda · co platí pro vidlice</summary>
<p>Kondo drží pohyblivý díl z obou stran: na jedné straně unašeč serva, na protější volný náboj ve stejné ose. Změřil jsem rámy R12 přímo ze sítí modelu: osm z devíti nosných os na každé straně už takové oboustranné uložení má a devátou, boční náklon kyčle, drží dvojice serv proti sobě. Bočnice vidlic jsou 6,6 a 8,5 mm silné, rozteč jejich středů je 44,8 mm a můstek leží 21–25 mm od osy, tedy těsně za obrysem serva. Vidlice jsou už krátké a zkrátit je bez změny rozměrů Emila nejde.</p>
<div class="r13-scroll"><table><thead><tr><th>Osa (obě strany)</th><th>Bočnice vidlice v R12</th><th>Ohyb mimo osu, který nese uložení<br><small>R12 → R13</small></th><th>Síla podél osy<br><small>R12 → R13</small></th><th>Síla na jednu bočnici z ohybu</th><th>Rozevření bočnice<br><small>odhad, PETG 2 GPa</small></th></tr></thead><tbody>{''.join(fr)}</tbody></table></div>
<p><b>Předpis pro tisk R13.</b> Tvar rámů v 3D modelu zůstává z R12; následující body jsou zadání pro CAD, nové díly k tisku jsem nevytvářel.</p>
<ul><li>Obě bočnice jedné vidlice tisknout v jednom kusu a otvory pro unašeč i protější čep vystružit na jedno upnutí. Nesouosost do 0,1 mm, jinak kloub drhne a servo ztrácí moment.</li>
<li>Protější čep uložit v ložisku 6 × 10 × 3 mm (C001) nebo ve volném náboji; axiální vůli vymezit podložkou na 0,1–0,2 mm.</li>
<li>Do koutů mezi bočnicí a můstkem přidat výztuhu 45° o délce nejméně 6 mm, vlákna vrstvit podél bočnice.</li>
<li>Bočnice neztenčovat pod 6,5 mm. Odhad rozevření při zatížení z přelezu vychází v setinách milimetru, tedy pod vůlí čepu 0,25 mm.</li></ul>
<p>Lepší uložení samo moment serva nesnižuje. Úsporu přinesla změna polohy těla.</p></details>
<details open><summary>Zkoušky</summary>
<div class="r13-scroll"><table><thead><tr><th>Zkouška</th><th>R12 stejným výpočtem</th><th>R13</th><th>Výsledek</th></tr></thead><tbody>{trs}</tbody></table></div>
<h3>Dynamická simulace (MuJoCo, polohová serva s omezeným momentem)</h3>{simnote}
<div class="r13-scroll"><table><thead><tr><th>Varianta</th><th>R12</th><th>R13</th></tr></thead><tbody>{simrows}</tbody></table></div>
<h3>Co ověřené není</h3>
<ul><li>Fyzický přelez. Všechno výše je výpočet nad modelem o hmotnosti 3,03 kg.</li>
<li>Skutečné rozdělení sil mezi opory. Statika počítá s nejvýhodnějším; robot s tuhými polohovými servy ho bez čidel síly v dlaních a korekce povelů nedodrží.</li>
<li>Schodiště. Scéna je jeden stupeň hluboký 28 cm s volným prostorem za ním. {('Další stupeň hned za ním by překážel: části robota při předklonu zasahují až '+cz(TN['next_riser_mm'],0)+' mm za zadní hranu nášlapu ve výšce pod 42 cm.') if TN.get('next_riser_mm',0)>1 else 'Do prostoru dalšího stupně robot při přelezu nezasahuje, hloubka nášlapu 28 cm ale zůstává podmínkou.'}</li>
<li>Plynulost povelů. Ve {nzz} místech se úhel kloubu mezi sousedními snímky vrací o víc než 1,2° a nejvyšší rychlost kloubu je {cz(TN['speedmax']['v'],0)} °/s (R12: {cz(TB['speedmax']['v'],0)} °/s). Před nahráním do serv je potřeba průběh vyhladit.</li>
<li>Odstupy pod cílem: mezi nesousedními díly {cz(TN['self']['min'],1)} mm místo 10 mm a od schodu {cz(TN['env']['min'],1)} mm místo 5 mm; v dynamické simulaci s odchylkou pánve do 15 mm se díl mimo opěry schodu dotkl.</li>
<li>Tisknutelné díly vidlic a jejich únava.</li></ul></details>
<script type="application/json" id="r13Data">{data}</script>
</section>'''
    return htmlr
