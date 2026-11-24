function render(){if(!width)return;const fs=active(),q=manual||sample(fs,currentTime),o=carried(fs,currentTime,q);
 camera();drawFloor(fs);drawMeshes(world(q,o.pos));}
function setMsg(t){$('notice').textContent=t;}
function stop(){playing=false;$('play').textContent='Přehrát';}
function moveTo(t,idx=-1){stop();manual=null;currentTime=clamp(t,0,active().at(-1)?.t_s||0);selected=idx;if(idx>=0&&editing){$('pname').value=active()[idx].label;$('event').value=active()[idx].event||'';}ui();render();}
function steps(){clearAudit();const fs=active();$('steps').replaceChildren(...fs.map((f,i)=>{const b=document.createElement('button');b.textContent=f.label;b.addEventListener('click',()=>moveTo(f.t_s,i));return b;}));}
function ui(){
 const fs=active(),q=manual||sample(fs,currentTime),tip=arm(q).tip,o=carried(fs,currentTime,q),outside=check(q,o.held),end=fs.at(-1)?.t_s||0;
 const at=fs.findIndex(f=>f.t_s>=currentTime-.00001),idx=at<0?fs.length-1:at;
 $('stageName').textContent=presets[seq]?.name||'Vlastní polohy';$('phase').textContent=manual?'Ruční nastavení':fs[idx]?.label||'Prázdný program';
 $('time').textContent=currentTime.toFixed(1)+' / '+end.toFixed(1)+' s';$('timebar').max=end||1;$('timebar').value=currentTime;
 $('coords').textContent=['X','Y ↑','Z'].map((k,i)=>k+' '+Math.round(tip[i])).join('  ·  ')+' mm';$('object').textContent='Předmět · '+o.state;
 names.forEach((k,i)=>{$('q'+i).value=q[i];$('v'+i).textContent=q[i].toFixed(1)+(i===3?' mm':'°');});
 const st=$('status');st.textContent=outside.length?'Možný průnik · '+outside.join(', '):o.issue||'Kontrolované obálky mají v této poloze volný průchod.';st.classList.toggle('warn',!!outside.length||!!o.issue);
 $('count').textContent='Vlastní program · '+own.length+' poloh';$('undo').disabled=!own.length;$('replace').disabled=seq!=='own'||selected<0;$('play').disabled=fs.length<2;
 $('save').disabled=!fs.length;$('timebar').disabled=fs.length<2;$('demoTab').setAttribute('aria-selected',String(!editing));$('teachTab').setAttribute('aria-selected',String(editing));$('teachBox').hidden=!editing;
 $('hint').textContent=editing?'Nastav klouby a ulož polohu. Čas přesunu platí od předchozí polohy.':'Úhly ukazují právě přehrávanou polohu. Pro změnu použij Učení poloh.';
 [...$('steps').children].forEach((b,i)=>b.classList.toggle('current',i===(selected>=0?selected:idx)));
}
function persist(){try{localStorage.setItem('emil-eta-waveshare-v2',JSON.stringify(own));}catch{}}
function validate(fs){
 if(!Array.isArray(fs)||!fs.length||fs.length>150)throw Error('Program musí obsahovat 1 až 150 poloh.');
 return fs.map((f,i)=>{if(typeof f!=='object'||!f||!Number.isFinite(f.t_s)||(i===0?f.t_s!==0:f.t_s-fs[i-1].t_s<.19999)||f.t_s>1800)throw Error('Neplatné časy poloh.');
 for(let j=0;j<4;j++){const v=f[names[j]];if(!Number.isFinite(v)||v<lim[j][0]||v>lim[j][1])throw Error('Poloha překračuje rozsah kloubu.');}
 if(![null,undefined,'grasp','release'].includes(f.event))throw Error('Neznámá událost.');
 return {t_s:f.t_s,label:String(f.label||('Poloha '+(i+1))).slice(0,55),...Object.fromEntries(names.map(k=>[k,f[k]])),event:f.event||null};});
}
function mode(b){stop();editing=b;if(!b)manual=null;names.forEach((k,i)=>$('q'+i).disabled=!b);ui();render();}
function pickSeq(k){seq=k;$('seq').value=k;steps();moveTo(0);}
names.forEach((k,i)=>{const div=document.createElement('div');div.className='slider';div.innerHTML='<div class="line"><label for="q'+i+'">'+labels[i]+'</label><output id="v'+i+'"></output></div><input type="range" step=".1" id="q'+i+'" min="'+lim[i][0]+'" max="'+lim[i][1]+'">';$('sliders').append(div);$('q'+i).addEventListener('input',()=>{stop();manual=manual||sample(active(),currentTime);manual[i]=+$('q'+i).value;ui();render();});});
$('demoTab').onclick=()=>mode(false);$('teachTab').onclick=()=>mode(true);
$('record').onclick=()=>{if(own.length>=150)return setMsg('Limit je 150 poloh.');const q=manual||sample(active(),currentTime),dt=+$('dt').value;if(!Number.isFinite(dt)||dt<.2||dt>45)return setMsg('Zadej čas přesunu 0,2 až 45 s.');
 const t=own.length?+(own.at(-1).t_s+dt).toFixed(3):0;if(t>1800)return setMsg('Limit programu je 1800 s.');const f={t_s:t,label:$('pname').value.trim()||'Poloha '+(own.length+1),...Object.fromEntries(names.map((k,i)=>[k,q[i]])),event:$('event').value||null};
 own.push(f);persist();seq='own';$('seq').value=seq;steps();moveTo(t,own.length-1);$('pname').value='';$('event').value='';setMsg('Poloha uložena do vlastního programu.');};
