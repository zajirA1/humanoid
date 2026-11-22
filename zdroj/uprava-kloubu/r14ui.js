/* ===== R14 · úprava kloubů přímo v modelu ===== */
const r14D=JSON.parse($('r14Data').textContent),r14Rev=r14D.revize||'R13';
const r14P0=r9Pivots.map(p=>p.slice()),r14Links0=r10MassModels.r9.links.map(l=>l.slice());
const r14Eng=r14Engine({par,axes,P:r14P0,links:r14Links0,lim:r14D.lim,mu:r14D.mu,servoKg:r14D.servoKg});
r14Eng.setClouds(r14D.clouds,r14D.pairs);
const r14Items0=r9RenderItems.map(o=>o.t.slice()),r14Loads0=r9Loads.climb.loads.map(l=>l?{...l}:l),r14Store=new WeakMap();
let r14Edits={},r14Ver=0,r14AppliedVer=-1,r14AppliedOn=null,r14Active=false,r14Sel=4,r14Proj=null,r14W=null,r14Busy=false,r14Result=null,r14Base=null,r14Drag=null,r14Open=false;
const r14Has=()=>Object.keys(r14Edits).length>0;
const r14Mirror=j=>j>=2&&j<12?j+10:j>=12?j-10:j;
const r14Zero=e=>!e||(!e.rot&&!e.carry&&Math.hypot(...e.d)<1e-6);
// direction from the axis towards the bridge of the fork on the driven part (rest pose)
const r14ForkDir={};
for(let j=0;j<22;j++){const f=r14D.forks[j];if(!f)continue;const ch=par.map((p,k)=>p===j?k:-1).filter(k=>k>=0);let v=ch.length?sub(r14P0[ch[0]],r14P0[j]):[0,0,-1];if(j===7||j===17)v=[0,0,-1];if(j===10||j===20)v=[0,0,-1];
 const a=axes[j],along=dot(v,a);v=sub(v,mul(a,along));if(norm(v)<1e-6)v=Math.abs(a[2])<.9?[0,0,-1]:[0,-1,0];r14ForkDir[j]=unit(v)}
function r14Apply(on,edits=r14Edits){
 const st=r14Eng.setEdits(on?edits:{});
 for(let j=0;j<22;j++)for(let a=0;a<3;a++){r9Pivots[j][a]=st.P[j][a];r14E[j][a]=on?st.E[j][a]:0}
 r10MassModels.r9.links.forEach((l,i)=>{for(let a=1;a<4;a++)l[a]=st.links[i][a]});
 r9RenderItems.forEach((o,k)=>{let t=r14Items0[k].slice();const j=o.owner,e=on&&Number.isInteger(j)&&j<22&&!o.frame?edits[j]:null;
  if(e){if(e.rot&&o.link===par[j])t=mat(rot(axes[j],e.rot,r14P0[j]),t);if(!(e.carry&&o.link===j))for(let a=0;a<3;a++)t[9+a]+=e.d[a]}o.t=t});
 r14AppliedOn=on;r14AppliedVer=r14Ver;r14Active=on;
}
function r14Sync(){const on=r9IsActive();if(on!==r14AppliedOn||r14Ver!==r14AppliedVer)r14Apply(on)}
function r14Rec(pose){let r=r14Store.get(pose);if(!r){r={q0:pose.q.slice(),rt0:pose.rt.slice(),ver:0};r14Store.set(pose,r)}return r}
function r14Climb(i){const pose=r9Motion.poses[i];if(!pose)return null;const rec=r14Rec(pose);if(rec.ver===r14Ver)return rec;rec.ver=r14Ver;const L=r9Loads.climb.loads,b=r14Loads0[i];
 if(!r14Has()){pose.q=rec.q0.slice();pose.rt=rec.rt0.slice();L[i]=b?{...b}:b;rec.res=null;return rec}
 const flat=r14D.contacts[i],w0=r14Eng.fk0(rec.q0,rec.rt0),r=r14Eng.retarget(rec.q0,rec.rt0,w0,flat);pose.q=r.q;pose.rt=r.root;
 const s=r14Eng.statics(r14Eng.fk(r.q,r.root),flat);rec.res={drift:r.drift,shift:r.shift,s:s?s.s:null,jmax:s?s.jmax:-1,tau:s?s.tau:null};
 if(!s){L[i]={...(b||{}),ratio:Infinity,joint:'rovnováha nenalezena',moving:Infinity};return rec}const k=b&&b.ratio>0?b.moving/b.ratio:1.1,fz=s.fz,g=l=>fz[l]||0;
 L[i]={...(b||{}),tau:s.tau,ratio:s.s,joint:data.joints[s.jmax],cm:s.com,leftN:g(10),rightN:g(20),palmN:g(10)+g(20),kneeN:[g(5),g(15)],footN:[g(7),g(17)],moving:s.s*k,movingTau:s.tau.map(v=>v*k)};return rec}
