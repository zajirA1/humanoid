// Statika hotového pohybu pro stránku: node statika.js <model.json> <pohyb.json> <výstup.json>
// pro každou polohu: využití serva (tření 0,5), nejzatíženější kloub, momenty, svislé síly po článcích opor, těžiště
const fs=require('fs'),path=require('path'),eng=require(path.join(__dirname,'../../kontrola/r14engine.js'));
const [,,mp,pp,out]=process.argv,M=JSON.parse(fs.readFileSync(mp)),Q=JSON.parse(fs.readFileSync(pp));
const E=eng({par:M.PAR,axes:M.AX,P:M.P,links:M.LINKS,lim:M.LIM,mu:0.5,servoKg:M.servoKg});E.setEdits({});
const r=(x,n=5)=>Math.round(x*10**n)/10**n,res=[];
for(let i=0;i<Q.q.length;i++){const fl=M.contacts[i],w=E.fk(Q.q[i],Q.rt[i]),s=E.statics(w,fl);
 if(!s){res.push(null);continue}
 res.push({s:r(s.s),j:s.jmax,tau:s.tau.map(x=>r(x)),F:Object.fromEntries(Object.entries(s.fz).map(([k,v])=>[k,r(v,3)])),com:s.com.map(x=>r(x,3))})}
fs.writeFileSync(out,JSON.stringify(res));console.log('statika',res.length,'poloh, bez rovnováhy',res.filter(x=>!x).length);
