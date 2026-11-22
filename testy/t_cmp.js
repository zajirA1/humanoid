const eng=require('../zdroj/uprava-kloubu/r14engine.js'),D=require('./r14data.json'),K=require('./kin.json');
const e=eng({par:K.par,axes:K.axes,P:D.P,links:D.links,lim:D.lim,mu:D.mu,servoKg:D.servoKg});
e.setEdits({5:{d:[0,3,8]},15:{d:[0,3,8]}});let peak=0,pk=0,bad=0,dr=0;
for(let i=0;i<D.q.length;i++){const r=e.retarget(D.q[i],D.rt[i],e.fk0(D.q[i],D.rt[i]),D.contacts[i]),s=e.statics(e.fk(r.q,r.root),D.contacts[i]);dr=Math.max(dr,r.drift);if(!s){bad++;continue}if(s.s>peak){peak=s.s;pk=i}}
console.log('node: peak',peak,pk,'bad',bad,'drift',dr);
