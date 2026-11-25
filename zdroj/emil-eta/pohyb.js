'use strict';
const $ = id => document.getElementById(id);
const rg = Math.PI / 180;
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const add = (a,b) => a.map((v,i) => v+b[i]);
const sub = (a,b) => a.map((v,i) => v-b[i]);
const mul = (v,k) => v.map(x => x*k);
const dot = (a,b) => a.reduce((s,x,i) => s+x*b[i],0);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
const unit = v => mul(v,1/(Math.hypot(...v)||1));

// X dopředu, Y vzhůru, Z doprava. Sklony obou článků se měří od vodorovné roviny.
const deckTop = 105.5, base = [91,deckTop+80,55], start = [212,16,125], basket = [18,deckTop+22,110];
const upper = 86.2, lower = 128, nose = 39;
const names = ['yaw_deg','upper_deg','fore_deg','jaw_gap_mm'];
const labels = ['Otočení základny','Sklon prvního článku','Sklon předloktí','Mezera čelistí'];
const lim = [[-10,165],[-48,125],[-100,65],[0,48]];
const keys = f => names.map(k => f[k]);
function arm(q) {
    const [yaw, s, f] = q.map(x => x*rg);
    const point = (r,h) => [base[0]+r*Math.cos(yaw), base[1]+h, base[2]+r*Math.sin(yaw)];
    const elbow = point(upper*Math.cos(s),upper*Math.sin(s));
    const wrist = point(upper*Math.cos(s)+lower*Math.cos(f), upper*Math.sin(s)+lower*Math.sin(f));
    const tip = add(wrist,[nose*Math.cos(yaw),0,nose*Math.sin(yaw)]);
    return {base,elbow,wrist,tip};
}
function inverse(target,gap) {
    const [x,y,z] = sub(target,base), r = Math.hypot(x,z)-nose;
    const cosine = (r*r+y*y-upper*upper-lower*lower)/(2*upper*lower);
    if (Math.abs(cosine)>1) throw Error('Cíl je mimo geometrický dosah.');
    const e = -Math.acos(cosine);
    const s = Math.atan2(y,r)-Math.atan2(lower*Math.sin(e), upper+lower*Math.cos(e));
    return [Math.atan2(z,x)/rg,s/rg,(s+e)/rg,gap];
}
function pose(t_s,label,q,event=null) {
    return {t_s,label,...Object.fromEntries(names.map((k,i)=>[k,q[i]])),event};
}
const park = [10,75,-25,40];
const atFloor = gap => inverse(start,gap);
const atBowl = gap => inverse([18,deckTop+50,110],gap);
const nearBowl = gap => inverse([18,deckTop+58,110],gap);
const transfer = [
    pose(0,'Výchozí poloha',park),
    pose(2.5,'Vpravo před nárazníkem',inverse([212,65,125],43)),
    pose(4.5,'K předmětu',atFloor(43)),
    pose(5.5,'Uchopit',atFloor(32),'grasp'),
    pose(8,'Zvednout',inverse([212,82,125],32)),
    pose(10,'Nad talířem',[30,91,-55,32]),
    pose(13,'Otočit k misce',[143,91,-55,32]),
    pose(15.5,'Nad miskou',nearBowl(32)),
    pose(17,'Připravit k uvolnění',atBowl(32)),
    pose(17.5,'Uvolnit nad miskou',atBowl(35),'release'),
    pose(18,'Otevřít',atBowl(43)),
    pose(20,'Odjet od misky',nearBowl(43)),
    pose(22,'Narovnat',[143,91,-55,40]),
    pose(25,'Výchozí poloha',park)
];
const sweep = [
    pose(0,'Výchozí poloha',park),pose(2,'Před robotem',[0,55,-35,40]),
    pose(5,'Pravý bok',[85,91,-55,40]),pose(8,'Nad miskou',nearBowl(40)),
    pose(10,'Zavřít',[143,91,-55,12]),pose(12,'Pravý bok',[85,91,-55,40]),pose(15,'Výchozí poloha',park)
];
const recipe = {
    format:'emil-eta-motion/2',model:'ETA 5229 / Waveshare Robot Arm for Pi / V3.1',
    coordinates:'mm, X dopředu, Y vzhůru, Z doprava; oba sklony od horizontály',
    limits_simulation:Object.fromEntries(names.map((k,i)=>[k,lim[i]]))
};
const presets = {
    demo:{name:'Podlaha a miska',frames:transfer},
    sweep:{name:'Zkouška rozsahu',frames:sweep}
};
const demo = transfer;
function sample(fs,t) {
    if (!fs.length || t<=fs[0].t_s) return keys(fs[0] || demo[0]);
    const i = fs.findIndex(f => f.t_s>=t);
    if (i<0) return keys(fs.at(-1));
    const a=fs[i-1], b=fs[i], x=(t-a.t_s)/(b.t_s-a.t_s);
    const u=x*x*x*(10-15*x+6*x*x);
    return names.map(k => a[k]+(b[k]-a[k])*u);
}
function carried(fs,t,q) {
    let pos=start, held=false, dropped=false, inBowl=false, releaseTime=0, issue='';
    for (const frame of fs) {
        if (frame.t_s>t+1e-7) break;
        if (!frame.event) continue;
        const angles=keys(frame), tip=arm(angles).tip;
        if (frame.event==='grasp') {
            const target=inBowl ? [pos[0],basket[1],pos[2]] : pos;
            if (!held && Math.hypot(...sub(tip,target))<4 && Math.abs(angles[3]-32)<=2) { held=true; inBowl=false; }
            else issue='Uchopení mimo předmět nebo chybná mezera čelistí.';
        } else if (frame.event==='release') {
            if (!held) { issue='Položení bez uchopeného předmětu.'; continue; }
            held=false; dropped=true; pos=tip; releaseTime=frame.t_s;
            inBowl=Math.abs(pos[0])<=30 && Math.abs(pos[2]-97)<=27 && pos[1]>=basket[1] && pos[1]<=deckTop+65;
            if (!inBowl && Math.abs(pos[1]-16)>3) issue='Místo položení nemá ověřenou oporu.';
        }
    }
    if (held) {
        pos=arm(q).tip;
        if (Math.abs(q[3]-32)>3) issue='Mezera čelistí neodpovídá uchopenému předmětu.';
    }
    if (inBowl) {
        const dt=Math.max(0,t-releaseTime);
        pos=[pos[0],Math.max(basket[1],pos[1]-4905*dt*dt),pos[2]];
    }
    const state=held?'V chapadle':inBowl && pos[1]<=basket[1]?'V misce':dropped?'Uvolněný':'Na podlaze';
    return {pos,held,issue,state};
}
let hardware;
function configureHardware(extras) {
    if (!extras.lidar || !Array.isArray(extras.static_obstacles)) throw Error('Chybí geometrie nástavby V3.');
    hardware=extras;
}
function movingEnvelopes(q,held) {
    const {elbow,wrist,tip}=arm(q), yaw=q[0]*rg;
    const dx=Math.cos(yaw), dz=Math.sin(yaw);
    const local=(p,x,y,z)=>[p[0]+dx*x-dz*z,p[1]+y,p[2]+dz*x+dx*z];
    const parts=[];
    const link=(a,b,r)=>parts.push({a,b,r});
    for (const side of [-1,1]) {
        // Obě rovnoběžná táhla mají příčnou rozteč i výškový odstup jako v GLB.
        link(local(base,0,0,side*16),local(elbow,0,0,side*16),4.2);
        link(local(base,-13,6,side*12.2),local(elbow,-13,6,side*12.2),2.7);
        link(local(elbow,-13,6,side*13),local(elbow,0,10,side*13),4.2);
        link(local(elbow,0,0,side*10.2),local(wrist,0,0,side*10.2),3.6);
        link(local(elbow,0,10,side*7.9),local(wrist,0,10,side*7.9),2.7);
        link(local(wrist,0,0,side*9.6),local(wrist,0,10,side*9.6),4.2);
        link(local(wrist,0,5,side*11),local(wrist,20,5,side*11),3);
        const jaw=side*(q[3]/2+2);
        link(local(wrist,9,0,jaw),local(tip,2,0,jaw),3.1);
    }
    // Servo je nad vodorovným chapadlem. Jeho obálka se otáčí s celou základnou.
    link(local(wrist,-4,16,0),local(wrist,18,16,0),11.5);
    if (held) link(tip,tip,16);
    return parts;
}
function check(q,held) {
    const hits=new Set();
    function probe([x,y,z],r) {
        if (y-r<-.2) hits.add('podlaha');
        if (Math.hypot(x,z)<175+r && y-r<83 && y+r>7) hits.add('podvozek');
        if (Math.hypot(x,z)<164+r && y-r<deckTop && y+r>hardware.lidar.deck_bottom_mm) hits.add('nosný talíř');
        if (Math.hypot(x,z)<33+r && y-r<hardware.lidar.adhesive_y_mm[1] && y+r>hardware.lidar.adhesive_y_mm[0]) hits.add('lepicí vrstva');
        for (const obstacle of hardware.static_obstacles) {
            const [lo,hi]=obstacle.bounds_mm;
            if (x>lo[0]-r && x<hi[0]+r && y>lo[1]-r && y<hi[1]+r && z>lo[2]-r && z<hi[2]+r) hits.add(obstacle.label);
        }
        if (Math.abs(x-91)<40+r && z>-54.6-r && z<95+r && y-r<deckTop+10 && y+r>deckTop) hits.add('základna Waveshare');
        if (Math.abs(x)<49+r && Math.abs(z-97)<46+r && y-r<deckTop+6-.15 && y+r>deckTop) hits.add('dno misky');
        if (y-r<deckTop+18 && y+r>deckTop+6 && ((Math.abs(Math.abs(x)-47.5)<1.5+r && Math.abs(z-97)<46+r) ||
            (Math.abs(Math.abs(z-97)-44.5)<1.5+r && Math.abs(x)<49+r))) hits.add('okraj misky');
    }
    for (const {a,b,r} of movingEnvelopes(q,held)) {
        const delta=sub(b,a), count=Math.max(1,Math.ceil(Math.hypot(...delta)/4));
        for (let i=0;i<=count;i++) probe(add(a,mul(delta,i/count)),r);
    }
    return [...hits];
}

