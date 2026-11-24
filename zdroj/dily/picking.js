// Ortografický paprsek má stejný směr a měřítko jako hlavní vykreslovač.
// Obálka vyřadí vzdálené objekty, o zásahu rozhodne nejbližší skutečný trojúhelník.
function r16PickSurface(commands,getMesh,camera,x,y) {
  const {target,right,up,look,span,width,height}=camera, scale=height/span;
  const px=(x-width/2)/scale, py=(height/2-y)/scale;
  const dot3=(v,w)=>v[0]*w[0]+v[1]*w[1]+v[2]*w[2];
  let front=-Infinity, winner=null;
  for(const command of commands){
    const [key,m]=command, mesh=getMesh(key);
    if(!mesh)continue;
    const {v,f}=mesh;
    if(!mesh.pickBounds){
      const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
      for(let i=0;i<v.length;i++) {const k=i%3;lo[k]=Math.min(lo[k],v[i]);hi[k]=Math.max(hi[k],v[i]);}
      mesh.pickBounds={center:lo.map((a,i)=>(a+hi[i])/2),half:lo.map((a,i)=>(hi[i]-a)/2)};
    }
    const axis=[m.slice(0,3),m.slice(3,6),m.slice(6,9)], offset=m.slice(9,12).map((a,i)=>a-target[i]);
    const R=axis.map(a=>dot3(a,right)), U=axis.map(a=>dot3(a,up)), D=axis.map(a=>dot3(a,look));
    const ox=dot3(offset,right)-px, oy=dot3(offset,up)-py, oz=dot3(offset,look);
    const {center,half}=mesh.pickBounds;
    const radius=a=>Math.abs(a[0])*half[0]+Math.abs(a[1])*half[1]+Math.abs(a[2])*half[2];
    if(Math.abs(ox+dot3(center,R))>radius(R)+1e-7||Math.abs(oy+dot3(center,U))>radius(U)+1e-7||oz+dot3(center,D)+radius(D)<front)continue;
    const pts=new Float64Array(v.length);
    for(let i=0;i<v.length;i+=3){
      const a=v[i],b=v[i+1],c=v[i+2];
      pts[i]=R[0]*a+R[1]*b+R[2]*c+ox;
      pts[i+1]=U[0]*a+U[1]*b+U[2]*c+oy;
      pts[i+2]=D[0]*a+D[1]*b+D[2]*c+oz;
    }
    for(let i=0;i<f.length;i+=3){
      const a=f[i]*3,b=f[i+1]*3,c=f[i+2]*3;
      const ax=pts[a],ay=pts[a+1],bx=pts[b]-ax,by=pts[b+1]-ay,cx=pts[c]-ax,cy=pts[c+1]-ay;
      const det=bx*cy-by*cx;if(Math.abs(det)<1e-10)continue;
      const s=(-ax*cy+ay*cx)/det,t=(ax*by-ay*bx)/det;
      if(s < -1e-8 || t < -1e-8 || s+t > 1+1e-8)continue;
      const depth=pts[a+2]+s*(pts[b+2]-pts[a+2])+t*(pts[c+2]-pts[a+2]);
      if(depth>front+1e-7){front=depth;winner=command[3]?command:null;}
    }
  }
  return winner;
}
