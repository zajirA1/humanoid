const eng=require('../zdroj/uprava-kloubu/r14engine.js'),D=require('./r14data.json'),K=require('./kin.json'),fs=require('fs');
const e=eng({par:K.par,axes:K.axes,P:D.P,links:D.links,lim:D.lim,mu:D.mu,servoKg:D.servoKg});
const ed={5:{d:[0,3,8]},15:{d:[0,3,8]},4:{d:[0,0,-12],carry:true},14:{d:[0,0,-12],carry:true},8:{d:[4,0,6]},18:{d:[-4,0,6]}};
e.setEdits(ed);let t0=Date.now();const out=[];let sh=0,peak=0,pk=0,bad=0,dr=0;
for(let i=0;i<D.q.length;i++){const w0=e.fk0(D.q[i],D.rt[i]),r=e.retarget(D.q[i],D.rt[i],w0,D.contacts[i]),w=e.fk(r.q,r.root),s=e.statics(w,D.contacts[i]);
 dr=Math.max(dr,r.drift);sh=Math.max(sh,r.shift);if(!s){bad++;out.push([r.q,null,r.root]);continue}if(s.s>peak){peak=s.s;pk=i}out.push([r.q,s.s,r.root])}
console.log('peak',peak,pk,'bad',bad,'drift',dr,'rootshift',sh,'ms',Date.now()-t0);
fs.writeFileSync('t_edit.json',JSON.stringify({ed,out}));
