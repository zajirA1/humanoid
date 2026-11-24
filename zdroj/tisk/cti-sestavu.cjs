// Přečte přesné sítě a seznam instancí z konstrukčního kódu simulátoru.
// Výběr ani zaokrouhlení geometrie pro kolizní kontrolu se zde nepoužívá.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const scripts = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const source = scripts.find(s => s[2].includes('function downloadCAD(meshes)'))?.[2];
const insert = 'function shinRunner(radius, halfLength)';
const pivots = source?.match(/(const r11FixedTip=[^;]*;\s*const r11InputPivot=[^;]*;)/)?.[1];
if (!source?.includes(insert) || !pivots) throw Error('Změnil se tvar simulátoru; ověřte načtení dat před exportem.');
const data = new Map();
for (const [,attrs,body] of scripts) {
    const id = /\bid="([^"]+)"/.exec(attrs)?.[1];
    if (id) data.set(id,{textContent:body});
}
data.set('r8Covers',{checked:true});
data.set('r8Assembly',{value:'r9'});
const doc = {
    documentElement:{outerHTML:''},
    getElementById(id) {
        if (!data.has(id)) data.set(id,{textContent:'',value:'',add(){},getContext(){return null;}});
        return data.get(id);
    }
};
const hook = `
{
    ${pivots}
    // Tato procedura vytváří i nástavec uchopovače; použije přesné konstanty stránky.
    let r11Pieces=null;
    ${source.slice(source.indexOf('function r11PickupToolItems(pose)'),source.indexOf('function r11ExtraCadItems('))}
    const cad=r9RenderItems.map(o=>({key:o.key,link:o.link,owner:o.owner,t:o.t,kind:'cad',frame:!!o.frame}));
    const covers=r9Covers().map(o=>({key:o.key,link:o.link,owner:null,t:I,kind:'cover',name:o.name}));
    const shins=r11ShinItems('climb').map(o=>({key:o.key,link:o.link,owner:null,t:o.t,kind:'shin'}));
    const hands=[1,-1].map(side=>({key:'opora_dlane',side,link:side===1?10:20,owner:null,kind:'palm',t:at(side*146,-12,205,1,1,1)}));
    const pickup=r11PickupToolItems().map(o=>({key:o.key,link:o.link,owner:o.owner,t:o.t,kind:'pickup',move:o.move}));
    const items=[...cad,...covers,...shins,...hands,...pickup],meshes={};
    for(const it of items) {
        const [v,f]=sourceMeshes[it.key];
        meshes[it.key]=[Array.from(v),Array.from(f)];
    }
    emit({items,meshes});
    return;
}
`;
let captured;
vm.runInNewContext(source.replace(insert,hook+insert),{
    document:doc,window:{},console,Option:function(){},atob,TextEncoder,Blob,
    emit(value){captured=value;}
});
if (!captured) throw Error('Sestava se nepodařila načíst.');
fs.writeFileSync(process.argv[3],JSON.stringify(captured));
