const raw=Uint8Array.from(atob($('model').textContent.trim()),c=>c.charCodeAt(0)),dview=new DataView(raw.buffer),jl=dview.getUint32(12,true);
const doc=JSON.parse(new TextDecoder().decode(raw.subarray(20,20+jl))),binStart=28+jl,ns=doc.nodes;
function acc(k){const a=doc.accessors[k],v=doc.bufferViews[a.bufferView],n={VEC3:3,VEC4:4,SCALAR:1}[a.type];return new Float32Array(raw.buffer,binStart+(v.byteOffset||0)+(a.byteOffset||0),a.count*n);}
const mm=(a,b)=>{let c=new Float32Array(16);for(let j=0;j<4;j++)for(let i=0;i<4;i++)for(let k=0;k<4;k++)c[j*4+i]+=a[k*4+i]*b[j*4+k];return c;};
function matrix(p,r,s){const [x,y,z,w]=r||[0,0,0,1],[a,b,c]=s||[1,1,1];
 return new Float32Array([(1-2*y*y-2*z*z)*a,(2*x*y+2*w*z)*a,(2*x*z-2*w*y)*a,0,(2*x*y-2*w*z)*b,(1-2*x*x-2*z*z)*b,(2*y*z+2*w*x)*b,0,(2*x*z+2*w*y)*c,(2*y*z-2*w*x)*c,(1-2*x*x-2*y*y)*c,0,...p,1]);}
const quat=(axis,degrees)=>{const v=degrees*rg/2;return [...mul(axis,Math.sin(v)),Math.cos(v)];};
const transform=(m,v)=>[0,1,2].map(i=>m[i]*v[0]+m[4+i]*v[1]+m[8+i]*v[2]+m[12+i]);
const identity=matrix([0,0,0]);
let phi=.93,el=.38,dist=1.22,target=[.045,.221,.030],vp,eye,basis,aspect;
function camera(){
 eye=add(target,[Math.cos(phi)*Math.cos(el)*dist,Math.sin(el)*dist,Math.sin(phi)*Math.cos(el)*dist]);
 const f=unit(sub(target,eye)),r=unit(cross(f,[0,1,0])),u=cross(r,f);basis=[r,u,f];
 const cam=new Float32Array([r[0],u[0],-f[0],0,r[1],u[1],-f[1],0,r[2],u[2],-f[2],0,-dot(r,eye),-dot(u,eye),dot(f,eye),1]);
 const t=Math.min(1,aspect/.90)/Math.tan(32*rg/2),n=.02,z=8;vp=mm(new Float32Array([t/aspect,0,0,0,0,t,0,0,0,0,-(z+n)/(z-n),-1,0,0,-2*z*n/(z-n),0]),cam);
}
// Souřadnice uzlů GLB jsou v metrech. Čtyřčlen zachovává vodorovné čelisti.
const v2Nodes = new Map(ns.map((node,i) => [node.name,i]));
function world(q,obj) {
    const [yaw,s,f,gap]=q;
    const special = new Map();
    function rotate(name,axis,angle) { special.set(v2Nodes.get(name),{r:quat(axis,angle)}); }
    const z=[0,0,1];
    rotate('WS_Yaw',[0,1,0],-yaw);
    rotate('WS_Upper',z,s);
    rotate('WS_Fore',z,f-s);
    rotate('WS_Hand',z,-f);
    rotate('WS_UpperParallel',z,s);
    rotate('WS_ElbowLevel',z,-s);
    rotate('WS_ForeParallel',z,f);
    for (const [name,sign] of [['WS_Jaw_L',-1],['WS_Jaw_R',1]]) {
        const i=v2Nodes.get(name), p=[...(ns[i].translation||[0,0,0])];
        p[2]=sign*gap/2000;
        special.set(i,{p});
    }
    special.set(v2Nodes.get('WS_Payload'),{p:mul(obj,.001)});
    const out=[];
    function visit(i,parent) {
        const n=ns[i],o=special.get(i)||{};
        const m=mm(parent,matrix(o.p||n.translation||[0,0,0],o.r||n.rotation,n.scale));
        if(n.mesh!==undefined) out.push([n.mesh,m]);
        (n.children||[]).forEach(c=>visit(c,m));
    }
    doc.scenes[doc.scene||0].nodes.forEach(i=>visit(i,identity));
    return out;
}
const stage=$('stage'),canvas=$('view'),ground=$('ground'),g=ground.getContext('2d'),gl=canvas.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:true});
const meshes=doc.meshes.map(s=>{const pr=s.primitives[0],p=acc(pr.attributes.POSITION),n=acc(pr.attributes.NORMAL),m=doc.materials[pr.material],rgb=m.pbrMetallicRoughness.baseColorFactor.slice(0,3).map(x=>x<=.00313?12.92*x:1.055*x**(1/2.4)-.055);return {p,n,rgb};});
let sh,ul,attr;
if(gl){
 function shader(type,code){const o=gl.createShader(type);gl.shaderSource(o,code);gl.compileShader(o);if(!gl.getShaderParameter(o,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(o));return o;}
 sh=gl.createProgram();gl.attachShader(sh,shader(gl.VERTEX_SHADER,'attribute vec3 pos,nor;uniform mat4 vp,model;varying vec3 normal;void main(){normal=mat3(model)*nor;gl_Position=vp*model*vec4(pos,1.0);}'));
 gl.attachShader(sh,shader(gl.FRAGMENT_SHADER,'precision mediump float;varying vec3 normal;uniform vec3 color;void main(){vec3 n=normalize(normal);float a=.70+.30*max(dot(n,normalize(vec3(.6,1.0,.35))),0.0);gl_FragColor=vec4(color*a,1.0);}'));gl.linkProgram(sh);if(!gl.getProgramParameter(sh,gl.LINK_STATUS))throw Error('WebGL');gl.useProgram(sh);
 ul=Object.fromEntries(['vp','model','color'].map(k=>[k,gl.getUniformLocation(sh,k)]));attr=['pos','nor'].map(k=>gl.getAttribLocation(sh,k));
 for(let i of attr)gl.enableVertexAttribArray(i);
 for(const mesh of meshes){mesh.bufs=[mesh.p,mesh.n].map(a=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,a,gl.STATIC_DRAW);return b;});}
 gl.enable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);
}
let width,height,dpr;
function fit(){width=stage.clientWidth;height=stage.clientHeight;aspect=width/height;dpr=Math.min(window.devicePixelRatio||1,2);
 for(const c of [canvas,ground]){c.width=Math.round(width*dpr);c.height=Math.round(height*dpr);}
 g.setTransform(dpr,0,0,dpr,0,0);if(gl)gl.viewport(0,0,canvas.width,canvas.height);render();}