function r14Walk(pose){if(!pose||!pose.contacts)return;const rec=r14Rec(pose);if(rec.ver===r14Ver)return;rec.ver=r14Ver;
 if(!r14Has()){pose.q=rec.q0.slice();pose.rt=rec.rt0.slice();return}
 const flat=[];if(pose.contacts.leftFoot)flat.push(7,0,0,0);if(pose.contacts.rightFoot)flat.push(17,0,0,0);
 const r=r14Eng.retarget(rec.q0,rec.rt0,r14Eng.fk0(rec.q0,rec.rt0),flat);pose.q=r.q;pose.rt=r.root;rec.res={drift:r.drift,shift:r.shift}}
function r14Legacy(pa){if(!Array.isArray(pa)||!Array.isArray(pa[0])||!Array.isArray(pa[1]))return;let rec=r14Store.get(pa);if(!rec){rec={q0:pa[0].slice(),p0:pa[1].slice(),ver:0};r14Store.set(pa,rec)}if(rec.ver===r14Ver)return;rec.ver=r14Ver;
 if(!r14Has()){pa[0]=rec.q0.slice();pa[1]=rec.p0.slice();return}
 const rt=rec.p0.map((x,i)=>x/(i<9?12000:16)),f=pa[2]|0,flat=[];if(f&1)flat.push(7,0,0,0);if(f&2)flat.push(17,0,0,0);if(f&4)flat.push(10,0,0,0);if(f&8)flat.push(20,0,0,0);
 const r=r14Eng.retarget(rec.q0,rt,r14Eng.fk0(rec.q0,rt),flat);pa[0]=r.q;pa[1]=r.root.map((x,i)=>x*(i<9?12000:16))}
function r14Fix(p){if(!r14Ready||!r14Active||!r14Has()||!p||!p.q||!p.rt)return p;const w0=r14Eng.fk0(p.q,p.rt),flat=[];
 for(const [link,sx] of [[7,1],[17,-1]]){let z=1e9;for(const c of [[sx*18.5,38],[sx*18.5,-58],[sx*95.5,38],[sx*95.5,-58]])z=Math.min(z,pos(w0[link],[c[0],c[1],0])[2]);if(z<1)flat.push(link,0,0,0)}
 const r=r14Eng.retarget(p.q,p.rt,w0,flat);return {...p,q:r.q,rt:r.root}}
function r14Before(){if(!r14Ready)return;r14Sync();if(!r14Active)return;
 if(mode==='climb')r14Climb(idx);else if(mode==='walk'){r14Walk(walkData.poses[idx]);r14Walk(walkData.poses[idx+1])}else if(!r10IsMotion()){const o=info();if(o&&o.poses)r14Legacy(o.poses[idx])}}
function r14After(project,w){if(!r14Ready)return;r14Proj=project;r14W=w;r14Overlay()}
// ---------- overlay: joint handles and the redrawn fork ----------
const r14Layer=document.createElementNS('http://www.w3.org/2000/svg','svg');r14Layer.id='r14Layer';$('stage').append(r14Layer);
function r14Pivot(j,w){return pos(w[par[j]],r9Pivots[j])}
function r14Overlay(){const show=r14Open&&r9IsActive()&&!document.body.classList.contains('kondo-active');r14Layer.style.display=show?'':'none';if(!show||!r14Proj||!r14W)return;
 const w=r14W,P2=p=>r14Proj(p),parts=[],ln=(a,b,c,wd=2.5,dash='')=>{const A=P2(a),B=P2(b);parts.push('<line x1="'+A[0].toFixed(1)+'" y1="'+A[1].toFixed(1)+'" x2="'+B[0].toFixed(1)+'" y2="'+B[1].toFixed(1)+'" stroke="'+c+'" stroke-width="'+wd+'" stroke-linecap="round"'+(dash?' stroke-dasharray="'+dash+'"':'')+'/>')};
 for(let j=0;j<22;j++){const e=r14Edits[j];if(r14Zero(e)&&j!==r14Sel)continue;const f=r14D.forks[j],T=w[par[j]],a=axes[j];
  const pn=r9Pivots[j],po=r14P0[j];
  if(e&&Math.hypot(...e.d)>.05)ln(pos(T,po),pos(T,pn),'#1f2a30',2,'4 3');
  if(f){const h=f.span/2,u=r14ForkDir[j],b0=plus(po,mul(u,f.L)),Wj=w[j];
   // points fixed on the driven part are given in its original coordinates; the axis ends follow the new pivot
   const axis=s=>pos(T,plus(pn,mul(a,s*h))),br=s=>pos(Wj,plus(b0,mul(a,s*h)));
   const col=j===r14Sel?'#c2571a':'#2a78d6';ln(axis(-1),axis(1),col,2,'2 3');for(const s of [-1,1])ln(axis(s),br(s),col,3);ln(br(-1),br(1),col,3)}
 }
 for(let j=0;j<22;j++){const p=P2(r14Pivot(j,w)),ed=!r14Zero(r14Edits[j]),sel=j===r14Sel;
  parts.push('<circle data-j="'+j+'" cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="'+(sel?8:5.5)+'" fill="'+(sel?'#c2571a':ed?'#2a78d6':'#ffffff')+'" fill-opacity="'+(sel||ed?.95:.75)+'" stroke="#1f2a30" stroke-width="1.5"><title>'+data.joints[j]+'</title></circle>')}
 r14Layer.innerHTML=parts.join('')}