$('replace').onclick=()=>{if(seq!=='own'||selected<0)return;const q=manual||sample(own,currentTime),f=own[selected];Object.assign(f,Object.fromEntries(names.map((k,i)=>[k,q[i]])),{label:$('pname').value.trim()||f.label,event:$('event').value||null});persist();steps();moveTo(f.t_s,selected);setMsg('Vybraná poloha upravena.');};
$('undo').onclick=()=>{own.pop();persist();pickSeq('own');setMsg('Poslední poloha odebrána.');};
$('copy').onclick=()=>{if(own.length&&!confirm('Nahradit vlastní polohy kopií vzorového pohybu?'))return;own=(presets[seq]?.frames||demo).map(f=>({...f}));persist();pickSeq('own');setMsg('Vzor zkopírován. Vyber krok a uprav jeho polohu.');};
$('seq').onchange=()=>pickSeq($('seq').value);$('speed').onchange=()=>scale=+$('speed').value;
$('timebar').oninput=()=>moveTo(+$('timebar').value);$('reset').onclick=()=>moveTo(0);
function frame(ts){if(!playing)return;const end=active().at(-1).t_s;currentTime=Math.min(end,currentTime+Math.min(.12,(ts-lastStamp)/1000)*scale);lastStamp=ts;
 if(ts-lastUI>65||currentTime>=end){ui();lastUI=ts;}render();if(currentTime>=end){stop();return;}requestAnimationFrame(frame);}
$('play').onclick=()=>{if(playing){stop();return;}if(active().length<2)return;manual=null;selected=-1;if(currentTime>=active().at(-1).t_s-.001)currentTime=0;playing=true;$('play').textContent='Pozastavit';lastStamp=performance.now();requestAnimationFrame(frame);};
function download(data,type,name){const url=URL.createObjectURL(new Blob([data],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
$('save').onclick=()=>{download(JSON.stringify({...recipe,name:presets[seq]?.name||'Vlastní pohyb',waypoints:active()},null,2),'application/json','Emil-ETA-V2-pohyb.json');};
$('glb').onclick=()=>download(raw,'model/gltf-binary','Emil-ETA-Waveshare-V2.glb');
$('load').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>1024*1024)throw Error('Soubor je příliš velký.');const p=JSON.parse(await file.text());
 if(p.format!==recipe.format||p.model!==recipe.model)throw Error('Nekompatibilní formát nebo model.');const candidate=validate(p.waypoints);if(own.length&&!confirm('Nahradit vlastní program importovanými polohami?'))return;own=candidate;persist();pickSeq('own');mode(true);setMsg('Program načten.');}catch(e){setMsg(e.message);}finally{e.target.value='';}};
try{const p=JSON.parse(localStorage.getItem('emil-eta-waveshare-v2'));if(p?.length)own=validate(p);}catch{}
function vbuttons(view){document.querySelectorAll('[data-v]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v===view)));}
document.querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{const v=b.dataset.v;
 [phi,el,dist]=v==='top'?[Math.PI/2,Math.PI/2-.002,.85]:v==='side'?[Math.PI/2,.075,1.12]:[.93,.38,1.22];vbuttons(v);render();});
$('path').onclick=()=>{showPath=!showPath;$('path').setAttribute('aria-pressed',String(showPath));render();};
let drag=null;stage.onpointerdown=e=>{if(e.target.closest('button'))return;drag=[e.clientX,e.clientY];stage.setPointerCapture(e.pointerId);};
stage.onpointermove=e=>{if(!drag)return;phi-=(e.clientX-drag[0])*.008;el=clamp(el+(e.clientY-drag[1])*.008,.025,1.565);drag=[e.clientX,e.clientY];vbuttons('');render();};
stage.onpointerup=stage.onpointercancel=()=>drag=null;
stage.addEventListener('wheel',e=>{e.preventDefault();dist=clamp(dist*Math.exp(clamp(e.deltaY,-400,400)*.001),.48,1.8);render();},{passive:false});
let auditRun=0;
function clearAudit() {
    auditRun++;
    $('auditText').textContent='';
    $('auditJump').hidden=true;
    $('audit').disabled=active().length<2;
}
$('audit').onclick=()=>{
    const frames=active().map(frame=>({...frame})), end=frames.at(-1).t_s;
    const run=++auditRun, count=Math.ceil(end*100)+1;
    let i=0,bad=0,first=null;
    const findings=new Set();
    $('audit').disabled=true;
    $('auditJump').hidden=true;
    function batch() {
        if (run!==auditRun) return;
        const until=Math.min(i+250,count);
        for (;i<until;i++) {
            const t=Math.min(i/100,end), q=sample(frames,t), object=carried(frames,t,q);
            const collisions=check(q,object.held);
            if (object.issue) collisions.push(object.issue);
            if (collisions.length) {
                bad++;
                if (first===null) first=t;
                collisions.forEach(name=>findings.add(name));
            }
        }
        if (i<count) {
            $('auditText').textContent='Kontroluji '+Math.floor(100*i/count)+' % programu…';
            requestAnimationFrame(batch);
            return;
        }
        $('auditText').textContent=count.toLocaleString('cs-CZ')+' poloh po 0,01 s. '+
            (bad ? 'Nález v '+bad+' polohách · '+[...findings].join(', ')+'.' : 'Kontrolované obálky prošly celým programem bez nálezu.');
        $('audit').disabled=false;
        if (first!==null) {
            $('auditJump').hidden=false;
            $('auditJump').onclick=()=>moveTo(first);
        }
    }
    batch();
};
steps();mode(false);new ResizeObserver(fit).observe(stage);fit();
