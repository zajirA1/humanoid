import sys,re,json
src,out=sys.argv[1],sys.argv[2]; hook=len(sys.argv)>3
s=open(src,encoding='utf8').read()
def rep(a,b,cnt=1):
    global s
    assert s.count(a)==cnt,(a[:60],s.count(a)); s=s.replace(a,b)
import os
HERE=os.path.dirname(os.path.abspath(__file__))
eng=open(os.path.join(HERE,'r14engine.js')).read().replace("if(typeof module!=='undefined')module.exports=r14Engine;","")
ui=open(os.path.join(HERE,'r14ui.js')).read()
data=open(os.path.join(HERE,'r14page.json')).read(); assert '</' not in data
rep("{axes,par}=data;let P=data.P;","{axes,par}=data;let P=data.P;var r14E=Array.from({length:22},()=>[0,0,0]),r14Ready=false;")
rep("for(let i=0;i<22;i++)w[i]=mat(w[par[i]],rot(axes[i],q[i],P[i]));return w}","for(let i=0;i<22;i++)w[i]=mat(w[par[i]],r14T(i,q[i]));return w}\nfunction r14T(i,a){const t=rot(axes[i],a,P[i]),e=r14E[i];if(e[0]||e[1]||e[2]){const r=dir(t,e);t[9]+=r[0];t[10]+=r[1];t[11]+=r[2]}return t}")
m=re.search(r"function render\(paintOnly\)\s*\{",s); assert m and len(re.findall(r"function render\(paintOnly\)\s*\{",s))==1
s=s[:m.end()]+"r14Before();"+s[m.end():]
rep("const project=rnd.paint(cmd,target,az,el,span/zoom);","const project=rnd.paint(cmd,target,az,el,span/zoom);r14After(project,w);")
rep("document.documentElement.dataset.ready='true';\n}catch(err)",eng+"\n"+ui+"\ndocument.documentElement.dataset.ready='true';\n}catch(err)")
m2=re.findall(r"function row\(\)\s*\{\s*if\(r10IsMotion\(\)\)return r10ReadPose\(\);",s); assert len(m2)==1
s=s.replace(m2[0],"function row() { if(r10IsMotion())return r14Fix(r10ReadPose());")
rep("const fmt=(v,n=1)=>v.toLocaleString(","const fmt=(v,n=1)=>(v??NaN).toLocaleString(")
if hook: rep("try{const data=JSON.parse($('data').textContent)","try{window.__ev=s=>eval(s);const data=JSON.parse($('data').textContent)")
css='''<style>#r14{position:fixed;right:12px;bottom:12px;z-index:60;width:min(356px,calc(100vw - 24px));font:13px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1f2a30;display:flex;flex-direction:column;align-items:flex-end}
body.kondo-active #r14{display:none}
#r14Toggle{background:#ad653a;color:#fff;border:0;border-radius:999px;padding:10px 16px;font:600 14px/1 inherit;cursor:pointer;box-shadow:0 3px 12px #0003}
#r14Toggle:focus-visible,#r14 button:focus-visible,#r14 input:focus-visible,#r14 select:focus-visible{outline:2px solid #1f2a30;outline-offset:2px}
#r14 .r14-body{display:none;order:-1;margin-bottom:8px;width:100%;box-sizing:border-box;max-height:calc(100vh - 86px);overflow:auto;background:#fffdf8;border:1px solid #d9d2c4;border-radius:12px;padding:12px 14px;box-shadow:0 6px 24px #0003}
#r14.open .r14-body{display:block}
#r14 h3{margin:0 0 6px;font-size:15px}#r14 label{display:block;margin:8px 0 2px;font-weight:600}#r14 label.r14-check{display:flex;gap:8px;align-items:flex-start;font-weight:400;margin:8px 0}
#r14 select,#r14 textarea{width:100%;box-sizing:border-box;font:inherit;padding:5px;border:1px solid #c9c1b2;border-radius:6px;background:#fff;color:inherit}
#r14 .r14-row{display:grid;grid-template-columns:1fr 64px;gap:8px;align-items:center}#r14 .r14-row input[type=number]{width:100%;box-sizing:border-box;font:inherit;padding:4px;border:1px solid #c9c1b2;border-radius:6px}
#r14 input[type=range]{width:100%;accent-color:#ad653a}#r14 .r14-hint{color:#5c6a70;font-size:12px;margin:2px 0 0}
#r14 .r14-btns{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}#r14 .r14-btns button{font:inherit;padding:6px 10px;border:1px solid #c9c1b2;border-radius:7px;background:#fff;color:inherit;cursor:pointer}#r14 .r14-btns button.primary{background:#1f2a30;color:#fff;border-color:#1f2a30;font-weight:600}
#r14Facts{margin:8px 0;border-top:1px solid #e6dfd2}#r14Facts div{display:flex;justify-content:space-between;gap:10px;padding:4px 0;border-bottom:1px solid #e6dfd2}#r14Facts span{color:#5c6a70}#r14Facts b{font-weight:600;text-align:right}
#r14State,#r14Progress{color:#5c6a70;margin:6px 0}#r14Progress:empty{display:none}
#r14 .r14-t{width:100%;border-collapse:collapse;margin:10px 0 4px;font-size:12px}#r14 .r14-t th,#r14 .r14-t td{text-align:left;padding:4px 4px;border-bottom:1px solid #e6dfd2;vertical-align:top;font-variant-numeric:tabular-nums}#r14 .r14-t thead th{color:#5c6a70;font-weight:600}#r14 .r14-t tbody th{font-weight:400}#r14 .r14-over td{color:#8a3a2a;font-weight:600}
#r14 .r14-verdict{background:#f3ece0;border-left:3px solid #ad653a;padding:7px 10px;border-radius:0 7px 7px 0;margin:10px 0 4px}#r14 .r14-bad{color:#8a3a2a}#r14 .r14-warn{color:#8a5a12}#r14 .r14-ok{color:#1f6b4f}#r14 .r14-stale{color:#8a3a2a}
#r14 .r14-link{font:inherit;background:none;border:0;padding:0;color:#1d5fae;text-decoration:underline;cursor:pointer}
#r14 .r14-legend{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0 2px;font-size:12px}#r14 .r14-legend i{display:inline-block;width:14px;height:3px;margin-right:5px;vertical-align:middle;border-radius:2px}#r14 .r14-legend i.r14-dash{background:repeating-linear-gradient(90deg,#8a3a2a 0 4px,transparent 4px 7px)}
#r14Chart{width:100%;height:auto;display:block;cursor:crosshair;touch-action:none}#r14Chart text{font-size:9px;fill:#5c6a70}#r14 .r14-tip{font-size:12px;color:#5c6a70;min-height:1.4em}#r14 .r14-note{font-size:12px;color:#5c6a70;margin:8px 0 0}
#r14Layer{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:6;overflow:visible}#r14Layer circle{pointer-events:auto;cursor:grab}
</style>'''
panel='''<aside id="r14" aria-label="Úprava kloubů"><button id="r14Toggle" aria-expanded="false" aria-controls="r14Body">Úprava kloubů</button><div class="r14-body" id="r14Body">
<h3>Úprava kloubů</h3><p id="r14State"></p>
<label for="r14Joint">Kloub</label><select id="r14Joint"></select>
<label class="r14-check"><input type="checkbox" id="r14Mirror" checked><span>Stejnou úpravu zrcadlit na druhou stranu těla</span></label>
<label for="r14R0">Do strany (+ k levému boku robota), mm</label><div class="r14-row"><input type="range" id="r14R0" min="-40" max="40" step="0.5"><input type="number" id="r14N0" min="-40" max="40" step="0.5" aria-label="Posun do strany v mm"></div>
<label for="r14R1">Dozadu (+) / dopředu (−), mm</label><div class="r14-row"><input type="range" id="r14R1" min="-40" max="40" step="0.5"><input type="number" id="r14N1" min="-40" max="40" step="0.5" aria-label="Posun dozadu v mm"></div>
<label for="r14R2">Nahoru (+) / dolů (−), mm</label><div class="r14-row"><input type="range" id="r14R2" min="-40" max="40" step="0.5"><input type="number" id="r14N2" min="-40" max="40" step="0.5" aria-label="Posun nahoru v mm"></div>
<label for="r14Rot">Natočení těla serva kolem jeho osy: <span id="r14RotOut">0°</span></label><input type="range" id="r14Rot" min="-180" max="180" step="5">
<p class="r14-hint">Natočení mění jen polohu pouzdra v modelu, do výpočtu sil nevstupuje.</p>
<label class="r14-check"><input type="checkbox" id="r14Carry"><span>Posunout i všechno, co na kloubu visí. Bez zaškrtnutí se hýbe jen osa se servem a díly pod kloubem zůstávají na místě.</span></label>
<div id="r14Facts"></div>
<div class="r14-btns"><button class="primary" id="r14RunBtn">Přepočítat</button><button id="r14ResetJoint">Vrátit kloub</button><button id="r14ResetAll">Vrátit vše</button></div>
<p id="r14Progress" role="status"></p><div id="r14Results"></div>
<h3 style="margin-top:14px">Plná kontrola v GitHubu</h3><p class="r14-hint">Pohyb jen přizpůsobí (neladí ho znovu), ale přepočítá přelez přesně: statika při třech třeních, přesné mezery ze sítí a dynamická simulace v šesti variantách. Trvá asi 10 minut, nic nenasazuje.</p>
<label class="r14-check"><input type="checkbox" id="r14Fast"><span>Rychlá kontrola (asi 3 minuty, méně přesná)</span></label>
<div class="r14-btns"><button class="primary" id="r14SendBtn">Odeslat k přepočtu</button></div><div id="r14Remote"></div>
<details><summary>Export a import nastavení</summary><div class="r14-btns"><button id="r14ExportBtn">Stáhnout JSON</button><button id="r14ImportBtn">Načíst z textu</button></div><textarea id="r14Json" rows="5" aria-label="Nastavení úprav jako JSON" spellcheck="false"></textarea></details>
<p class="r14-note">V modelu táhni za kolečko vybraného kloubu. Oranžově je nakreslená vidlice vybraného kloubu, modře vidlice ostatních upravených kloubů, čárkovaně posun osy.</p>
</div></aside>'''
rep('<section id="r13" aria-labelledby="r13Title">',css+panel+'<section id="r13" aria-labelledby="r13Title">')
i=s.find('<p class="r13-lead">'); j=s.find('</p>',i)+4
s=s[:j]+'<p class="r13-note"><b>Nově:</b> tlačítkem <b>Úprava kloubů</b> vpravo dole posuneš libovolné servo přímo v modelu, uvidíš překreslenou vidlici a necháš přepočítat přelez i chůzi.</p>'+s[j:]
k=s.find('<script type="application/json" id="r13Data">'); s=s[:k]+'<script type="application/json" id="r14Data">'+data+'</script>'+s[k:]
open(out,'w',encoding='utf8').write(s); print('ok',len(s))
