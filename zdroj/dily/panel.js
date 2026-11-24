// Prohlížení přesné geometrie právě vykreslené sestavy; katalog výrobních výstupů patří ke konkrétní revizi.
function r16CreateParts() {
  const dialog=$('r16PartDialog'), list=$('r16PartList'), search=$('r16PartSearch'), viewport=$('r16PartCanvas');
  const trigger=$('r16PartCatalog'),toggle=$('r16PartToggle');
  const baseLinks={index:new Map(),pair:new Map()}, catalog=new Map(), profiles=new Map(), urls=new Map();
  let scene,displayCommands=[],selection=null,catalogState='idle',payloadData=null,offline=null,inspector,center=[0,0,0],extent=100,visible=false,zoom=1,az=-1.02,el=.32;
  let suppressTap=false,request=null,selectedRow=null,meshColor=hex('#659c87');
  const touches=new Set(), localStatic=!document.querySelector('meta[name="robot-api"]');
  const normalize=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('cs');
  let lastAvailable=null;
  const current=()=>r9IsActive()&&String(r14Rev)==='R16'&&!r14View;
  const changed=()=>typeof r14Has==='function'&&r14Has();
  const relative=s=>typeof s==='string'&&!s.includes('..')&&!s.startsWith('/')&&/^[A-Za-z0-9_./-]+$/.test(s);
  function fileURL(file){
    if(!relative(file))return null;
    if(offline?.files?.[file]){
      if(!urls.has(file)){const binary=atob(offline.files[file]),bytes=Uint8Array.from(binary,c=>c.charCodeAt(0));urls.set(file,URL.createObjectURL(new Blob([bytes])));}
      return urls.get(file);
    }
    if(location.protocol==='file:')return null;
    return localStatic?'tisk/R16/'+file:'index.php?data=tisk-r16&file='+encodeURIComponent(file);
  }
  function indexCatalog(payload){
    if(String(payload.revision)!=='R16'||!Array.isArray(payload.parts))throw Error('Nesouhlasí revize katalogu.');
    payloadData=payload;for(const [id,p] of Object.entries(payload.profiles||{}))profiles.set(id,p);
    for(const p of payload.parts){
      catalog.set(p.id,p);
      for(const ref of p.source_objects||[]){
        if(Number.isInteger(ref.index))baseLinks.index.set(ref.index,p);
        const pair=ref.key+'|'+ref.link;const old=baseLinks.pair.get(pair);
        if(!old)baseLinks.pair.set(pair,p);else if(old.id!==p.id)baseLinks.pair.set(pair,{id:null});
      }
    }
  }
  async function getCatalog(){
    if(catalogState==='ok')return;
    if(request)return request;
    catalogState='loading';
    request=(async()=>{
      const embedded=$('r16PartBundle');
      if(embedded){offline=JSON.parse(embedded.textContent);indexCatalog(offline.catalog);}
      else{
        const url=fileURL('catalog.json');if(!url)throw Error('Katalog vyžaduje připojení.');
        const response=await fetch(url,{credentials:'same-origin'});if(!response.ok)throw Error('Katalog není dostupný.');
        indexCatalog(await response.json());
      }
      catalogState='ok';
    })().catch(()=>{catalogState='error';}).finally(()=>{request=null;if(dialog.open)showSelection();});
    return request;
  }
  function matching(ref){
    if(!ref)return null;
    const exact=Number.isInteger(ref.index)?baseLinks.index.get(ref.index):null;
    if(exact?.source_objects.some(o=>o.index===ref.index && (o.key===ref.key||ref.key===r14BaseKey(o.key)) && o.link===ref.link))return exact;
    const pair=baseLinks.pair.get(ref.key+'|'+ref.link);if(pair?.id)return pair;
    return null;
  }
  function capture(cmd,target,angle,elev,span){
    const active=current();if(active!==lastAvailable)refreshAvailability();
    if(!active){scene=null;return;}
    const look=[Math.cos(elev)*Math.cos(angle),Math.cos(elev)*Math.sin(angle),Math.sin(elev)];
    const right=unit(cross([0,0,1],look));
    scene={cmd,camera:{target,look,right,up:cross(look,right),span,width:$('canvas').clientWidth,height:$('canvas').clientHeight}};
  }
  function fallbackName(ref) {return ref.key.replace(/^r(?:8|9|10|11|12|13)_/,'').replaceAll('_',' ');}
  function allRefs(){
    const out=r9RenderItems.map((o,index)=>({key:r14Key0[index],link:o.link,owner:o.owner,index,t:o.t,mesh:o.key==='L_knee_ram'?'L_knee_ram_R5':r14BaseKey(o.key)}));
    for(const o of r9CoverItems)out.push({key:o.key,link:o.link,owner:o.link,t:I,mesh:o.key});
    for(const o of [...r11ShinItems('climb'),...r11PickupToolItems()])out.push({key:o.key,link:o.link,owner:o.owner,t:o.t,mesh:o.key});
    for(const [i,link] of [10,20].entries())out.push({key:'opora_dlane',link,owner:link,mesh:'ball',t:at((1-2*i)*146,-12,205,12,12,12)});
    return out;
  }
  function references(part){
    const refs=allRefs(),resolved=[];
    for(const src of part.source_objects||[]){
      const exact=Number.isInteger(src.index)&&refs[src.index];
      if(exact?.key===src.key&&exact.link===src.link){resolved.push(exact);continue;}
      const match=refs.find(r=>r.key===src.key&&r.link===src.link);
      if(match)resolved.push(match);
    }
    return resolved;
  }
  function fillList(row){
    const prev=list.value;list.replaceChildren();
    const query=normalize(search.value).trim().split(/\s+/).filter(Boolean);
    const filter=$('r16PartFilter').value;
    const parts=[...catalog.values()].filter(p=>(filter==='all'||(filter==='print')===Boolean(p.printable))&&query.every(term=>normalize([p.name,p.category,p.side,p.id,...(p.source_objects||[]).map(s=>s.key)].join(' ')).includes(term)));
    for(const p of parts){const owner=p.source_objects?.[0]?.owner;const suffix=p.side?' · '+p.side:'';const joint=!p.printable&&owner!=null&&owner<22?' · '+data.joints[owner]:'';list.add(new Option(p.name+suffix+joint,p.id));}
    if(row&&parts.includes(row))list.value=row.id;
    else if(!row&&prev&&parts.some(p=>p.id===prev))list.value=prev;
    else list.selectedIndex=-1;
    $('r16PartCount').textContent=catalogState==='ok'?parts.length+' / '+catalog.size+' položek':catalogState==='error'?'Výrobní katalog se nepodařilo načíst.':'Načítám výrobní katalog…';
  }
  function geometry(refs){
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];displayCommands=[];
    for(const [i,ref] of refs.entries()){
      const g=rnd.geometry(ref.mesh||ref.key);if(!g)continue;
      const t=ref.t||I;
      for(let j=0;j<g.v.length;j+=3){const p=pos(t,[g.v[j],g.v[j+1],g.v[j+2]]);for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],p[k]);hi[k]=Math.max(hi[k],p[k]);}}
      if(!inspector)inspector=shoulderSoftwareRenderer(viewport);
      const key='dil'+i;inspector.add(key,g.v,g.f);displayCommands.push([key,t,meshColor]);
    }
    visible=Boolean(displayCommands.length);if(!visible)return null;
    center=lo.map((v,i)=>(hi[i]+v)/2);const size=lo.map((v,i)=>hi[i]-v);
    extent=Math.max(1,Math.hypot(...size));return size;
  }
  function draw(){
    if(!visible||!dialog.open||!viewport.clientWidth||!viewport.clientHeight)return;
    const widthFactor=Math.min(1,viewport.clientWidth/viewport.clientHeight);
    inspector.paint(displayCommands,center,az,el,extent*1.08/(widthFactor*zoom));
  }
  function fact(label,value){
    if(value==null||value==='')return;const wrap=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');
    dt.textContent=label;dd.textContent=value;wrap.append(dt,dd);$('r16PartFacts').append(wrap);
  }
  function link(parent,title,file){
    const url=fileURL(file);if(!url)return;
    const a=document.createElement('a');a.textContent=title;a.href=url;a.download=file.split('/').pop();parent.append(a);
  }
  const czSize=arr=>arr?.length===3?arr.map(v=>fmt(Number(v),2)).join(' × ')+' mm':null;
  function showSelection(){
    if(!dialog.open)return;
    selectedRow=selection?.row||matching(selection?.ref);
    const row=selectedRow,ref=selection?.ref;
    const compound=row?.printable&&row.source_objects.length>1;
    const refs=compound?references(row):ref?[ref]:[];
    const actual=geometry(refs);fillList(row);
    $('r16PartEmpty').hidden=!!actual;
    $('r16PartEmpty').textContent=ref?'Náhled této součásti není k dispozici.':'Vyber součást v seznamu nebo klikni na robota.';
    $('r16PartTitle').textContent=row?.name||(ref?fallbackName(ref):'Katalog dílů');
    $('r16PartType').textContent=row?[row.category,row.side==='L'?'levá strana':row.side==='P'?'pravá strana':''].filter(Boolean).join(' · '):'Díly robota H22';
    $('r16PartSource').textContent=ref||row?(changed()?'R16 s pracovní úpravou kloubů. Náhled odpovídá aktuálnímu modelu.':'Konstrukce H22 · R16'):'';
    $('r16PartFacts').replaceChildren();$('r16PartDownloads').replaceChildren();
    $('r16PartProcess').hidden=true;$('r16PartProcessBody').replaceChildren();
    if(ref){
      fact('Článek',data.joints?.[ref.link]||(ref.link===22?'Trup':undefined));
      fact('Rozměry v modelu',czSize(actual));
      fact('Označení geometrie',ref.key);
    }
    if(row){
      fact('Výrobní stav',row.status);
      fact('Rozměry ve směru tisku',czSize(row.print_dimensions_mm));
      if(row.volume_cm3!=null)fact('Objem plného modelu',fmt(row.volume_cm3,2)+' cm³');
      if(row.solid_mass_reference_g!=null)fact('Hmotnost plného materiálu',fmt(row.solid_mass_reference_g,1)+' g při '+fmt(row.solid_reference_density_g_cm3,2)+' g/cm³');
      if(row.weight_estimate_g!=null && typeof row.weight_estimate_g==='number')fact('Odhad hmotnosti',fmt(row.weight_estimate_g,1)+' g');
      const note=Array.isArray(row.notes)?row.notes.join(' '):row.notes;
      $('r16PartNote').textContent=note||'';
      if(row.printable&&row.files?.model3mf){
        if(changed())$('r16PartNote').textContent+=' Tiskový soubor je ověřen pro základní R16. Pro jeho stažení obnov výchozí geometrii.';
        else{
          link($('r16PartDownloads'),'Stáhnout díl · 3MF',row.files.model3mf);
          if(row.files.stl)link($('r16PartDownloads'),'STL',row.files.stl);
          if(row.files.project3mf)link($('r16PartDownloads'),row.reinforcement?.length?'Projekt X1 Carbon se zesílením':'Projekt pro X1 Carbon',row.files.project3mf);
          showProcess(row);
        }
      }
    }else $('r16PartNote').textContent=ref?'U této součásti není přiřazen katalogový tiskový soubor.':'';
    const j=ref?.owner;$('r16GoJoint').hidden=!Number.isInteger(j)||j<0||j>=22;
    draw();
  }
  function showProcess(row){
    const p=row.process||profiles.get(row.process_id);if(!p || typeof p!=='object')return;
    const output=$('r16PartProcessBody'), add=(label,val)=>{if(val==null||val==='')return;const line=document.createElement('p');line.textContent=label+' · '+(Array.isArray(val)?val.join(' '):val);output.append(line);};
    add('Materiál',p.material?.name||p.material);add('Výchozí profil',p.base);add('Počet stěn',p.wall_loops);add('Výplň',p.infill_pct!=null?p.infill_pct+' %':null);
    add('Horní / dolní vrstvy',p.top_layers!=null&&p.bottom_layers!=null?p.top_layers+' / '+p.bottom_layers:null);add('Orientace',p.orientation);add('Lokální zesílení',p.local_reinforcement);
    add('Orientace dílu',row.orientation);
    if(row.reinforcement?.length)add('Oblasti zesílení',row.reinforcement.map(z=>z.name).join(', '));
    add('Kontrola výtisku',p.checks);add('Bambu Studio · X1 Carbon',p.import_steps);
    if(row.files.project3mf&&row.reinforcement?.length)add('Projekt X1C','V Bambu Studiu otevři soubor jako projekt a v panelu Objekty ověř místní modifikátory.');
    if(p.preset_file)link(output,'Stáhnout profil Bambu Studio',p.preset_file);
    add('Anycubic Slicer Next · Kobra S1 Max',p.kobra?.steps);
    add('Hmotnost výtisku','Odhad s výplní zjistíš po rozřezání dílu s vlastním profilem. Hmotnost plného materiálu v tabulce vychází z objemu geometrie.');
    $('r16PartProcess').hidden=!output.childElementCount;
  }
  function show(ref,row=null,color=null){
    if(!current())return;stop();selection=ref||row?{ref,row}:null;
    search.value='';$('r16PartFilter').value='all';zoom=1;az=-1.02;el=.32;visible=false;
    meshColor=Array.isArray(color)?color:hex('#659c87');
    if(!dialog.open)dialog.showModal();showSelection();getCatalog();
  }
  function tap(e){
    if(!current()||toggle.getAttribute('aria-pressed')!=='true')return false;
    if(suppressTap)return true;
    const canvas=$('canvas'),bounds=canvas.getBoundingClientRect();
    if(!scene)return false;
    const cmd=r16PickSurface(scene.cmd,key=>rnd.geometry(key),scene.camera,e.clientX-bounds.left,e.clientY-bounds.top);
    if(cmd)show({...cmd[3],mesh:cmd[0]},null,cmd[2]);
    return true;
  }
  list.onchange=()=>{const row=catalog.get(list.value);if(row){selection={row,ref:references(row)[0]};meshColor=hex('#659c87');zoom=1;showSelection();}};
  search.oninput=$('r16PartFilter').onchange=()=>fillList(selectedRow);
  $('r16PartClose').onclick=()=>dialog.close();$('r16GoJoint').onclick=()=>{const ref=selection?.ref;if(!ref)return;dialog.close();r10SelectMotor(ref.owner);$('joint').scrollIntoView({block:'nearest'});};
  trigger.onclick=()=>{if(current())show(null);};
  toggle.onclick=()=>toggle.setAttribute('aria-pressed',toggle.getAttribute('aria-pressed')==='true'?'false':'true');
  const can=$('canvas');can.addEventListener('pointerdown',e=>{if(!touches.size)suppressTap=false;touches.add(e.pointerId);if(touches.size>1)suppressTap=true;},true);
  for(const event of ['pointerup','pointercancel','lostpointercapture'])can.addEventListener(event,e=>touches.delete(e.pointerId),true);
  let drag=null;
  viewport.onpointerdown=e=>{if(!e.isPrimary)return;viewport.setPointerCapture(e.pointerId);drag=[e.clientX,e.clientY];};
  viewport.onpointermove=e=>{if(!drag||!e.isPrimary)return;az-=(e.clientX-drag[0])*.009;el=cl(el+(e.clientY-drag[1])*.009,-1.54,1.54);drag=[e.clientX,e.clientY];draw();};
  viewport.onpointerup=viewport.onpointercancel=()=>{drag=null;};
  viewport.onkeydown=e=>{const turn={ArrowLeft:[-.13,0],ArrowRight:[.13,0],ArrowUp:[0,.13],ArrowDown:[0,-.13]}[e.key];if(turn){e.preventDefault();az+=turn[0];el=cl(el+turn[1],-1.54,1.54);draw();}};
  function zoomBy(n){zoom=cl(zoom*n,.45,5);draw();}
  viewport.onwheel=e=>{e.preventDefault();zoomBy(Math.exp(-e.deltaY*.001));};
  $('r16PartPlus').onclick=()=>zoomBy(1.22);$('r16PartMinus').onclick=()=>zoomBy(1/1.22);
  $('r16PartReset').onclick=()=>{az=-1.02;el=.32;zoom=1;draw();};
  new ResizeObserver(draw).observe(viewport);
  function refreshAvailability(){
    const active=current();lastAvailable=active;toggle.disabled=trigger.disabled=!active;
    trigger.title=active?'Prohlédnout geometrii a tiskové soubory':'Katalog je určen pro základní R16 a její pracovní úpravy. Vrať se z historického pohybu k současné sestavě.';
    if(!active&&dialog.open)dialog.close();
  }
  $('r8Assembly').addEventListener('change',refreshAvailability);refreshAvailability();
  // Přenositelný HTML prohlížeč obsahuje schválené výstupy právě tohoto katalogu i data referenčního modelu.
  // Zdrojový soubor na serveru fyzické modely neobsahuje. Přenos probíhá až na výslovné stažení.
  const saveButton=$('save'),saveStatus=document.createElement('span');
  saveStatus.className='small';saveStatus.setAttribute('role','status');saveButton.after(saveStatus);
  function to64(bytes){
    return new Promise((ok,fail)=>{const reader=new FileReader();reader.onload=()=>ok(String(reader.result).split(',')[1]);reader.onerror=()=>fail(Error('Chyba při sestavení souboru.'));reader.readAsDataURL(new Blob([bytes]));});
  }
  async function checkFile(path,data){
    const bytes=new Uint8Array(data), ext=path.split('.').pop();
    if(ext==='3mf' && !(bytes[0]===80 && bytes[1]===75 && bytes[2]===3 && bytes[3]===4))throw Error('Neplatné 3MF: '+path);
    if(ext==='stl' && !(data.byteLength>=84 && 84+50*new DataView(data).getUint32(80,true)===data.byteLength))throw Error('Neplatné STL: '+path);
    if(ext==='json')JSON.parse(new TextDecoder().decode(bytes));
    const expected=payloadData.file_checksums?.[path];
    if(expected){
      if(!window.crypto?.subtle)throw Error('Pro ověření tiskových souborů otevři aplikaci přes HTTPS nebo jako místní soubor.');
      const hash=new Uint8Array(await window.crypto.subtle.digest('SHA-256',data));
      if(Array.from(hash,n=>n.toString(16).padStart(2,'0')).join('')!==expected)throw Error('Nesouhlasí kontrolní součet souboru '+path);
    }
  }
  async function saveOffline(){
    if(saveButton.disabled)return;saveButton.disabled=true;saveStatus.textContent='Připravuji offline HTML…';
    try{
      await getCatalog();if(catalogState!=='ok')throw Error('Katalog R16 se nepodařilo načíst. Zkus uložit HTML z otevřené online aplikace.');
      const paths=new Set();
      for(const row of catalog.values())if(row.printable)for(const path of Object.values(row.files||{}))paths.add(path);
      for(const profile of profiles.values())if(profile.preset_file)paths.add(profile.preset_file);
      if(!paths.size||[...paths].some(p=>!relative(p)))throw Error('Neplatný seznam tiskových souborů.');
      const files={},pending=[...paths];let done=0,failure=null;
      async function work(){
        while(pending.length&&!failure){
          const path=pending.shift();
          try{
            if(offline?.files?.[path]){
              const bytes=Uint8Array.from(atob(offline.files[path]),c=>c.charCodeAt(0));
              await checkFile(path,bytes.buffer);files[path]=offline.files[path];
            }else{
              const url=fileURL(path);if(!url)throw Error('Chybí dříve uložený soubor '+path);
              const r=await fetch(url,{credentials:'same-origin'});if(!r.ok)throw Error('Soubor '+path+' se nepodařilo načíst (HTTP '+r.status+').');
              const data=await r.arrayBuffer();await checkFile(path,data);files[path]=await to64(data);
            }
            done++;saveStatus.textContent='Příprava tiskových souborů '+done+' / '+paths.size;
          }catch(e){failure=e;}
        }
      }
      await Promise.all([work(),work(),work()]);if(failure)throw failure;
      const safeJson=v=>JSON.stringify(v).replaceAll('<','\\u003c');
      const copy=new DOMParser().parseFromString(originalHTML,'text/html');
      let kondo=$('kModelData')?.textContent.trim();
      if(!kondo){
        const source=localStatic?'kondo-data.json':'index.php?data=kondo';
        const response=await fetch(source,{credentials:'same-origin'});if(!response.ok)throw Error('Chybí data referenčního modelu Kondo.');
        kondo=await response.text();
      }
      const kondoNode=copy.getElementById('kModelData');
      if(!kondoNode)throw Error('V uložené stránce chybí referenční model Kondo.');
      kondoNode.textContent=safeJson(JSON.parse(kondo));
      for(const node of copy.querySelectorAll('meta[name="robot-csrf"],meta[name="robot-api"],#khLoad,#r16PartBundle'))node.remove();
      const script=copy.createElement('script');script.type='application/json';script.id='r16PartBundle';script.textContent=safeJson({catalog:payloadData,files});
      copy.head.append(script);
      const blob=new Blob(['<!doctype html>',copy.documentElement.outerHTML],{type:'text/html;charset=utf-8'});
      const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download='Emil-H22-'+r14Rev+'-simulator.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
      saveStatus.textContent='Offline HTML připraveno · '+paths.size+' souborů pro tisk.';
    }catch(error){saveStatus.textContent='HTML se nepodařilo uložit. '+error.message;}
    finally{saveButton.disabled=false;}
  }
  if(String(r14Rev)==='R16')saveButton.onclick=saveOffline;
  return {capture,tap};
}
