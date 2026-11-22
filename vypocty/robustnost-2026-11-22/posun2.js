// node posun2.js model.json pozadavky.json vystup.json ; požadavek {i, off:[x,y,z], shift:{10:[dx,dy,dz],20:[...]}, plne:bool}
const fs=require('fs'),eng=require('/home/claude/humanoid/kontrola/r14engine.js');
const [,,mp,rq,out]=process.argv,M=JSON.parse(fs.readFileSync(mp)),R=JSON.parse(fs.readFileSync(rq));
const E=eng({par:M.PAR,axes:M.AX,P:M.P,links:M.LINKS,lim:M.LIM,mu:0.5,servoKg:M.servoKg});E.setEdits({});
const E02=eng({par:M.PAR,axes:M.AX,P:M.P,links:M.LINKS,lim:M.LIM,mu:0.02,servoKg:M.servoKg});E02.setEdits({});
const res=R.map(({i,off,shift,plne,lift})=>{const q0=M.q[i],rt0=M.rt[i],fl=M.contacts[i],a=E.retarget(q0,rt0,E.fk0(q0,rt0),fl,off||[0,0,0],shift,lift||0),s=E.statics(E.fk(a.q,a.root),fl);
 const w=E.fk(a.q,a.root),f=plne?E02.statics(w,fl):null;
 return plne?{i,q:a.q,rt:a.root,drift:a.drift,s50:s?s.s:null,ff:f?f.tau:null,com:s?s.com:null}:{i,q:a.q,rt:a.root,drift:a.drift,s50:s?s.s:null}});
fs.writeFileSync(out,JSON.stringify(res));
