const eng=require('../zdroj/uprava-kloubu/r14engine.js'),D=require('../zdroj/uprava-kloubu/r14page.json'),D0=require('./r14data.json'),K=require('./kin.json');
const e=eng({par:K.par,axes:K.axes,P:D.P,links:D.links,lim:D.lim,mu:D.mu,servoKg:D.servoKg});e.setClouds(D.clouds,D.pairs);
let t0=Date.now();const bs=[],be=[];for(let i=0;i<D0.q.length;i++){const w=e.fk(D0.q[i],D0.rt[i]),c=e.clearance(w,D.ex[i]);bs.push(c.self-D.selfBase[i]);be.push(c.env-D.envBase[i])}
const st=a=>{const s=a.slice().sort((x,y)=>x-y);return [s[0],s[s.length>>1],s[s.length-1]].map(v=>v.toFixed(2))};
console.log('ms',Date.now()-t0,'self bias min/med/max',st(bs),'env bias',st(be));
