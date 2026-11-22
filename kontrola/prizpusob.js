// Přizpůsobení přelezu upravené geometrii a statika (stejné jádro jako v simulátoru).
// node prizpusob.js <model.json> <upravy.json> <vystup.json>
const fs=require('fs'),eng=require('./r14engine.js');
const [,,mp,up,out]=process.argv,M=JSON.parse(fs.readFileSync(mp)),U=JSON.parse(fs.readFileSync(up));
const ed={};for(const [j,e] of Object.entries(U.upravy||{})){const d=(e.posun_mm||e.d||[0,0,0]).map(Number);if(d.some(Number.isNaN)||d.some(v=>Math.abs(v)>40))throw Error('Neplatný posun u kloubu '+j);ed[+j]={d,carry:!!(e.nese_dalsi_dily??e.carry),rot:+(e.natoceni_serva_deg??e.rot)||0}}
const mk=mu=>{const e=eng({par:M.PAR,axes:M.AX,P:M.P,links:M.LINKS,lim:M.LIM,mu,servoKg:M.servoKg});e.setEdits(ed);return e};
const E5=mk(0.5),E4=mk(0.4),E3=mk(0.3),E02=mk(0.02),r=x=>x===null?null:Math.round(x*1e5)/1e5;
const res={edits:ed,P:E5.P,E:E5.E,links:E5.links,frames:[]};const t0=Date.now();
// volitelně 4. argument: hotové polohy {q,rt} (po doladění) – bez přizpůsobení, jen statika
const FIX=process.argv[5]?JSON.parse(fs.readFileSync(process.argv[5])):null;
// přizpůsobení výšce schodu (robot ji změří dotykem dlaní): U.vyska_dh = o kolik je schod vyšší než 210 mm, od M.vyska_od_s s náběhem
const DH=+(U.vyska_dh||0),OD=(M.vyska_od_s??30)*6,NAB=Math.max(1,(M.vyska_nabeh_s??2)*6);
function vyska(i,w0,fl){if(!DH||i<OD)return [null,0];const lw=Math.min(1,(i-OD)/NAB);let on=0,tot=0;
 for(let k=0;k<fl.length;k+=4){const p=E5.pos(w0[fl[k]],[fl[k+1],fl[k+2],fl[k+3]]);tot++;if(p[2]>100)on++}
 return [[0,0,tot?DH*lw*on/tot:0],DH*lw]}
for(let i=0;i<M.q.length;i++){const q0=M.q[i],rt0=M.rt[i],fl=M.contacts[i],w0=E5.fk0(q0,rt0),[vo,vl]=vyska(i,w0,fl),a=FIX?{q:FIX.q[i],root:FIX.rt[i],drift:FIX.drift[i],shift:FIX.shift[i]}:E5.retarget(q0,rt0,w0,fl,vo||undefined,undefined,vl),w=E5.fk(a.q,a.root);
 const s5=E5.statics(w,fl),s4=E4.statics(w,fl),s3=E3.statics(w,fl),s02=E02.statics(w,fl);
 res.frames.push({q:a.q.map(v=>Math.round(v*1e6)/1e6),rt:a.root.map(v=>Math.round(v*1e9)/1e9),drift:r(a.drift),shift:r(a.shift),
  s50:s5?r(s5.s):null,j50:s5?s5.jmax:-1,tau:s5?s5.tau.map(r):null,s40:s4?r(s4.s):null,s30:s3?r(s3.s):null,ff:s02?s02.tau.map(r):null,com:s5?s5.com.map(r):null})}
res.ms=Date.now()-t0;fs.writeFileSync(out,JSON.stringify(res));console.log('přizpůsobeno',M.q.length,'poloh za',res.ms,'ms');