function project(p){const v=sub(p,eye),z=dot(v,basis[2]),k=height*Math.min(1,aspect/.90)/(2*Math.tan(16*rg)*z);return [width/2+dot(v,basis[0])*k,height/2-dot(v,basis[1])*k,z];}
function stroke(pts,col,w=1){g.beginPath();pts.map(project).forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=col;g.lineWidth=w;g.stroke();}
function fill(pts,col){g.beginPath();pts.map(project).forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fillStyle=col;g.fill();}
let own=[],seq='demo',editing=false,manual=null,currentTime=0,playing=false,scale=1,showPath=false,selected=-1,lastStamp=0,lastUI=0;
const active=()=>presets[seq]?.frames||own;
function drawFloor(fs){g.clearRect(0,0,width,height);
 for(let i=-6;i<=6;i++){stroke([[i*.075,0,-.45],[i*.075,0,.45]],'#d3ddd2');stroke([[-.45,0,i*.075],[.45,0,i*.075]],'#d3ddd2');}
 fill(Array.from({length:65},(_,i)=>[.18*Math.cos(i*Math.PI/32),.001,.177*Math.sin(i*Math.PI/32)]),'rgba(54,72,64,.10)');
 function circle(p,rad,col){stroke(Array.from({length:49},(_,i)=>[p[0]+rad*Math.cos(i*Math.PI/24),p[1],p[2]+rad*Math.sin(i*Math.PI/24)]),col,1.5);}
 circle([start[0]/1000,.001,start[2]/1000],.025,'#ba8e55');
 if(showPath&&fs.length>1){g.setLineDash([4,4]);const end=fs.at(-1).t_s;stroke(Array.from({length:160},(_,i)=>mul(arm(sample(fs,end*i/159)).tip,.001)),'#287b6a',1.8);g.setLineDash([]);}
}
function drawMeshes(w){
 if(gl){gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniformMatrix4fv(ul.vp,false,vp);
 for(const [i,m] of w){const me=meshes[i];gl.uniformMatrix4fv(ul.model,false,m);gl.uniform3fv(ul.color,me.rgb);for(let j=0;j<2;j++){gl.bindBuffer(gl.ARRAY_BUFFER,me.bufs[j]);gl.vertexAttribPointer(attr[j],3,gl.FLOAT,false,0,0);}gl.drawArrays(gl.TRIANGLES,0,me.p.length/3);}return;}
 const faces=[];
 for(const [i,m] of w){const me=meshes[i];for(let j=0;j<me.p.length;j+=9){const pv=[0,3,6].map(d=>transform(m,me.p.subarray(j+d,j+d+3))),n=unit(cross(sub(pv[1],pv[0]),sub(pv[2],pv[0])));if(dot(n,sub(eye,pv[0]))<=0)continue;
 const pp=pv.map(project),shade=.70+.30*Math.max(0,dot(n,[.49,.82,.28]));faces.push([pp.reduce((s,v)=>s+v[2],0),pp,'rgb('+me.rgb.map(x=>Math.round(255*x*shade)).join(',')+')']);}}
 faces.sort((a,b)=>b[0]-a[0]);for(const [,pts,col] of faces){g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fillStyle=col;g.fill();}
}
