"""Opravy a vylepšení z auditu stránek (22. 11. 2026) – nanáší je build_r14.py na stránku před vložením panelu.
Každá úprava hlídá, že její vzor ve stránce existuje právě jednou (jinak sestavení skončí chybou)."""

STYL = '''<style id="audit2211">
/* panel Úprava kloubů: neviditelný obal nesmí brát kliknutí ani dědit okraj z obecného stylu aside */
#r14{border:0!important;padding:0!important;margin:0!important;pointer-events:none}#r14>*{pointer-events:auto}
#r14Toggle{background:#9c5530!important}
/* načítání */
#khLoad{position:fixed;left:0;right:0;top:0;z-index:99;background:#193733;color:#fff;font:14px/1.3 system-ui,-apple-system,"Segoe UI",sans-serif;padding:11px 16px;text-align:center}
#khLoad i{display:block;height:3px;margin:8px auto 0;max-width:320px;background:linear-gradient(90deg,transparent,#e9b36f,transparent);background-size:40% 100%;background-repeat:no-repeat;animation:khL 1.1s linear infinite}
@keyframes khL{from{background-position:-40% 0}to{background-position:140% 0}}html[data-ready="true"] #khLoad{display:none}
/* zpráva revize sbalená pod čísly, model je blíž nahoře */
.rev-more>summary{cursor:pointer;font-weight:600;font-size:15px;padding:8px 0;color:#1e5a4d}.rev-more[open]>summary{margin-bottom:6px}
@media (max-width:700px){
 #r15 .r13-kpis,.rev-sec .r13-kpis{grid-template-columns:1fr 1fr!important;gap:8px}
 #r15 .r13-kpi b,.rev-sec .r13-kpi b{font-size:26px}
 #r15 .r13-chartwrap,.rev-sec .r13-chartwrap{overflow-x:auto}
 #r15Chart,#r15Chart3,.rev-sec svg[id$="Chart"]{min-width:760px}
 #r14Toggle{padding:8px 13px!important;font-size:12.5px!important}
 body{padding-bottom:64px}
 #r14{left:0!important;right:0!important;bottom:0!important;width:100%!important}
 #r14Body{width:100%!important;max-width:100%!important;border-radius:14px 14px 0 0!important;max-height:72vh!important;margin:0!important}
 #r14Toggle{margin:0 10px 10px auto}
}
</style>'''


KONDO = None


