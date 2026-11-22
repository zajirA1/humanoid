const eng=require('../zdroj/uprava-kloubu/r14engine.js'),D=require('./r14data.json'),K=require('./kin.json');
const e=eng({par:K.par,axes:K.axes,P:D.P,links:D.links,lim:D.lim,mu:D.mu,servoKg:D.servoKg});
let t0=Date.now(),maxd=0,bad=0,peak=0,pk=-1,wd=-1;
for(let i=0;i<D.q.length;i++){const w=e.fk(D.q[i],D.rt[i]),r=e.statics(w,D.contacts[i]);if(!r){bad++;continue}
 const d=Math.abs(r.s-D.ref[i][0]);if(d>maxd){maxd=d;wd=i}if(r.s>peak){peak=r.s;pk=i}}
console.log('frames',D.q.length,'infeasible',bad,'max |ds|',maxd,'at',wd,'peak',peak,pk,'ms',Date.now()-t0);
// IK with zero edits must not move
let mq=0;for(let i=0;i<D.q.length;i+=37){const w0=e.fk0(D.q[i],D.rt[i]),r=e.retarget(D.q[i],D.rt[i],w0,D.contacts[i]);mq=Math.max(mq,...r.q.map((v,j)=>Math.abs(v-D.q[i][j])),r.drift)}
console.log('zero-edit IK change',mq);
if(bad||maxd>1e-4||Math.abs(peak-0.70278)>1e-4||mq>1e-9){console.error('KONTROLA SELHALA');process.exit(1)}
console.log('KONTROLA OK');