// Úhlová obálka pohyblivé části v celé výšce optického okénka.
// Nula = příď, 90° = pravý bok. Původní podpěry víčka zde nejsou přičteny.
function lidarShadows(q,held) {
    const arcs=[], [low,high]=hardware.lidar.window_y_mm;
    for (const {a,b,r} of movingEnvelopes(q,held)) {
        if (Math.max(a[1],b[1])+r<low || Math.min(a[1],b[1])-r>high) continue;
        const d=sub(b,a);
        let t0=0,t1=1;
        if (Math.abs(d[1])>1e-8) {
            const l=(low-r-a[1])/d[1],h=(high+r-a[1])/d[1];
            t0=clamp(Math.min(l,h),0,1);t1=clamp(Math.max(l,h),0,1);
        }
        const p=add(a,mul(d,t0)),e=add(a,mul(d,t1));
        const angle=t=>Math.atan2(t[2],t[0])/rg;
        const half=t=>Math.asin(clamp(r/Math.hypot(t[0],t[2]),0,1))/rg;
        const centre=angle(p), other=centre+((angle(e)-centre+540)%360-180);
        let start=Math.min(centre-half(p),other-half(e));
        let end=Math.max(centre+half(p),other+half(e));
        const offset=360*Math.floor(start/360);
        start-=offset;end-=offset;
        if (end>360) arcs.push([0,end-360],[start,360]);
        else arcs.push([start,end]);
    }
    const result=[];
    for (const interval of arcs.sort((a,b)=>a[0]-b[0])) {
        const last=result.at(-1);
        if (last && interval[0]<=last[1]) last[1]=Math.max(last[1],interval[1]);
        else result.push(interval);
    }
    return result;
}