r14Layer.addEventListener('pointerdown',ev=>{const j=ev.target?.dataset?.j;if(j===undefined)return;ev.preventDefault();ev.stopPropagation();r14Sel=+j;$('r14Joint').value=j;r14Pick();r14Drag={id:ev.pointerId,x:ev.clientX,y:ev.clientY,d0:(r14Edits[r14Sel]?.d||[0,0,0]).slice()};r14Layer.setPointerCapture(ev.pointerId);r14Controls();render(true)});
r14Layer.addEventListener('pointermove',ev=>{if(!r14Drag||ev.pointerId!==r14Drag.id||!r14Proj||!r14W)return;const j=r14Sel,T=r14W[par[j]],p=r14Pivot(j,r14W),s0=r14Proj(p),J=[[],[]];
 for(let a=0;a<3;a++){const u=[0,0,0];u[a]=1;const s=r14Proj(plus(p,dir(T,u)));J[0].push(s[0]-s0[0]);J[1].push(s[1]-s0[1])}
 const dx=ev.clientX-r14Drag.x,dy=ev.clientY-r14Drag.y;if(Math.hypot(dx,dy)<3&&!r14Drag.moved)return;r14Drag.moved=true;
 const a=dot(J[0],J[0]),b=dot(J[0],J[1]),c=dot(J[1],J[1]),det=a*c-b*b||1e-9,l0=(c*dx-b*dy)/det,l1=(a*dy-b*dx)/det;
 const d=[0,1,2].map(k=>cl(Math.round(2*(r14Drag.d0[k]+J[0][k]*l0+J[1][k]*l1))/2,-40,40));r14Set(j,{d})});
const r14EndDrag=ev=>{if(r14Drag&&ev.pointerId===r14Drag.id){r14Drag=null}};r14Layer.addEventListener('pointerup',r14EndDrag);r14Layer.addEventListener('pointercancel',r14EndDrag);
// ---------- edits ----------
function r14Set(j,patch){const cur=r14Edits[j]||{d:[0,0,0],carry:false,rot:0},e={...cur,...patch};
 const put=(k,v)=>{if(r14Zero(v))delete r14Edits[k];else r14Edits[k]=v};put(j,e);
 const m=r14Mirror(j);if($('r14Mirror').checked&&m!==j)put(m,{d:[-e.d[0],e.d[1],e.d[2]],carry:e.carry,rot:-e.rot});
 r14Ver++;r14Result=null;stop();r14Controls();render()}
