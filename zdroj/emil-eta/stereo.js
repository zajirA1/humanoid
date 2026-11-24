// Rektifikované obrazy mají shodné hlavní body a společnou vodorovnou základnu.
const sensorW=1280, sensorH=720;
function stereoPoint(point,origin,rig,focal) {
    const delta=sub(point,origin), z=dot(delta,rig.forward);
    if(z<=0) return null;
    const right=unit(cross(rig.forward,rig.up));
    return {u:sensorW/2+focal*dot(delta,right)/z,
        v:sensorH/2-focal*dot(delta,rig.up)/z,z};
}
function stereoDepth(focal,baseline,left,right) {
    if(!(focal>0 && baseline>0) || !left || !right) return null;
    const disparity=left.u-right.u;
    if(!(disparity>0) || Math.abs(left.v-right.v)>3) return null;
    return {disparity,depth:focal*baseline/disparity};
}
const stereoRig=doc.extras.stereo;
const stereoViews=['left','right'];
const sourceImages={left:null,right:null}, chosenPoints={left:null,right:null};
const imageVersions={left:0,right:0};
const numberCs=(n,d=0)=>n.toLocaleString('cs-CZ',{maximumFractionDigits:d});
const exampleFocal=900;
function sensorCentre(side){return stereoRig[side+'_mm'];}
function insideSensor(p){return p && p.u>=0 && p.u<sensorW && p.v>=0 && p.v<sensorH;}
function modelProjection(origin,rig,fx) {
    const f=rig.forward,r=unit(cross(f,rig.up)),u=rig.up,o=mul(origin,.001);
    const view=new Float32Array([r[0],u[0],-f[0],0,r[1],u[1],-f[1],0,r[2],u[2],-f[2],0,-dot(r,o),-dot(u,o),dot(f,o),1]);
    const near=.005, far=12;
    return mm(new Float32Array([2*fx/sensorW,0,0,0,0,2*fx/sensorH,0,0,0,0,-(far+near)/(far-near),-1,0,0,-2*far*near/(far-near),0]),view);
}
function gridInSensor(ctx,origin,scale) {
    ctx.fillStyle='#e8eff0';ctx.fillRect(0,0,sensorW,sensorH);
    ctx.strokeStyle='#b9c8c8';ctx.lineWidth=2;
    function line(a,b) {
        const p=stereoPoint(a,origin,stereoRig,scale),q=stereoPoint(b,origin,stereoRig,scale);
        if(!p || !q) return;
        ctx.beginPath();ctx.moveTo(p.u,p.v);ctx.lineTo(q.u,q.v);ctx.stroke();
    }
    for(let z=-2400;z<=2400;z+=200) line([0,0,z],[5500,0,z]);
    for(let x=0;x<=5400;x+=200) line([x,0,-2400],[x,0,2400]);
}
// Ověření viditelnosti středu bodu na neobarvené scéně. Omezení testu na
// ohraničující kvádry před průnikem s trojúhelníky udržuje odezvu při přehrávání.
const meshBoxes=doc.meshes.map(item=>{
    const a=doc.accessors[item.primitives[0].attributes.POSITION]; return [a.min,a.max];
});
function occluded(origin,target,items,skipIndex) {
    const startM=mul(origin,.001),endM=mul(target,.001);
    for(const [mesh,m] of items) {
        if(mesh===skipIndex) continue;
        const basis=[[m[0],m[1],m[2]],[m[4],m[5],m[6]],[m[8],m[9],m[10]]];
        const t=[m[12],m[13],m[14]];
        const local=p=>basis.map(axis=>dot(sub(p,t),axis)/dot(axis,axis));
        const a=local(startM),b=local(endM),v=sub(b,a),[lo,hi]=meshBoxes[mesh];
        let enter=.005/Math.hypot(...sub(endM,startM)),leave=.9999;
        for(let j=0;j<3 && enter<=leave;j++) {
            if(Math.abs(v[j])<1e-9){if(a[j]<lo[j]||a[j]>hi[j]) enter=2;continue;}
            const ta=(lo[j]-a[j])/v[j],tb=(hi[j]-a[j])/v[j];
            enter=Math.max(enter,Math.min(ta,tb));leave=Math.min(leave,Math.max(ta,tb));
        }
        if(enter>leave) continue;
        const verts=meshes[mesh].p;
        for(let i=0;i<verts.length;i+=9) {
            const p=verts.subarray(i,i+3),e1=sub(verts.subarray(i+3,i+6),p),e2=sub(verts.subarray(i+6,i+9),p);
            const h=cross(v,e2),det=dot(e1,h);
            if(Math.abs(det)<1e-12) continue;
            const s=sub(a,p),u=dot(s,h)/det;
            if(u<0||u>1) continue;
            const k=cross(s,e1),w=dot(v,k)/det;
            if(w<0||u+w>1) continue;
            const d=dot(e2,k)/det;
            if(d>=enter-1e-6 && d<=leave+1e-6) return true;
        }
    }
    return false;
}
function markPoint(ctx,p) {
    ctx.beginPath();ctx.arc(p.u,p.v,15,0,2*Math.PI);
    ctx.moveTo(p.u-22,p.v);ctx.lineTo(p.u+22,p.v);
    ctx.moveTo(p.u,p.v-22);ctx.lineTo(p.u,p.v+22);
    ctx.lineWidth=4;ctx.strokeStyle='#fff';ctx.stroke();
    ctx.lineWidth=2;ctx.strokeStyle='#8f3610';ctx.stroke();
}
let previewStamp=0;
function simulatedStereo(q,payload,force=false) {
    if(!$('stereoPanel').open || $('stereoMode').value!=='model') return;
    const now=performance.now();
    if(!force && playing && now-previewStamp<180) return;
    previewStamp=now;
    const usePayload=$('stereoTarget').value==='payload', x=Number($('stereoRange').value);
    $('stereoRange').disabled=usePayload;$('stereoRangeValue').textContent=numberCs(x)+' mm';
    const target=usePayload?payload:[x,16,0], frames=world(q,payload);
    const objectMesh=ns[v2Nodes.get('WS_Payload')].mesh;
    const visible={},points={},saved=vp;
    for(const side of stereoViews) {
        const origin=sensorCentre(side), view=$('cam-'+side),ctx=view.getContext('2d');
        ctx.setTransform(view.width/sensorW,0,0,view.height/sensorH,0,0);
        gridInSensor(ctx,origin,exampleFocal);
        const p=stereoPoint(target,origin,stereoRig,exampleFocal);points[side]=p;
        visible[side]=insideSensor(p) && !occluded(origin,target,frames,usePayload?objectMesh:-1);
        if(gl) {
            const w=Math.min(canvas.width,Math.floor(canvas.height*16/9)),h=Math.floor(w*9/16);
            vp=modelProjection(origin,stereoRig,exampleFocal);
            gl.viewport(0,0,w,h);
            const objects=usePayload?frames:[...frames,[objectMesh,matrix(mul(target,.001))]];
            drawMeshes(objects);
            ctx.drawImage(canvas,0,canvas.height-h,w,h,0,0,sensorW,sensorH);
        } else if(visible[side]) {
            ctx.fillStyle='#db9b3d';ctx.beginPath();ctx.arc(p.u,p.v,16*exampleFocal/p.z,0,2*Math.PI);ctx.fill();
        }
        if(visible[side]) markPoint(ctx,p);
    }
    vp=saved;if(gl) gl.viewport(0,0,canvas.width,canvas.height);
    const left=points.left,right=points.right;
    const estimate=visible.left&&visible.right?stereoDepth(exampleFocal,stereoRig.baseline_mm,left,right):null;
    $('stereoResult').textContent=estimate?
        'Posun '+numberCs(estimate.disparity,1)+' px · hloubka '+numberCs(estimate.depth)+' mm podél optické osy.':
        'Bod je mimo společný výhled nebo ho zakrývá část robota. Hloubku nelze určit.';
}
function showRealImage(side) {
    const cv=$('real-'+side),ctx=cv.getContext('2d'),img=sourceImages[side];
    ctx.clearRect(0,0,cv.width,cv.height);
    if(!img) return;
    ctx.drawImage(img,0,0,cv.width,cv.height);
    const p=chosenPoints[side];
    if(p) {
        ctx.save();ctx.scale(cv.width/img.width,cv.height/img.height);markPoint(ctx,p);ctx.restore();
    }
}
function realResult(){
    const a=sourceImages.left,b=sourceImages.right;
    let message='Nahraj oba rektifikované snímky a v každém označ stejný bod.';
    if(a&&b && (a.width!==b.width || a.height!==b.height)) message='Oba snímky musejí mít stejné rozlišení.';
    else if(a&&b&&chosenPoints.left&&chosenPoints.right) {
        const res=stereoDepth(Number($('realFocal').value),Number($('realBaseline').value),chosenPoints.left,chosenPoints.right);
        message=res?'Posun '+numberCs(res.disparity,1)+' px · hloubka '+numberCs(res.depth)+' mm podél optické osy.':
            'Zkontroluj kalibraci, pořadí kamer a výběr bodů. Body mají ležet na stejném řádku (±3 px) s kladným posunem.';
    }
    $('realResult').textContent=message;
}
for(const side of stereoViews) {
    $('file-'+side).onchange=async event=>{
        const file=event.target.files[0], version=++imageVersions[side];
        sourceImages[side]?.close();sourceImages[side]=null;chosenPoints[side]=null;showRealImage(side);realResult();
        if(!file) return;
        try {
            const img=await createImageBitmap(file);
            if(version!==imageVersions[side]){img.close();return;}
            sourceImages[side]=img;
            const cv=$('real-'+side);
            cv.width=640;cv.height=Math.max(1,Math.round(640*img.height/img.width));
            showRealImage(side);realResult();
        } catch {if(version===imageVersions[side]) $('realResult').textContent='Obrázek se nepodařilo načíst.';}
    };
    $('real-'+side).onclick=event=>{
        const img=sourceImages[side];if(!img)return;
        const box=event.target.getBoundingClientRect();
        chosenPoints[side]={u:(event.clientX-box.left)*img.width/box.width,v:(event.clientY-box.top)*img.height/box.height};
        showRealImage(side);realResult();
    };
}
function changeStereo() {
    const real=$('stereoMode').value==='real';
    $('realPane').hidden=!real;$('simPane').hidden=real;
    if(real) realResult();
    else if(width) render();
}
$('stereoMode').onchange=changeStereo;$('stereoPanel').ontoggle=changeStereo;
$('stereoTarget').onchange=()=>render();$('stereoRange').oninput=()=>render();
$('realFocal').oninput=$('realBaseline').oninput=realResult;
$('stereoParam').textContent='Rozteč optických středů '+numberCs(stereoRig.baseline_mm)+' mm · sklon '+numberCs(stereoRig.pitch_down_deg)+'° dolů · virtuální ohnisko '+exampleFocal+' px při 1280 × 720.';
$('openStereo').addEventListener('click',()=>{$('stereoPanel').open=true;});
let showLaser=false;
$('laser').onclick=()=>{
    showLaser=!showLaser;$('laser').setAttribute('aria-pressed',String(showLaser));ui();render();
};
function updateScanLabel(q,held) {
    const out=$('scanStatus');out.hidden=!showLaser;
    if(!showLaser) return;
    const sectors=lidarShadows(q,held);
    const degrees=sectors.reduce((sum,[a,b])=>sum+b-a,0);
    out.textContent=degrees?'Ruka nebo náklad v pásmu laseru · odhad stínu '+numberCs(degrees,1)+'°.':
        'Ruka i náklad jsou v této poloze mimo skenovací pásmo.';
}
function drawLaserPlane(q,held) {
    if(!showLaser) return;
    const scanner=doc.extras.lidar,o=mul(scanner.origin_mm,.001),r0=scanner.window_radius_mm*.001,r1=.33;
    const point=(r,a)=>[o[0]+r*Math.cos(a*rg),o[1],o[2]+r*Math.sin(a*rg)];
    const sectors=lidarShadows(q,held);
    const posts=scanner.stock_posts_mm.map(p=>{
        const x=p.x-scanner.origin_mm[0],z=p.z-scanner.origin_mm[2];
        return {angle:Math.atan2(z,x)/rg,half:Math.asin(p.radius/Math.hypot(x,z))/rg};
    });
    for(let a=0;a<360;a+=2) {
        const blocked=sectors.some(([lo,hi])=>a+2>lo&&a<hi);
        const stock=posts.some(p=>Math.abs(((a+1-p.angle+540)%360)-180)<p.half);
        const color=blocked?'rgba(197,82,39,.36)':stock?'rgba(63,76,84,.29)':'rgba(0,126,127,.10)';
        fill([point(r0,a),point(r1,a),point(r1,a+2),point(r0,a+2)],color);
        stroke([point(r1,a),point(r1,a+2)],blocked?'#bd522d':stock?'#4c565b':'#5c9390',blocked||stock?3:1);
    }
}
