'use strict';
// Oba distribuované cykly musí projít kontrolou obálek a souhlasit s distribuovaným modelem.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const src = path.join(root,'zdroj/emil-eta');
const glb = fs.readFileSync(path.join(src,'Emil-V3.1.glb'));
const model = JSON.parse(glb.toString('utf8',20,20+glb.readUInt32LE(12)));
const ctx = vm.createContext({assert, model});
vm.runInContext(fs.readFileSync(path.join(src,'pohyb.js'),'utf8'),ctx);
vm.runInContext(`
const near=(a,b)=>a.every((v,i)=>Math.abs(v-b[i])<0.001);
configureHardware(model.extras);
assert(near(park,Object.values(model.extras.parked)));
assert(near(start,mul(model.nodes[model.extras.controls.WS_Payload].translation,1000)));
for (const item of Object.values(presets)) {
    const frames=item.frames;
    for(let i=0;i<=100*frames.at(-1).t_s;i++) {
        const t=i/100,q=sample(frames,t),object=carried(frames,t,q);
        assert(q.every((x,j)=>Number.isFinite(x)&&x>=lim[j][0]&&x<=lim[j][1]));
        assert.equal(object.issue,'');
        assert.equal(check(q,object.held).join(', '),'',item.name+' · '+t+' s');
    }
}
assert(near(arm(atFloor(32)).tip,start));
assert(carried(transfer,8,sample(transfer,8)).held);
const end=carried(transfer,25,park);
assert(near(end.pos,basket));
assert.equal(end.state,'V misce');
// U bodu o 10 mm blíže nárazníku obálka paže zasáhne podvozek i se sníženou základnou.
assert(check(inverse([215,16,55],32),true).includes('podvozek'));
assert.equal(lidarShadows(park,false).length,0);
const obstruction=lidarShadows(atFloor(32),true);
assert(obstruction.length>0 && obstruction.every(([a,b])=>a>20 && b<45 && a<b));
assert(near(model.extras.tablet.front,[1,0,0]) && near(model.extras.tablet.rear,[-1,0,0]));
assert.equal(model.extras.lidar.stock_posts_mm.length,3);
`,ctx);
// Kontrola instalovaných dílů proti skutečně distribuovaným vrcholům GLB.
const names=new Map(model.nodes.map((node,i)=>[node.name,i]));
assert(!names.has('Držák kamery') && !names.has('Kamera') && !names.has('Červený talíř'));
const printed=model.nodes.filter(node=>node.extras?.stl);
assert.equal(printed.length,8);   // talíř, stojan, horní pojistka, dvě kamery na liště, 4 příchytky
const lidar=model.extras.lidar;
const xyz=(node)=>{
    const mesh=model.meshes[node.mesh].primitives[0];
    const acc=model.accessors[mesh.attributes.POSITION];
    const view=model.bufferViews[acc.bufferView];
    const pos=28+glb.readUInt32LE(12)+(view.byteOffset||0)+(acc.byteOffset||0);
    return Array.from({length:acc.count},(_,i)=>[0,1,2].map(j=>glb.readFloatLE(pos+12*i+4*j)*1000));
};
for (const node of printed) {
    const points=xyz(node); // vestavěné STL jsou exportované v robotovém rámci
    const bottom=Math.min(...points.map(p=>p[1]));
    assert(bottom>lidar.window_y_mm[1],node.name+' protíná optické pásmo');
    if (node.extras.stl==='talir.stl') {
        assert(Math.abs(bottom-98.5)<.001);
        assert(points.every(([,y])=>Math.abs(y-98.5)<.001 || Math.abs(y-105.5)<.001));
        assert(Math.abs(lidar.deck_top_mm-lidar.deck_bottom_mm-7)<.001);
    }
}
const stereo=model.extras.stereo;
assert(Math.abs(stereo.right_mm[2]-stereo.left_mm[2]-stereo.baseline_mm)<.001);
assert.equal(stereo.baseline_mm,110);
assert.equal(stereo.pitch_down_deg,20);
assert(Math.abs(Math.hypot(...stereo.forward)-1)<1e-7);
// Möller–Trumbore: pohled od předního skla proti skutečným tiskovým trojúhelníkům.
function rayHits(origin,direction,triangles,maxDistance) {
    const sub=(a,b)=>a.map((x,i)=>x-b[i]);
    const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
    const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0);
    for(let i=0;i<triangles.length;i+=3) {
        const a=triangles[i], e=sub(triangles[i+1],a), f=sub(triangles[i+2],a);
        const h=cross(direction,f), det=dot(e,h);
        if (Math.abs(det)<1e-9) continue;
        const s=sub(origin,a), u=dot(s,h)/det;
        if (u<0 || u>1) continue;
        const q=cross(s,e),v=dot(direction,q)/det, t=dot(f,q)/det;
        if(v>=0 && v+u<=1 && t>=0 && t<=maxDistance) return true;
    }
    return false;
}
for(const [side,origin] of [['L',stereo.left_mm],['R',stereo.right_mm]]) {
    const optic=model.nodes[names.get('Stereo_'+side+'_optical')];
    assert(optic.translation.every((v,i)=>Math.abs(v*1000-origin[i])<.001));
    for(const part of printed) assert(!rayHits(origin,stereo.forward,xyz(part),250),part.name+' zakrývá osu kamery '+side);
}
const page=fs.readFileSync(path.join(root,'web/app/emil-eta.html'),'utf8');
assert(page.includes(glb.toString('base64')));
for(const name of ['pohyb.js','vykresleni.js','stereo.js','ovladani.js']) {
    assert(page.includes(fs.readFileSync(path.join(src,name),'utf8').replace(/\r\n/g,'\n')));
}
for(const name of ['miska','koule','sablona','talir','stojan','pojistka-tabletu','prichytka-ramene','stereo-lista']) for(const extension of ['stl','3mf']) {
    const file=name+'.'+extension;
    assert(page.includes('file='+file));
    assert(fs.statSync(path.join(root,'web/app/tisk/emil',file)).size>84);
}
console.log('Emil ETA V3.1: 4 002 poloh, mechanika, výhled lidar/stereo a tiskové soubory OK.');
