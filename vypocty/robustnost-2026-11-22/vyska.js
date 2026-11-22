// Přelez přizpůsobený výšce schodu: node vyska.js model.json dh vystup.json  (dh = o kolik je schod vyšší než 210 mm)
const fs=require('fs'),eng=require('/tmp/plan/eng_lift.js');
const [,,mp,dhs,out]=process.argv,M=JSON.parse(fs.readFileSync(mp)),dh=+dhs;
const E=eng({par:M.PAR,axes:M.AX,P:M.P,links:M.LINKS,lim:M.LIM,mu:0.5,servoKg:M.servoKg});E.setEdits({});
// body nad schodem (y < 0 a výš než polovina schodu) se zvednou o dh, body před hranou plynule (5 mm pás)
const lift=t=>{const nad=t[1]<-5?1:t[1]>5?0:(5-t[1])/10;return t[2]>100?dh*nad:0};
const res={q:[],rt:[],drift:[],shift:[]};
for(let i=0;i<M.q.length;i++){const q0=M.q[i],rt0=M.rt[i],fl=M.contacts[i],w0=E.fk0(q0,rt0);
 // podíl opor na schodu → zvednutí pánve
 let on=0,tot=0;for(let k=0;k<fl.length;k+=4){const p=E.pos(w0[fl[k]],[fl[k+1],fl[k+2],fl[k+3]]);tot++;if(p[2]>100)on++}
 const a=E.retarget(q0,rt0,w0,fl,[0,0,tot?dh*on/tot:0],lift);
 res.q.push(a.q);res.rt.push(a.root);res.drift.push(a.drift);res.shift.push(a.shift)}
fs.writeFileSync(out,JSON.stringify(res));