function r14Controls(){r14Sync();const j=r14Sel,e=r14Edits[j]||{d:[0,0,0],carry:false,rot:0};
 for(let a=0;a<3;a++){$('r14R'+a).value=e.d[a];$('r14N'+a).value=e.d[a]}$('r14Rot').value=e.rot;$('r14RotOut').textContent=fmt(e.rot,0)+'°';$('r14Carry').checked=!!e.carry;
 const f=r14D.forks[j],pn=r14Eng.P[j],lines=[],seg=(a,b)=>norm(sub(a,b)),up=par[j];
 if(up<22){const o=seg(r14P0[j],r14P0[up]),n=seg(pn,r14Eng.P[up]);lines.push(['K ose nad kloubem ('+data.joints[up].split(' · ')[0]+')',fmt(o,1)+' → '+fmt(n,1)+' mm'])}
 const ch=par.map((p,k)=>p===j?k:-1).filter(k=>k>=0);
 if(ch.length){const k=ch[0],o=seg(r14P0[k],r14P0[j]),E=r14Eng.E[j],n=seg(plus(r14Eng.P[k],E),pn);lines.push(['K ose pod kloubem',fmt(o,1)+' → '+fmt(n,1)+' mm'])}
 if(f){const u=r14ForkDir[j],b0=plus(r14P0[j],mul(u,f.L)),rel=sub(b0,e.carry?r14P0[j]:pn),a=axes[j],al=dot(rel,a),L=norm(sub(rel,mul(a,al)));
  lines.push(['Rameno vidlice (osa → můstek)',fmt(f.L,1)+' → '+fmt(L,1)+' mm']);lines.push(['Ohybová tuhost bočnic',(L>f.L+.05||L<f.L-.05)?fmt(100*(Math.pow(f.L/L,3)-1),0)+' %':'beze změny']);
  if(Math.abs(al)>.05&&!e.carry)lines.push(['Posun podél osy',fmt(Math.abs(al),1)+' mm · obě bočnice se posouvají']);
  lines.push(['Rozteč uložení / síla bočnice',fmt(f.span,1)+' / '+fmt(f.t,1)+' mm'])}
 else lines.push(['Vidlice','pro tento kloub nemám změřený tvar uchycení, kreslí se jen poloha osy']);
 lines.push(['Hmotnost posouvaného pohonu',fmt(1000*r14D.servoKg[j],0)+' g']);
 $('r14Facts').innerHTML=lines.map(([k,v])=>'<div><span>'+k+'</span><b>'+v+'</b></div>').join('');
 const n=Object.keys(r14Edits).length;$('r14State').textContent=!r9IsActive()?'Úpravy fungují jen v pracovní sestavě Emil '+r14Rev+'.':n?('Upraveno kloubů: '+n+'. '+(r14Result?'Souhrn níže odpovídá této úpravě.':'Aktuální poloha se přepočítává hned, souhrn celého pohybu až po stisku Přepočítat.')):'Bez úprav. Vyber kloub v seznamu nebo kliknutím na kolečko v modelu a posuň ho.';
 r14ShowResult()}
// ---------- full run ----------
const r14Tick=()=>new Promise(r=>setTimeout(r,0));
function r14WalkPeaks(){const out={};for(const [key,motion] of Object.entries(walkVersions)){let pk=0,at=0,jn='',bad=0,drift=0;motion.poses.forEach((p,i)=>{r14Walk(p);const rr=r14Store.get(p)?.res;if(rr&&r14Has())drift=Math.max(drift,rr.drift);const L=r10Loads(fk(p.q,p.rt),{feet:p.contacts});if(!L||!L.balanced)bad++;if(L&&L.ratio>pk){pk=L.ratio;at=i;jn=L.joint}});out[key]={pk,at,jn,bad,drift}}return out}
async function r14Run(){if(r14Busy||!r9IsActive())return;r14Busy=true;stop();const say=t=>{$('r14Progress').textContent=t},n=r9Motion.poses.length;
 try{
  if(!r14Base){say('Připravuji výchozí hodnoty…');await r14Tick();const saved=r14Edits;r14Edits={};r14Ver++;r14Apply(true);const walks=r14WalkPeaks();r14Edits=saved;r14Ver++;r14Apply(true);
   r14Eng.prepClouds(false);const cs=[],ce=[];for(let i=0;i<n;i++){const rec=r14Rec(r9Motion.poses[i]),c=r14Eng.clearance(r14Eng.fk0(rec.q0,rec.rt0),r14D.ex[i]);cs.push(c.self);ce.push(c.env);if(i%120===0){say('Připravuji výchozí hodnoty… '+Math.round(100*i/n)+' %');await r14Tick()}}
   const tb=Array(22).fill(0);r14Loads0.forEach(l=>l&&l.tau.forEach((v,j)=>tb[j]=Math.max(tb[j],Math.abs(v))));r14Base={walks,cs,ce,tau:tb}}
  r14Sync();r14Eng.prepClouds(true);
  const R={s:[],bad:[],over:[],drift:0,shift:0,tau:Array(22).fill(0),self:[],env:[],pk:0,at:0,jn:''};
  for(let i=0;i<n;i++){const rec=r14Climb(i),pose=r9Motion.poses[i],L=r9Loads.climb.loads[i];
   if(!L||!Number.isFinite(L.ratio)){R.bad.push(i);R.s.push(null)}else{R.s.push(L.ratio);if(L.ratio>1)R.over.push(i);if(L.ratio>R.pk){R.pk=L.ratio;R.at=i;R.jn=L.joint}L.tau.forEach((v,j)=>R.tau[j]=Math.max(R.tau[j],Math.abs(v)))}
   if(rec.res){R.drift=Math.max(R.drift,rec.res.drift);R.shift=Math.max(R.shift,rec.res.shift)}
   const c=r14Eng.clearance(fk(pose.q,pose.rt),r14D.ex[i]);R.self.push(r14D.selfBase[i]+c.self-r14Base.cs[i]);R.env.push(r14D.envBase[i]+c.env-r14Base.ce[i]);
   if(i%60===0){say('Přepočítávám přelez… '+Math.round(100*i/n)+' %');await r14Tick()}}
  say('Přepočítávám chůzi…');await r14Tick();R.walks=r14WalkPeaks();
  const mi=a=>a.reduce((b,v,i)=>v<a[b]?i:b,0);R.selfAt=mi(R.self);R.envAt=mi(R.env);R.selfMin=R.self[R.selfAt];R.envMin=R.env[R.envAt];R.selfBelow=R.self.filter(v=>v<10).length;R.envBelow=R.env.filter(v=>v<5).length;R.ver=r14Ver;
  r14Result=R;say('');
 }catch(err){say('Přepočet selhal: '+err.message);console.error(err)}
 r14Busy=false;r14Controls();render()}
