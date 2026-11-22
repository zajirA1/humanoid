// dávkové přizpůsobení s posunem trupu: node posun.js model.json pozadavky.json vystup.json
const fs=require('fs'),eng=require('/home/claude/humanoid/kontrola/r14engine.js');
const [,,mp,rq,out]=process.argv,M=JSON.parse(fs.readFileSync(mp)),R=JSON.parse(fs.readFileSync(rq));
const E=eng({par:M.PAR,axes:M.AX,P:M.P,links:M.LINKS,lim:M.LIM,mu:0.5,servoKg:M.servoKg});E.setEdits({});
const res=R.map(({i,off})=>{const q0=M.q[i],rt0=M.rt[i],fl=M.contacts[i],a=E.retarget(q0,rt0,E.fk0(q0,rt0),fl,off),s=E.statics(E.fk(a.q,a.root),fl);
 return {i,off,q:a.q,rt:a.root,drift:a.drift,shift:a.shift,s50:s?s.s:null}});
fs.writeFileSync(out,JSON.stringify(res));
