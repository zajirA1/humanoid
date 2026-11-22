// R14 engine: kinematics with movable joint pivots, limb IK that keeps supports in place, minimax statics (LP).
// Pure functions, no DOM. Matrix convention = page convention (12 numbers: 3 columns + translation).
function r14Engine(K){
 const rad=Math.PI/180,G=9.80665,N=22,par=K.par,axes=K.axes,P0=K.P.map(p=>p.slice()),links0=K.links.map(l=>l.slice()),lim=K.lim,mu=K.mu||0.5;
 const anc=[];for(let i=0;i<23;i++){const a=[];let j=i;while(j<22){a.push(j);j=par[j]}anc.push(a)}
 const mirror=j=>j>=2&&j<12?j+10:j>=12?j-10:j;
 let P=P0.map(p=>p.slice()),E=P0.map(()=>[0,0,0]),links=links0.map(l=>l.slice()),edits={};
 const mtot=links0.reduce((s,l)=>s+l[0],0);
 function setEdits(ed){
  edits=ed||{};P=P0.map(p=>p.slice());E=P0.map(()=>[0,0,0]);links=links0.map(l=>l.slice());
  for(const k in edits){const j=+k,e=edits[k];if(!e)continue;const d=e.d||[0,0,0];
   for(let a=0;a<3;a++){P[j][a]+=d[a];if(e.carry)E[j][a]=d[a]}
   const L=par[j],m=K.servoKg[j];for(let a=0;a<3;a++)links[L][1+a]+=d[a]*m/links[L][0];}
  return {P,E,links};
 }
 function dir(t,p){return [t[0]*p[0]+t[3]*p[1]+t[6]*p[2],t[1]*p[0]+t[4]*p[1]+t[7]*p[2],t[2]*p[0]+t[5]*p[1]+t[8]*p[2]]}
 function pos(t,p){const d=dir(t,p);return [d[0]+t[9],d[1]+t[10],d[2]+t[11]]}
 function mat(a,b){const c0=dir(a,[b[0],b[1],b[2]]),c1=dir(a,[b[3],b[4],b[5]]),c2=dir(a,[b[6],b[7],b[8]]),t=pos(a,[b[9],b[10],b[11]]);return [...c0,...c1,...c2,...t]}
 function jointT(i,angle){const [x,y,z]=axes[i],s=Math.sin(angle*rad),c=Math.cos(angle*rad),v=1-c,t=[c+x*x*v,y*x*v+z*s,z*x*v-y*s,x*y*v-z*s,c+y*y*v,z*y*v+x*s,x*z*v+y*s,y*z*v-x*s,c+z*z*v,0,0,0];
  const p=P[i],r=dir(t,p),e=E[i],re=(e[0]||e[1]||e[2])?dir(t,e):[0,0,0];t[9]=p[0]-r[0]+re[0];t[10]=p[1]-r[1]+re[1];t[11]=p[2]-r[2]+re[2];return t}
 function fk(q,root){const w=[];w[22]=root;for(let i=0;i<22;i++)w[i]=mat(w[par[i]],jointT(i,q[i]));return w}
 const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
 function frames(w){const piv=[],ax=[];for(let i=0;i<22;i++){piv.push(pos(w[par[i]],P[i]));ax.push(dir(w[par[i]],axes[i]))}return {piv,ax}}
 function com(w){const c=[0,0,0];for(let i=0;i<23;i++){const p=pos(w[i],links[i].slice(1));for(let a=0;a<3;a++)c[a]+=links[i][0]*p[a]}return c.map(v=>v/mtot)}
 // ---------- dense simplex: min t  s.t. Aeq x = beq, +-(A x) - t <= -+b, x,t >= 0 ----------
 function minimax(Aeq,beq,A,b,nx){
  const U=A.length,m=6+2*U,ct=nx,cs=nx+1,ca=cs+2*U,W=ca+6+1,rhs=W-1,T=[];
  for(let r=0;r<6;r++){const row=new Float64Array(W);let s=beq[r]<0?-1:1;for(let c=0;c<nx;c++)row[c]=s*Aeq[r][c];row[ca+r]=1;row[rhs]=s*beq[r];T.push(row)}
  for(let k=0;k<2*U;k++){const row=new Float64Array(W),u=k<U?k:k-U,s=k<U?1:-1;for(let c=0;c<nx;c++)row[c]=s*A[u][c];row[ct]=-1;row[cs+k]=1;row[rhs]=-s*b[u];T.push(row)}
  const basis=new Int32Array(m);for(let r=0;r<6;r++)basis[r]=ca+r;for(let k=0;k<2*U;k++)basis[6+k]=cs+k;
  let worst=-1,wv=-1e-12;for(let k=0;k<2*U;k++)if(T[6+k][rhs]<wv){wv=T[6+k][rhs];worst=6+k}
  const pivot=(pr,pc)=>{const R=T[pr],pv=R[pc];for(let c=0;c<W;c++)R[c]/=pv;for(let r=0;r<T.length;r++){if(r===pr)continue;const f=T[r][pc];if(f!==0){const X=T[r];for(let c=0;c<W;c++)X[c]-=f*R[c];X[pc]=0}}basis[pr]=pc};
  if(worst>=0)pivot(worst,ct);
  for(let r=0;r<m;r++)if(T[r][rhs]<0)T[r][rhs]=0;
  const run=(z,allow)=>{let it=0,degen=0;for(;;){if(++it>20000)return false;let pc=-1,best=-1e-9;
    if(degen>40){for(let c=0;c<allow;c++)if(z[c]<-1e-9){pc=c;break}}else for(let c=0;c<allow;c++)if(z[c]<best){best=z[c];pc=c}
    if(pc<0)return true;let pr=-1,br=Infinity;
    for(let r=0;r<m;r++){const a=T[r][pc];if(a>1e-9){const q=T[r][rhs]/a;if(q<br-1e-12||(q<br+1e-12&&pr>=0&&basis[r]<basis[pr])){br=q;pr=r}}}
    if(pr<0)return false;degen=br<1e-12?degen+1:0;
    const R=T[pr],pv=R[pc];for(let c=0;c<W;c++)R[c]/=pv;
    for(let r=0;r<m;r++){if(r===pr)continue;const f=T[r][pc];if(f!==0){const X=T[r];for(let c=0;c<W;c++)X[c]-=f*R[c];X[pc]=0}}
    const f=z[pc];if(f!==0){for(let c=0;c<W;c++)z[c]-=f*R[c];z[pc]=0}basis[pr]=pc}};
  // phase 1
  const z1=new Float64Array(W);for(let r=0;r<6;r++)for(let c=0;c<W;c++)if(c<ca||c===rhs)z1[c]-=T[r][c];
  if(!run(z1,ca))return null;if(-z1[rhs]>1e-6)return null;
  for(let r=0;r<m;r++)if(basis[r]>=ca){let pc=-1,bv=1e-7;for(let c=0;c<ca;c++)if(Math.abs(T[r][c])>bv){bv=Math.abs(T[r][c]);pc=c}
    if(pc>=0){const R=T[r],pv=R[pc];for(let c=0;c<W;c++)R[c]/=pv;for(let q=0;q<m;q++){if(q===r)continue;const f=T[q][pc];if(f!==0){const X=T[q];for(let c=0;c<W;c++)X[c]-=f*R[c];X[pc]=0}}basis[r]=pc}}
  // phase 2
  const z2=new Float64Array(W);z2[ct]=1;for(let r=0;r<m;r++)if(basis[r]===ct){for(let c=0;c<W;c++)z2[c]-=T[r][c];z2[ct]=0}
  if(!run(z2,ca))return null;
  const x=new Float64Array(nx+1);for(let r=0;r<m;r++)if(basis[r]<=ct)x[basis[r]]=T[r][rhs];return x;
 }
 const cone=[];for(let k=0;k<8;k++){const a=k*Math.PI/4;cone.push([mu*Math.cos(a),mu*Math.sin(a),1])}
 const use=[];for(let j=0;j<22;j++)if(j!==11&&j!==21)use.push(j);
 function gravTau(w,fr){const tau=new Array(22).fill(0);for(let i=0;i<22;i++){const c=pos(w[i],links[i].slice(1)),F=[0,0,-links[i][0]*G];for(const j of anc[i]){const r=[c[0]-fr.piv[j][0],c[1]-fr.piv[j][1],c[2]-fr.piv[j][2]],x=cross(r,F);tau[j]-=1e-3*(fr.ax[j][0]*x[0]+fr.ax[j][1]*x[1]+fr.ax[j][2]*x[2])}}return tau}
 // contacts: flat [link,x,y,z,...] in link coordinates
 function statics(w,flat){
  const n=flat.length/4;if(!n)return null;const fr=frames(w),c=com(w),tg=gravTau(w,fr),nx=n*8;
  const Aeq=[];for(let r=0;r<6;r++)Aeq.push(new Float64Array(nx));const Tm=[];for(let j=0;j<22;j++)Tm.push(new Float64Array(nx));const pts=[];
  for(let i=0;i<n;i++){const link=flat[4*i],p=pos(w[link],[flat[4*i+1],flat[4*i+2],flat[4*i+3]]);pts.push(p);
   for(const j of anc[link]){const a=cross(fr.ax[j],[p[0]-fr.piv[j][0],p[1]-fr.piv[j][1],p[2]-fr.piv[j][2]]);for(let k=0;k<8;k++)Tm[j][i*8+k]=-1e-3*(cone[k][0]*a[0]+cone[k][1]*a[1]+cone[k][2]*a[2])}
   const r=[(p[0]-c[0])*1e-3,(p[1]-c[1])*1e-3,(p[2]-c[2])*1e-3];
   for(let k=0;k<8;k++){const g=cone[k],x=cross(r,g);for(let a=0;a<3;a++){Aeq[a][i*8+k]=g[a];Aeq[3+a][i*8+k]=x[a]}}}
  const A=use.map(j=>{const row=new Float64Array(nx);for(let c2=0;c2<nx;c2++)row[c2]=Tm[j][c2]/lim[j];return row}),b=use.map(j=>tg[j]/lim[j]);
  const x=minimax(Aeq,[0,0,mtot*G,0,0,0],A,b,nx);if(!x)return null;
  const tau=tg.slice();for(let j=0;j<22;j++){let s=0;for(let c2=0;c2<nx;c2++)s+=Tm[j][c2]*x[c2];tau[j]+=s}
  const ratio=tau.map((v,j)=>j===11||j===21?0:Math.abs(v)/lim[j]);let jmax=0;for(let j=1;j<22;j++)if(ratio[j]>ratio[jmax])jmax=j;
  const fz={};for(let i=0;i<n;i++){let s=0;for(let k=0;k<8;k++)s+=x[i*8+k];fz[flat[4*i]]=(fz[flat[4*i]]||0)+s}
  return {s:ratio[jmax],jmax,tau,ratio,fz,com:c};
 }
 // ---------- limb IK: keep supports where they were ----------
 function solveSmall(A,b){const n=b.length;for(let i=0;i<n;i++){let p=i;for(let r=i+1;r<n;r++)if(Math.abs(A[r][i])>Math.abs(A[p][i]))p=r;[A[i],A[p]]=[A[p],A[i]];[b[i],b[p]]=[b[p],b[i]];const d=A[i][i]||1e-12;for(let r=i+1;r<n;r++){const f=A[r][i]/d;if(f){for(let c=i;c<n;c++)A[r][c]-=f*A[i][c];b[r]-=f*b[i]}}}
  const x=new Array(n);for(let i=n-1;i>=0;i--){let s=b[i];for(let c=i+1;c<n;c++)s-=A[i][c]*x[c];x[i]=s/(A[i][i]||1e-12)}return x}
 const LIMBS=[{foot:7,shin:5,leg:[2,3,4,5,6,7],arm:[8,9,10],hand:10,sx:1},{foot:17,shin:15,leg:[12,13,14,15,16,17],arm:[18,19,20],hand:20,sx:-1}];
 const refs=(link,sx)=>link===7||link===17?[[sx*54,1,30],[sx*54+60,1,30],[sx*54,61,30]]:link===5||link===15?[[sx*54,-24,103],[sx*54+60,-24,103],[sx*54,-24,163]]:[[sx*146,-12,205]];
 function rodrigues(o){const th=Math.hypot(o[0],o[1],o[2]);if(th<1e-12)return [1,0,0,0,1,0,0,0,1];const x=o[0]/th,y=o[1]/th,z=o[2]/th,s=Math.sin(th),c=Math.cos(th),v=1-c;return [c+x*x*v,y*x*v+z*s,z*x*v-y*s,x*y*v-z*s,c+y*y*v,z*y*v+x*s,x*z*v+y*s,y*z*v-x*s,c+z*z*v]}
 const VARJ=[2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20],VIDX={};VARJ.forEach((j,i)=>VIDX[j]=6+i);const NV=24,PELV=[0,1,324];
 // whole-body least squares: supports stay where they were, torso and free limbs give way
 function retarget(q0,root0,w0,flat,off,shift,liftdz){const q=q0.slice();let root=root0.slice();const on=new Set();for(let i=0;i<flat.length;i+=4)on.add(flat[i]);
  const tasks=[];
  for(const L of LIMBS){const shinMode=on.has(L.shin)&&!on.has(L.foot);
   const add=(link,wt,c)=>{for(const p of refs(link,L.sx)){const t=pos(w0[link],p);
     if(shift&&shift[link]){t[0]+=shift[link][0];t[1]+=shift[link][1];t[2]+=shift[link][2]||0}
     // přizpůsobení výšce schodu: body nad schodem (y<-5 mm, z>100 mm) o liftdz výš, v pásu ±5 mm u hrany plynule
     if(liftdz){const nad=t[1]<-5?1:t[1]>5?0:(5-t[1])/10;if(t[2]>100)t[2]+=liftdz*nad}
     tasks.push({link,p,t,wt,c})}};
   if(shinMode){add(L.shin,1,true);add(L.foot,0.05,false)}else add(L.foot,on.has(L.foot)?1:0.15,on.has(L.foot));
   add(L.hand,on.has(L.hand)?1:0.15,on.has(L.hand))}
  const lt=3e-4,lr=30,lq=3,du=[0,0,0],dw=[0,0,0];let drift=0;
  for(let it=0;it<30;it++){const w=fk(q,root),fr=frames(w),c=pos(root,PELV),A=[],b=new Array(NV).fill(0);for(let i=0;i<NV;i++)A.push(new Array(NV).fill(0));drift=0;
   for(const T of tasks){const pw=pos(w[T.link],T.p),r=[T.t[0]-pw[0],T.t[1]-pw[1],T.t[2]-pw[2]];if(T.c)drift=Math.max(drift,Math.hypot(r[0],r[1],r[2]));
    const cols=[],idx=[];for(let a=0;a<3;a++){const u=[0,0,0];u[a]=1;cols.push(u);idx.push(a)}
    const rc=[pw[0]-c[0],pw[1]-c[1],pw[2]-c[2]];for(let a=0;a<3;a++){const u=[0,0,0];u[a]=1;cols.push(cross(u,rc));idx.push(3+a)}
    for(const j of anc[T.link])if(VIDX[j]!==undefined){cols.push(cross(fr.ax[j],[pw[0]-fr.piv[j][0],pw[1]-fr.piv[j][1],pw[2]-fr.piv[j][2]]));idx.push(VIDX[j])}
    const ww=T.wt*T.wt;for(let i=0;i<cols.length;i++){const ci=cols[i];b[idx[i]]+=ww*(ci[0]*r[0]+ci[1]*r[1]+ci[2]*r[2]);for(let k=0;k<cols.length;k++){const ck=cols[k];A[idx[i]][idx[k]]+=ww*(ci[0]*ck[0]+ci[1]*ck[1]+ci[2]*ck[2])}}}
   for(let a=0;a<3;a++){const k=off?0.05:lt,tg=off?off[a]:0;A[a][a]+=k;b[a]-=k*(du[a]-tg);A[3+a][3+a]+=lr;b[3+a]-=lr*dw[a]}
   VARJ.forEach((j,i)=>{A[6+i][6+i]+=lq;b[6+i]-=lq*(q[j]-q0[j])*rad});
   for(let i=0;i<NV;i++)A[i][i]+=1e-3;
   const x=solveSmall(A,b);let big=0;for(let i=3;i<NV;i++)big=Math.max(big,Math.abs(x[i]));const sc=big>0.3?0.3/big:1;let step=0;for(let i=0;i<NV;i++){x[i]*=sc;step=Math.max(step,Math.abs(x[i])*(i<3?0.01:1))}
   const R=rodrigues([x[3],x[4],x[5]]),Rm=[...R,0,0,0],nr=mat(Rm,[...root.slice(0,9),0,0,0]),tc=[root[9]-c[0],root[10]-c[1],root[11]-c[2]],rtc=dir(Rm,tc);
   root=[...nr.slice(0,9),c[0]+rtc[0]+x[0],c[1]+rtc[1]+x[1],c[2]+rtc[2]+x[2]];
   for(let a=0;a<3;a++){du[a]+=x[a];dw[a]+=x[3+a]}VARJ.forEach((j,i)=>q[j]+=x[6+i]/rad);
   if(step<1e-7)break}
  return {q,root,drift,shift:Math.hypot(du[0],du[1],du[2])}}
 // ---------- approximate clearances from sampled surface points ----------
 let CL=null;
 function setClouds(clouds,pairs){CL={pairs,c:clouds.map(c=>({link:c.link,kind:c.kind,n:c.tag.length,p0:Float64Array.from(c.p),tag:c.tag,p:Float64Array.from(c.p),w:new Float64Array(c.p.length),ctr:[0,0,0],r:0,cw:[0,0,0]}))};prepClouds(false)}
 function prepClouds(edited){if(!CL)return;for(const c of CL.c){const m=[0,0,0];for(let i=0;i<c.n;i++){const j=c.tag[i];let s=[0,0,0];if(edited&&j>=0&&edits[j]){const e=edits[j],d=e.d||[0,0,0];s=(e.carry&&c.link===j)?[0,0,0]:d}
    for(let a=0;a<3;a++){c.p[3*i+a]=c.p0[3*i+a]+s[a];m[a]+=c.p[3*i+a]/c.n}}
   let r=0;for(let i=0;i<c.n;i++)r=Math.max(r,Math.hypot(c.p[3*i]-m[0],c.p[3*i+1]-m[1],c.p[3*i+2]-m[2]));c.ctr=m;c.r=r}}
 function clearance(w,exbits){if(!CL)return null;
  for(const c of CL.c){const t=w[c.link],p=c.p,o=c.w;for(let i=0;i<c.n;i++){const x=p[3*i],y=p[3*i+1],z=p[3*i+2];o[3*i]=t[0]*x+t[3]*y+t[6]*z+t[9];o[3*i+1]=t[1]*x+t[4]*y+t[7]*z+t[10];o[3*i+2]=t[2]*x+t[5]*y+t[8]*z+t[11]}c.cw=pos(t,c.ctr)}
  let best=40,b2=best*best;
  for(const [ia,ib] of CL.pairs){const a=CL.c[ia],b=CL.c[ib],dc=Math.hypot(a.cw[0]-b.cw[0],a.cw[1]-b.cw[1],a.cw[2]-b.cw[2]);if(dc-a.r-b.r>=best)continue;
   const A=a.w,B=b.w,bx=b.cw[0],by=b.cw[1],bz=b.cw[2],lim=b.r+best;
   for(let i=0;i<a.n;i++){const x=A[3*i],y=A[3*i+1],z=A[3*i+2],ex=x-bx,ey=y-by,ez=z-bz;if(ex*ex+ey*ey+ez*ez>=(b.r+best)*(b.r+best))continue;
    for(let k=0;k<b.n;k++){const dx=x-B[3*k],dy=y-B[3*k+1],dz=z-B[3*k+2],d=dx*dx+dy*dy+dz*dz;if(d<b2){b2=d;best=Math.sqrt(d)}}}}
  let env=60;
  for(const c of CL.c){if((exbits&1&&c.link===7&&c.kind==='body')||(exbits&2&&c.link===17&&c.kind==='body')||(exbits&4&&c.link===5&&c.kind==='sleeve')||(exbits&8&&c.link===15&&c.kind==='sleeve'))continue;
   const W=c.w;for(let i=0;i<c.n;i++){const x=W[3*i],y=W[3*i+1],z=W[3*i+2];if(z<env)env=z;
    const dx=Math.max(Math.abs(x)-330,0),dy=Math.max(y,-280-y,0),dz=Math.max(z-210,0);let d;if(dx||dy||dz)d=Math.hypot(dx,dy,dz);else d=-Math.min(-y,y+280,210-z);if(d<env)env=d}}
  return {self:best,env}}
 function fk0(q,root){const sP=P,sE=E;P=P0;E=P0.map(()=>[0,0,0]);const w=fk(q,root);P=sP;E=sE;return w}
 return {setEdits,setClouds,prepClouds,clearance,fk,fk0,frames,com,statics,retarget,jointT,mirror,anc,pos,dir,mat,get P(){return P},get E(){return E},get links(){return links},P0,links0,mtot};
}
if(typeof module!=='undefined')module.exports=r14Engine;