def uprav(s, rep):
    s = rep('</head>', '<link rel="icon" href="data:,">' + STYL + '</head>')
    s = rep('<body>', '<body><div id="khLoad" role="status">Načítám simulátor Emil H22 (12 MB)…<i></i></div>')
    # zastaralý údaj „Kryt u schodu · reference R11“ → odstup od schodu aktuální revize (z panelu Úprava kloubů)
    s = rep("const closest=r9IsActive()?r11CoverCheck:displayedClearance().climb.minima.environment;",
            "const closest=r9IsActive()?(window.r14EnvMin||r11CoverCheck):displayedClearance().climb.minima.environment;")
    s = rep("(r9IsActive()?'Kryt u schodu · reference R11 ':'Nejmenší vůle krytu u schodu ')",
            "(r9IsActive()?(window.r14EnvMin?'Odstup od schodu · '+window.r14Rev+' ':'Kryt u schodu · reference R11 '):'Nejmenší vůle krytu u schodu ')")
    s = rep("idx = r9IsActive()&&r11CoverCheck ? r11CoverCheck.frame : displayedClearance().climb.minima.environment.frame;",
            "idx = r9IsActive()&&(window.r14EnvMin||r11CoverCheck) ? (window.r14EnvMin||r11CoverCheck).frame : displayedClearance().climb.minima.environment.frame;")
    # stažené HTML bez klíče relace a adresy API
    s = rep("URL.createObjectURL(new Blob([originalHTML],{type:'text/html;charset=utf-8'}))",
            "URL.createObjectURL(new Blob([originalHTML.replace(/<meta name=\"robot-(csrf|api)\"[^>]*>/g,'').replace(/<div id=\"khLoad\"[^]*?<\\/div>/,'')],{type:'text/html;charset=utf-8'}))")
    # hlavní model: přiblížení dvěma prsty (dotyk), jinak beze změny
    s = rep("let drag=null;const can=$('canvas');can.onpointerdown=e=>{can.setPointerCapture(e.pointerId);drag=[e.clientX,e.clientY]};"
            "can.onpointermove=e=>{if(!drag)return;az-=(e.clientX-drag[0])*.009;el=cl(el+(e.clientY-drag[1])*.007,-1.1,1.4);drag=[e.clientX,e.clientY];$('axis').textContent='Vlastní pohled';render()};"
            "can.onpointerup=can.onpointercancel=()=>drag=null;",
            "let drag=null;const can=$('canvas'),khPtr=new Map();let khPinch=0;"
            "can.onpointerdown=e=>{try{can.setPointerCapture(e.pointerId)}catch{}khPtr.set(e.pointerId,[e.clientX,e.clientY]);if(khPtr.size===2){const [a,b]=[...khPtr.values()];khPinch=Math.hypot(a[0]-b[0],a[1]-b[1]);drag=null}else drag=[e.clientX,e.clientY]};"
            "can.onpointermove=e=>{if(khPtr.has(e.pointerId))khPtr.set(e.pointerId,[e.clientX,e.clientY]);if(khPtr.size>=2){const [a,b]=[...khPtr.values()],d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(khPinch>0&&d>0){zoom=cl(zoom*d/khPinch,.55,4);khPinch=d;render()}return}"
            "if(!drag)return;az-=(e.clientX-drag[0])*.009;el=cl(el+(e.clientY-drag[1])*.007,-1.1,1.4);drag=[e.clientX,e.clientY];$('axis').textContent='Vlastní pohled';render()};"
            "can.onpointerup=can.onpointercancel=e=>{khPtr.delete(e.pointerId);if(khPtr.size<2)khPinch=0;drag=khPtr.size===1?[...khPtr.values()][0]:null};")
    s = rep('Kliknutím na servo zobrazíš jeho hodnoty. Tažením otočíš pohled a kolečkem ho přiblížíš.',
            'Kliknutím na servo zobrazíš jeho hodnoty. Tažením otočíš pohled, kolečkem myši nebo dvěma prsty ho přiblížíš.')
    # výška schodu: schod v modelu a volba v postranním panelu přelezu
    s = rep("function climbEnvironment(boxes) {\n  const {width, depth} = climbData;\n  const step = 210;",
            "function climbEnvironment(boxes) {\n  const {width, depth} = climbData;\n  const step = 210 + (r9IsActive() ? (window.r14Dh || 0) : 0);")
    s = rep('<label id="phaseLabel" class="section-label" for="phaseJump">Fáze výstupu</label>',
            '<div id="r14HeightBox" hidden><label class="section-label" for="r14Height">Výška schodu v modelu</label><select id="r14Height">'
            + ''.join(f'<option value="{h}"{" selected" if h == 210 else ""}>{h} mm{" · plán" if h == 210 else ""}</option>' for h in (200, 202, 205, 208, 210, 212, 215, 218, 220, 222, 225))
            + '</select><p id="r14HeightNote" class="phase-note" hidden></p></div><label id="phaseLabel" class="section-label" for="phaseJump">Fáze výstupu</label>')
    # karta Mezery mezi díly: od R15 nemíchat údaje R13 o hraně schodu a rozlišit cíl 10 mm a mez kontroly 9 mm
    nova = "(window.khNovaRevize??(window.khNovaRevize=(()=>{try{return (JSON.parse(document.getElementById('r14Data').textContent).revize||'R13')!=='R13'}catch{return false}})()))"
    s = rep("state.textContent=({hit:'Dotyk mezi díly',near:'Jmenovitá mezera pod cílem',pass:'Nesousední články a kryty splňují cíl',unknown:'Bez výsledku'})[level];",
            "state.textContent=({hit:'Dotyk mezi díly',near:(valid&&min>=9?'Pod cílem 10 mm · mez kontroly 9 mm splněna':'Jmenovitá mezera pod cílem'),pass:'Nesousední články a kryty splňují cíl',unknown:'Bez výsledku'})[level];if(level==='near'&&valid&&min>=9)state.dataset.result='pass';")
    s = rep("climbWarning.hidden=context?.name!=='climb' || !climbFrame;", "climbWarning.hidden=context?.name!=='climb' || !climbFrame || " + nova + ";")
    s = rep("if(climbCase && climbFrame){byId('r12ClimbEntry').hidden=false;", "if(climbCase && climbFrame && !" + nova + "){byId('r12ClimbEntry').hidden=false;")
    # export 3MF: název podle revize a dokreslené úchyty jako díly
    s = rep("a.download=r8IsPaired()?(r9IsActive()?'Emil-H22-R12':'Emil-H22-R8-dvojite-kycle')",
            "a.download=r8IsPaired()?(r9IsActive()?'Emil-H22-'+(window.r14Rev||'R12')+(window.r14CadItems&&window.r14CadItems().length?'-s-uchyty':''):'Emil-H22-R8-dvojite-kycle')")
    s = rep("if(typeof r11ExtraCadItems==='function'){",
            "if(r9IsActive()&&window.r14CadItems){const U=window.r14CadItems();if(U.length){meshes.r14_uchyt=window.r14CadBox;for(const item of U)nodes.push('<component objectid=\"'+mesh('r14_uchyt')+'\" transform=\"'+item.t.map(v=>+v.toFixed(5)).join(' ')+'\"/>')}}if(typeof r11ExtraCadItems==='function'){")
    # export 3MF: posunutá serva i visící díly (E) jako v modelu, ne původní polohy R12
    s = rep('for(let [n,tm,ow,link,flip] of cadItems)nodes.push(\'<component objectid="\'+mesh(n,flip)+\'" transform="\'+tm.join(\' \')+\'"/>\');',
            'const r14T=r9IsActive()&&window.r14CadPrep?window.r14CadPrep():null;cadItems.forEach(([n,tm,ow,link,flip],k)=>{const t=r14T?r14T(k,tm,ow,link).map(v=>+(+v).toFixed(6)):tm;nodes.push(\'<component objectid="\'+mesh(r14T&&r14T.mesh?r14T.mesh(k,n):n,flip)+\'" transform="\'+t.join(\' \')+\'"/>\')});')
    # prohlížeč Kondo: data až při otevření (index.php?data=kondo); stažené HTML je dostane vložená
    i = s.index('<script id="kModelData" type="application/json">') + len('<script id="kModelData" type="application/json">'); j = s.index('</script>', i)
    global KONDO
    KONDO = s[i:j]; s = rep('<script id="kModelData" type="application/json">' + KONDO + '</script>', '<script id="kModelData" type="application/json"></script>')
    s = rep("document.addEventListener('DOMContentLoaded',function(){try{const model=JSON.parse(document.getElementById('kModelData').textContent);",
            "window.khKondoAdd=(t,f)=>{window.khKondoInit=f};window.khKondoAdd('DOMContentLoaded',function(){try{const model=JSON.parse(document.getElementById('kModelData').textContent);")
    s = rep('<script id="kViewerScript">', '''<script>(function(){let stav='ne',predchozi=null;
 function nacti(){const el=document.getElementById('kModelData');if(el.textContent.trim())return Promise.resolve();
  return fetch('index.php?data=kondo',{credentials:'same-origin'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.text()}).then(t=>{el.textContent=t;window.khKondoText=t})}
 window.khKondoNacti=nacti;
 document.addEventListener('DOMContentLoaded',()=>{const a=document.getElementById('r8Assembly');if(!a)return;predchozi=a.value;
  a.addEventListener('change',e=>{if(stav==='hotovo'){return}if(a.value!=='kondo'){predchozi=a.value;return}e.stopImmediatePropagation();a.value=predchozi;if(stav==='nacitam')return;stav='nacitam';
   const st=document.getElementById('status');const old=st&&st.textContent;if(st)st.textContent='Načítám prohlížeč Kondo…';
   nacti().then(()=>{window.khKondoInit();stav='hotovo';a.value='kondo';a.dispatchEvent(new Event('change',{bubbles:true}))}).catch(err=>{stav='ne';if(st)st.textContent='Prohlížeč Kondo se nepodařilo načíst ('+err.message+').'})},{capture:true})})})();</script><script id="kViewerScript">''')
    s = rep("$('save').onclick=()=>{let link=document.createElement('a'),url=URL.createObjectURL(new Blob([originalHTML.replace(",
            "$('save').onclick=async()=>{let kd='';try{if(window.khKondoNacti){await window.khKondoNacti();kd=window.khKondoText||document.getElementById('kModelData').textContent}}catch{}let link=document.createElement('a'),url=URL.createObjectURL(new Blob([originalHTML.replace('<script id=\"kModelData\" type=\"application/json\"><\\/script>','<script id=\"kModelData\" type=\"application/json\">'+kd.replace(/<\\//g,'<\\\\/')+'<\\/script>').replace(")
    return s
