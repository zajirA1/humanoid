import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
import json, re, html as H, fork, export as EX, clear_export as CE
SRC='/mnt/user-data/uploads/fcda309b-Emil-Kondo.html'
def cz(x,d=1): return (f'{x:.{d}f}').replace('.',',')
def pct(x,d=0): return cz(100*x,d)+' %'
def set_block(s,bid,obj):
    m=re.search(r'<script[^>]*id="'+re.escape(bid)+r'"[^>]*>',s); assert m,bid
    e=s.index('</script>',m.end()); body=json.dumps(obj,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')
    return s[:m.end()]+body+s[e:]
def get_block(s,bid):
    m=re.search(r'<script[^>]*id="'+re.escape(bid)+r'"[^>]*>',s); e=s.index('</script>',m.end()); return json.loads(s[m.end():e])
def rep(s,old,new,count=1):
    assert s.count(old)>=1,old[:60]; return s.replace(old,new) if count==0 else s.replace(old,new,count)

def main(final,tnew,tbase,out):
    recs=pickle.load(open(final,'rb')); TN=pickle.load(open(tnew,'rb')); TB=pickle.load(open(tbase,'rb'))
    rows=TN['rows']; brecs=baseline_records(); brows=TB['rows']; n=len(recs); nb=len(brecs)
    scen=json.load(open('scen.json')); G=fork.geometry()
    sN=np.array([r['s50'] for r in rows]); sB=np.array([r['s50'] for r in brows])
    tauN=np.array([r['r']['tau'] for r in rows]); tauB=np.array([r['r']['tau'] for r in brows])
    simrec=TN['sim']['nominal']['rec'] if 'sim' in TN else None
    sim=None
    if simrec is not None:
        ok=simrec['t']>=-1e-9; ratio=(simrec['taupk']/simrec['lim']); ratio[:,[11,21]]=0
        sim=dict(ratio=ratio[ok].max(axis=1)[:n],tau=simrec['taupk'][ok][:n])
    climb,loads=EX.export(recs,rows,sim=sim)
    s=open(SRC,encoding='utf-8').read()
    # ---------- data blocks ----------
    s=set_block(s,'r9ClimbData',climb)
    L=get_block(s,'r9LoadsData'); L['climb']=loads; L['massKg']=float(MTOT)
    L['climbSummary']=f'R13 · {n} / {n} poloh s rovnováhou · maximum {pct(sN.max(),1)} při součiniteli tření 0,50.'
    s=set_block(s,'r9LoadsData',L)
    selfc=CE.self_case(recs,rows); scene=CE.scene_case(recs)
    C=get_block(s,'r12ClearanceData')
    old=[c for c in C['cases'] if c['name']=='climb'][0]
    C['cases']=[selfc if c['name']=='climb' else c for c in C['cases']]
    for c in C['adjacent']['cases']:
        if c.get('frames')==911 and abs((c.get('minMm') or 0)-2.041)<1e-3:
            c['frames']=n; c['minMm']=round(TN['adjmin'],4); c['minLowerMm']=round(TN['adjmin']-0.005,4)
            for k in ('nearest','worst'):
                if k in c: c[k]['frame']=int(np.argmin(np.abs(np.array([r['state'].q[8] for r in recs])-brecs[508]['state'].q[8])))
            for p in c.get('pairs',[]): p['frame']=c['worst']['frame']
    tot=sum(c['frames'] for c in C['cases']); near=sum(c.get('nearFrames',0) for c in C['cases']); hit=sum(c.get('hitFrames',0) for c in C['cases'])
    C['summaryCs']=(f'R13 nahrazuje přelez schodu 21 cm novou sekvencí; ostatní pohyby zůstávají z R12. V {len(C["cases"])} pohybech jsme prověřili {tot:,} poloh.'.replace(',',' ')+
                    f' Mezi nesousedními články a kryty klesla mezera pod 10 mm v {near} polohách, z toho {selfc["nearFrames"]} při přelezu (minimum {cz(selfc["minMm"],1)} mm; R12 mělo {cz(old["minMm"],1)} mm). Dotyk se objevil v {hit} polohách. '
                    'U sousedních rámů v kloubech vychází minimum 2,02 mm. Hodnoty u překážek jsou v oddílu Okolí a předměty.')
    s=set_block(s,'r12ClearanceData',C)
    S=get_block(s,'r12SceneData'); S['cases']['climb']=scene; s=set_block(s,'r12SceneData',S)
    Gd=get_block(s,'r9GeometryData'); Gd['climb']['frames']=n
    Gd['climb']['minima']['environment']=dict(mm=round(TN['env']['min'],3),cover=CE.inst(TN['envkey'][0],rows[TN['env']['frame']]['envpt'],recs[TN['env']['frame']]['state'])[0],obstacle='step210',frame=TN['env']['frame'])
    s=set_block(s,'r9GeometryData',Gd)
    # ---------- script / text patches ----------
    s=rep(s,'<title>Emil H22 R12 a Kondo KHR-3HV · 3D modely</title>','<title>Emil H22 R13 · podepření podle Konda a nový přelez 21 cm</title>')
    s=rep(s,'<option value="r9" selected>R12 · pracovní sestava</option>','<option value="r9" selected>R13 · pracovní sestava (nový přelez 21 cm)</option>')
    s=rep(s,'<option value="r9">Emil H22 R12</option>','<option value="r9">Emil H22 R13</option>')
    s=rep(s,'<div class="brand">EMIL H22 / R12</div>','<div class="brand">EMIL H22 / R13 · NEJLEPŠÍ Z OBOU</div>')
    a=s.index('"R12 · Simulace ukazuje přenos přes kolenní oporu.'); b=s.index('"',a+1)
    envp=CE.inst(TN['envkey'][0],rows[TN['env']['frame']]['envpt'],recs[TN['env']['frame']]['state'])[0]
    s=s[:a]+json.dumps(f'R13 · Rovnováha vyšla ve všech {n} polohách, nejvyšší statické využití pohonu je {pct(sN.max(),1)} (R12: {pct(sB.max(),1)}). Díly, které se schodu dotýkat nemají, od něj drží nejméně {cz(TN["env"]["min"],1)} mm (R12: 0,25 mm). Jde o simulaci, fyzický přelez potvrzený není.',ensure_ascii=False)+s[b+1:]
    s=rep(s,'Moment a rozložení sil vycházejí z referenčního výpočtu R11. Poloha a geometrie odpovídají R12.','R13 · statický moment při nejvýhodnějším rozdělení sil mezi opory (tření 0,50, hmotnost 3,03 kg s návleky). Skutečné rozdělení určí tuhost serv a dosednutí opor.')
    s=rep(s,'Referenční dynamika R11 · bodové hmoty','Dynamická simulace R13 · špička momentu serva')
    s=rep(s,"switchView(location.hash==='#emil'?false:initialKondo)","switchView(location.hash==='#kondo')")
    JS=r"""(function(){const D=JSON.parse($('r13Data').textContent),svg=$('r13Chart'),tip=$('r13Tip'),cross=$('r13Cross'),hit=$('r13Hit'),wrap=svg.parentElement;
 const pc=v=>(100*v).toFixed(0)+' %';
 function at(e){const r=svg.getBoundingClientRect(),vx=(e.clientX-r.left)/r.width*D.geo.W,t=Math.max(0,Math.min(D.geo.tmax,(vx-D.geo.ml)/(D.geo.W-D.geo.ml-D.geo.mr)*D.geo.tmax));return {t,vx}}
 hit.addEventListener('pointermove',e=>{const {t,vx}=at(e),i=Math.round(t*D.hz),w=wrap.getBoundingClientRect();cross.setAttribute('x1',vx);cross.setAttribute('x2',vx);cross.setAttribute('visibility','visible');
  const rows=[t.toFixed(0)+' s'];if(i<D.n.length)rows.push('R13 · '+pc(D.n[i])+' · '+D.jn[i]+' · fáze '+(D.ph[i]+1)+' '+D.names[D.ph[i]]);if(i<D.b.length)rows.push('R12 · '+pc(D.b[i])+' · '+D.jb[i]);
  tip.replaceChildren(...rows.map(x=>{const d=document.createElement('div');d.textContent=x;return d}));tip.style.left=Math.max(120,Math.min(w.width-120,e.clientX-w.left))+'px';tip.style.top=(e.clientY-w.top)+'px';tip.style.visibility='visible'});
 hit.addEventListener('pointerleave',()=>{tip.style.visibility='hidden';cross.setAttribute('visibility','hidden')});
 function go(i,play){if(document.body.classList.contains('kondo-active'))return;if(mode!=='climb'){for(const b of document.querySelectorAll('button[data-mode]'))if(b.dataset.mode==='climb'){b.click();break}}stop();idx=Math.max(0,Math.min(i,climbData.poses.length-1));render();$('stage').scrollIntoView({behavior:'smooth',block:'center'});if(play)$('play').click()}
 hit.addEventListener('click',e=>{const i=Math.round(at(e).t*D.hz);if(i<D.n.length)go(i)});hit.style.cursor='pointer';
 $('r13Play').onclick=()=>go(0,true);$('r13Peak').onclick=()=>go(D.peak);$('r13Lift').onclick=()=>go(D.lift);
})();"""
    s=rep(s,"choose('pickup');document.documentElement.dataset.ready='true';","choose('climb');"+JS+"document.documentElement.dataset.ready='true';")
    s=rep(s,"'Emil-H22-R12-a-Kondo-KHR-3HV.html'","'Emil-H22-R13-prelez-21cm.html'")
    s=rep(s,'Odhad hmotnosti s oběma návleky činí 3,033 kg','Odhad hmotnosti s oběma návleky činí 3,03 kg')
    # palm-confirmation gate: three frames just before the left foot is unloaded
    lN=[l['leftN'] for l in loads['loads']]; rN_=[l['rightN'] for l in loads['loads']]
    g=next(i for i in range(len(lN)-3) if all(lN[k]>=1.0 and rN_[k]>=1.0 for k in (i,i+1,i+2)))
    gate=[g,g+1,g+2]; print('palm gate frames',gate)

    s=rep(s,'[53,54,55].every','['+','.join(map(str,gate))+'].every'); s=rep(s,'idx>=55','idx>='+str(gate[-1]),0); s=rep(s,'limit:fault?55:null','limit:fault?'+str(gate[-1])+':null')
    s=rep(s,'if(sg.fault&&idx>=%d){idx=55;'%gate[-1],'if(sg.fault&&idx>=%d){idx=%d;'%(gate[-1],gate[-1])) if ('if(sg.fault&&idx>=%d){idx=55;'%gate[-1]) in s else s
    report=build_report(recs,rows,brecs,brows,TN,TB,scen,G,sN,sB,tauN,tauB,selfc,old)
    i0=s.index('<main><header>'); i1=s.index('</header>',i0)+len('</header>'); s=s[:i1]+report+s[i1:]
    open(out,'w',encoding='utf-8').write(s); print('written',out,len(s))

from report import build_report
if __name__=='__main__': main(*sys.argv[1:5])