function r14Go(i){if(mode!=='climb'){for(const b of document.querySelectorAll('button[data-mode]'))if(b.dataset.mode==='climb'){b.click();break}}stop();idx=cl(i,0,r9Motion.poses.length-1);render()}
function r14ShowResult(){const box=$('r14Results'),R=r14Result;if(!R||R.ver!==r14Ver){box.innerHTML=R?'<p class="r14-stale">Úprava se od posledního přepočtu změnila. Souhrn už neplatí.</p>':'';return}
 const B=r14Base,p=v=>fmt(100*v,1)+' %',bpk=Math.max(...r14D.ref),hz=climbData.hz,t=i=>fmt(i/hz,1)+' s',n=R.s.length;
 const link=(i,txt)=>'<button class="r14-link" data-go="'+i+'">'+txt+'</button>';
 const pl=k=>k===1?'v 1 poloze':'v '+k+' polohách';const hit=R.envMin<0.5?' <b class="r14-bad">Podle odhadu se díl dotkne schodu.</b>':R.selfMin<0.5?' <b class="r14-bad">Podle odhadu se díly robota dotknou.</b>':'';const verdict=R.bad.length?'<b class="r14-bad">Přelez po úpravě nevychází:</b> '+pl(R.bad.length)+' není rovnováha.':R.over.length?'<b class="r14-bad">Přelez přetěžuje serva</b> '+pl(R.over.length)+'.':R.pk>.85?'<b class="r14-warn">Přelez vychází těsně.</b>':'<b class="r14-ok">Přelez vychází.</b>';
 let h='<p class="r14-verdict">'+verdict+hit+' Pohyb je jen přizpůsobený nové geometrii, není znovu doladěný.</p>';
 const row=(k,a,b,cls='')=>'<tr class="'+cls+'"><th>'+k+'</th><td>'+a+'</td><td>'+b+'</td></tr>';
 h+='<table class="r14-t"><thead><tr><th>Schod 21 cm</th><th>Výchozí</th><th>Po úpravě</th></tr></thead><tbody>'
  +row('Nejvyšší využití serva',p(bpk),p(R.pk)+' · '+link(R.at,t(R.at)))+row('Nejvíc zatížený kloub',r14Loads0[r14D.ref.indexOf(bpk)]?.joint||'',R.jn||'')
  +row('Polohy bez rovnováhy','0',String(R.bad.length)+(R.bad.length?' · '+link(R.bad[0],t(R.bad[0])):''))+row('Polohy nad 100 %','0',String(R.over.length))
  +row('Největší posun opory','0 mm',fmt(R.drift,2)+' mm')+row('Největší posun trupu','0 mm',fmt(R.shift,1)+' mm')
  +row('Nejmenší mezera mezi díly (odhad)',fmt(Math.min(...r14D.selfBase),1)+' mm',fmt(R.selfMin,1)+' mm · '+link(R.selfAt,t(R.selfAt)))+row('Polohy s mezerou pod 10 mm',String(r14D.selfBase.filter(v=>v<10).length),String(R.selfBelow))
  +row('Nejmenší odstup od schodu (odhad)',fmt(Math.min(...r14D.envBase),1)+' mm',fmt(R.envMin,1)+' mm · '+link(R.envAt,t(R.envAt)))+row('Polohy s odstupem pod 5 mm',String(r14D.envBase.filter(v=>v<5).length),String(R.envBelow))+'</tbody></table>';
 // chart
 const Wd=312,Ht=120,ml=30,mr=6,mt=8,mb=18,ymax=Math.max(1.1,R.pk*1.05,bpk*1.05),X=i=>ml+(Wd-ml-mr)*i/(n-1),Y=v=>mt+(Ht-mt-mb)*(1-v/ymax);
 const path=a=>{let d='',pen=false;a.forEach((v,i)=>{if(v===null){pen=false;return}d+=(pen?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1);pen=true});return d};
 let g='';for(const v of [0,.5,1]){g+='<line x1="'+ml+'" x2="'+(Wd-mr)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="'+(v===1?'#8a3a2a':'#d9d2c4')+'" stroke-width="1"'+(v===1?' stroke-dasharray="4 3"':'')+'/><text x="'+(ml-4)+'" y="'+(Y(v)+3.5)+'" text-anchor="end">'+(100*v)+' %</text>'}
 for(const s of [0,60,120,180])if(s*hz<n)g+='<text x="'+X(s*hz)+'" y="'+(Ht-4)+'" text-anchor="middle">'+s+' s</text>';
 for(const i of R.bad)g+='<line x1="'+X(i)+'" x2="'+X(i)+'" y1="'+mt+'" y2="'+(mt+6)+'" stroke="#8a3a2a" stroke-width="1.5"/>';
 h+='<div class="r14-legend"><span><i style="background:#2a78d6"></i>Výchozí '+r14Rev+'</span><span><i style="background:#c2571a"></i>Po úpravě</span><span><i class="r14-dash"></i>Mez serva</span></div>'
  +'<svg id="r14Chart" viewBox="0 0 '+Wd+' '+Ht+'" role="img" aria-label="Využití nejzatíženějšího serva během přelezu, výchozí stav a stav po úpravě">'+g+'<path d="'+path(r14D.ref)+'" fill="none" stroke="#2a78d6" stroke-width="1.6"/><path d="'+path(R.s)+'" fill="none" stroke="#c2571a" stroke-width="1.6"/><line id="r14Cross" y1="'+mt+'" y2="'+(Ht-mb)+'" stroke="#1f2a30" stroke-width="1" visibility="hidden"/></svg><div id="r14Tip" class="r14-tip">Najetím na graf zobrazíš hodnoty, kliknutím skočíš na polohu.</div>';
 // joints
 const rows=[];for(let j=0;j<22;j++){if(j===11||j===21)continue;rows.push([j,B.tau[j],R.tau[j],R.tau[j]/r14D.lim[j]])}rows.sort((a,b)=>b[3]-a[3]);
 h+='<table class="r14-t"><thead><tr><th>Kloub (špička při přelezu)</th><th>Výchozí</th><th>Po úpravě</th></tr></thead><tbody>'+rows.slice(0,8).map(r=>row(data.joints[r[0]],fmt(r[1],2)+' N·m',fmt(r[2],2)+' N·m · '+fmt(100*r[3],0)+' %',r[3]>1?'r14-over':'')).join('')+'</tbody></table>';
 const names={power:'Chůze · silnější kyčle',r7:'Chůze · R7',r6:'Chůze · R6'};
 h+='<table class="r14-t"><thead><tr><th>Chůze (nejvyšší využití)</th><th>Výchozí</th><th>Po úpravě</th></tr></thead><tbody>'+Object.keys(R.walks).map(k=>row(names[k]||k,p(B.walks[k].pk),p(R.walks[k].pk)+(R.walks[k].bad?' · '+R.walks[k].bad+' poloh bez rovnováhy':''),R.walks[k].pk>1?'r14-over':'')).join('')+'</tbody></table>';
 h+='<p class="r14-note">Mezery jsou odhad ze vzorkovaných povrchů s chybou asi ±2 mm. Ostatní pohyby se nové geometrii přizpůsobují stejně (chodidla a dlaně zůstávají na místě) a jejich zatížení uvidíš po přepnutí pohybu. Výjimka: u schodů s opěrami se zobrazené zatížení nepřepočítává.</p>';
 box.innerHTML=h;
 const svg=$('r14Chart'),tip=$('r14Tip'),cross=$('r14Cross'),at=ev=>{const r=svg.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width*Wd;return cl(Math.round((x-ml)/(Wd-ml-mr)*(n-1)),0,n-1)};
 svg.onpointermove=ev=>{const i=at(ev);cross.setAttribute('x1',X(i));cross.setAttribute('x2',X(i));cross.setAttribute('visibility','visible');tip.textContent=t(i)+' · výchozí '+p(r14D.ref[i])+' · po úpravě '+(R.s[i]===null?'bez rovnováhy':p(R.s[i]))};
 svg.onpointerleave=()=>cross.setAttribute('visibility','hidden');svg.onclick=ev=>r14Go(at(ev));
 for(const b of box.querySelectorAll('[data-go]'))b.onclick=()=>r14Go(+b.dataset.go)}
// ---------- export / import ----------
function r14Export(){const R=r14Result&&r14Result.ver===r14Ver?r14Result:null,ed={};for(const [j,e] of Object.entries(r14Edits))ed[j]={kloub:data.joints[j],posun_mm:e.d,nese_dalsi_dily:!!e.carry,natoceni_serva_deg:e.rot||0};
 const out={model:'Emil H22 '+r14Rev,souradnice:'základní poloha, mm: x + vlevo (z pohledu robota), y + dozadu, z + nahoru',upravy:ed,
  souhrn:R?{prelez_max_vyuziti:+R.pk.toFixed(4),prelez_kloub:R.jn,polohy_bez_rovnovahy:R.bad.length,posun_opory_mm:+R.drift.toFixed(3),posun_trupu_mm:+R.shift.toFixed(2),mezera_dilu_odhad_mm:+R.selfMin.toFixed(2),odstup_schod_odhad_mm:+R.envMin.toFixed(2),chuze:Object.fromEntries(Object.entries(R.walks).map(([k,v])=>[k,+v.pk.toFixed(4)]))}:null};
 const txt=JSON.stringify(out,null,1);$('r14Json').value=txt;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([txt],{type:'application/json'}));a.download='emil-uprava-kloubu.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}
function r14Import(){try{const o=JSON.parse($('r14Json').value),src=o.upravy||o.edits||{},ed={};for(const [j,e] of Object.entries(src)){const d=(e.posun_mm||e.d||[0,0,0]).map(v=>cl(+v||0,-40,40));if(+j>=0&&+j<22)ed[+j]={d,carry:!!(e.nese_dalsi_dily??e.carry),rot:+(e.natoceni_serva_deg??e.rot)||0}}
  for(const k of Object.keys(ed))if(r14Zero(ed[k]))delete ed[k];r14Edits=ed;r14Ver++;r14Result=null;stop();r14Controls();render();$('r14Progress').textContent='Nastavení načteno.'}catch(err){$('r14Progress').textContent='Text se nepodařilo načíst: '+err.message}}
// ---------- automatický přepočet v GitHubu (jen na serveru po přihlášení) ----------
const r14Csrf=document.querySelector('meta[name="robot-csrf"]')?.content||'',r14ApiUrl=document.querySelector('meta[name="robot-api"]')?.content||'';
let r14PollT=null;
function r14Payload(){const u={};for(const [j,e] of Object.entries(r14Edits))u[j]={kloub:data.joints[j],posun_mm:e.d,nese_dalsi_dily:!!e.carry,natoceni_serva_deg:e.rot||0};return u}
async function r14Api(akce,telo){const r=await fetch(r14ApiUrl+'?akce='+akce,{method:telo?'POST':'GET',headers:{'X-Robot-CSRF':r14Csrf,...(telo?{'Content-Type':'application/json'}:{})},body:telo?JSON.stringify(telo):undefined,credentials:'same-origin',cache:'no-store'});
 let d={};try{d=await r.json()}catch(e){}if(!r.ok)throw Error(d.chyba||('HTTP '+r.status));return d}
async function r14Send(){const say=t=>{$('r14Progress').textContent=t};if(!r14Has())return say('Nejdřív posuň aspoň jeden kloub.');
 if(!r14Csrf)return say('Odesílat k přepočtu jde jen ze simulátoru na robot.caribhaus.com po přihlášení.');
 $('r14SendBtn').disabled=true;try{const d=await r14Api('odeslat',{upravy:r14Payload(),rychle:$('r14Fast').checked});say('Odesláno jako '+d.id+'. Plná kontrola trvá asi 10 minut, výsledek se ukáže níže.');r14List(true)}
 catch(err){say('Odeslání selhalo: '+err.message)}finally{$('r14SendBtn').disabled=false}}
function r14Esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c])}
async function r14List(force){const box=$('r14Remote');if(!r14Csrf){box.innerHTML='<p class="r14-note">Seznam přepočtů je dostupný v simulátoru na robot.caribhaus.com.</p>';return}
 if(!force&&!r14Open)return;let d;try{d=await r14Api('seznam')}catch(err){box.innerHTML='<p class="r14-stale">'+r14Esc(err.message)+'</p>';return}
 const L=d.prepocty||[];if(!L.length){box.innerHTML='<p class="r14-note">Zatím žádný přepočet.</p>';return}
 const stav=p=>p.stav!=='completed'?(p.stav==='ceka'?'čeká na spuštění':'počítá se…'):p.vysledek?(p.vysledek.proslo?'<b class="r14-ok">prošlo</b>':'<b class="r14-bad">neprošlo</b>'):(p.zaver==='success'?'hotovo':'<b class="r14-bad">chyba běhu</b>');
 box.innerHTML='<table class="r14-t"><thead><tr><th>Přepočet</th><th>Stav</th></tr></thead><tbody>'+L.map((p,i)=>{const v=p.vysledek,kl=Object.values(p.upravy||{}).map(e=>r14Esc(e.kloub)).join(', ');
  const det=v?('<br>servo max '+fmt(100*(v.statika.max||0),1)+' % · mezera '+fmt(v.mezery.dily_mm,1)+' mm · schod '+fmt(v.mezery.schod_mm,1)+' mm'+(v.kontroly.filter(k=>!k.ok).map(k=>'<br><span class="r14-bad">✗ '+r14Esc(k.nazev)+': '+r14Esc(k.hodnota)+'</span>').join(''))+((v.varovani||[]).map(t=>'<br><span class="r14-warn">⚠ '+r14Esc(t)+'</span>').join(''))):'';
  return '<tr><th>'+new Date(p.cas*1000).toLocaleString('cs-CZ',{day:'numeric',month:'numeric',hour:'2-digit',minute:'2-digit'})+(p.rychle?' · rychlá':'')+'<br><span class="r14-note">'+kl+'</span></th><td>'+stav(p)+det+
   '<br><button class="r14-link" data-load="'+i+'">Načíst úpravu</button>'+(p.odkaz?' · <a href="'+r14Esc(p.odkaz)+'" target="_blank" rel="noopener">protokol a stránka návrhu</a>':'')+'</td></tr>'}).join('')+'</tbody></table>';
 for(const b of box.querySelectorAll('[data-load]'))b.onclick=()=>{const p=L[+b.dataset.load];$('r14Json').value=JSON.stringify({upravy:p.upravy});r14Import()};
 clearTimeout(r14PollT);if(L.some(p=>p.stav!=='completed'))r14PollT=setTimeout(()=>r14List(),20000)}
