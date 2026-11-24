'use strict';
// Oba distribuované cykly musí projít kontrolou obálek a souhlasit s distribuovaným modelem.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const src = path.join(root,'zdroj/emil-eta');
const glb = fs.readFileSync(path.join(src,'Emil-V2.glb'));
const model = JSON.parse(glb.toString('utf8',20,20+glb.readUInt32LE(12)));
const ctx = vm.createContext({assert, model});
vm.runInContext(fs.readFileSync(path.join(src,'pohyb.js'),'utf8'),ctx);
vm.runInContext(`
const near=(a,b)=>a.every((v,i)=>Math.abs(v-b[i])<0.001);
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
// Původní cíl přímo před robotem protínal podvozek.
assert(check(inverse([225,16,55],32),true).includes('podvozek'));
`,ctx);
const page=fs.readFileSync(path.join(root,'web/app/emil-eta.html'),'utf8');
assert(page.includes(glb.toString('base64')));
for(const name of ['pohyb.js','vykresleni.js','ovladani.js']) {
    assert(page.includes(fs.readFileSync(path.join(src,name),'utf8').replace(/\r\n/g,'\n')));
}
for(const name of ['miska','koule','sablona']) for(const extension of ['stl','3mf']) {
    const file=name+'.'+extension;
    assert(page.includes('file='+file));
    assert(fs.statSync(path.join(root,'web/app/tisk/emil',file)).size>84);
}
console.log('Emil ETA V2: geometrie, kolize, 4 002 poloh, přenos a tiskové soubory OK.');