// ---------- wiring ----------
for(let k=0;k<22;k++)$('r14Joint').add(new Option(data.joints[k],k));$('r14Joint').value=String(r14Sel);
const r14Pick=()=>{side=r14Sel;$('joint').value=String(side)};
$('r14Joint').onchange=()=>{r14Sel=+$('r14Joint').value;r14Pick();r14Controls();render()};
for(let a=0;a<3;a++){const h=src=>()=>{const e=r14Edits[r14Sel]||{d:[0,0,0]},d=e.d.slice();d[a]=cl(+$(src+a).value||0,-40,40);r14Set(r14Sel,{d})};$('r14R'+a).oninput=h('r14R');$('r14N'+a).onchange=h('r14N')}
$('r14Rot').oninput=()=>r14Set(r14Sel,{rot:+$('r14Rot').value});
$('r14Carry').onchange=()=>r14Set(r14Sel,{carry:$('r14Carry').checked});
$('r14ResetJoint').onclick=()=>r14Set(r14Sel,{d:[0,0,0],rot:0,carry:false});
$('r14ResetAll').onclick=()=>{r14Edits={};r14Ver++;r14Result=null;stop();r14Controls();render()};
$('r14RunBtn').onclick=r14Run;$('r14SendBtn').onclick=r14Send;$('r14ExportBtn').onclick=r14Export;$('r14ImportBtn').onclick=r14Import;
$('r14Toggle').onclick=()=>{r14Open=!r14Open;$('r14').classList.toggle('open',r14Open);if(r14Open)r14List(true);$('r14Toggle').setAttribute('aria-expanded',String(r14Open));r14Controls();render(true)};
$('r8Assembly').addEventListener('change',()=>setTimeout(r14Controls,0));
r14Ready=true;
// Revize z automatického přepočtu: stránka se otevře s úpravou, ze které vznikla
(()=>{const el=$('r14Start');if(!el)return;try{const o=JSON.parse(el.textContent),src=o.upravy||{};for(const [j,e] of Object.entries(src)){const d=(e.posun_mm||[0,0,0]).map(Number);r14Edits[+j]={d,carry:!!e.nese_dalsi_dily,rot:+e.natoceni_serva_deg||0}}
 for(const k of Object.keys(r14Edits))if(r14Zero(r14Edits[k]))delete r14Edits[k];$('r14Mirror').checked=false;r14Ver++;r14Open=true;$('r14').classList.add('open');$('r14Toggle').setAttribute('aria-expanded','true');
 const b=document.createElement('p');b.className='r14-verdict';b.innerHTML='<b>'+(o.revize||'Revize')+'</b> z automatického přepočtu: '+(o.proslo?'<b class="r14-ok">kontroly prošly</b>':'<b class="r14-bad">kontroly neprošly</b>')+'. Protokol je u běhu v GitHubu.';$('r14State').before(b)}catch(err){console.error('r14Start',err)}})();
r14Controls();
