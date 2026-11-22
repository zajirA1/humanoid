import asyncio, json, sys
from playwright.async_api import async_playwright
JS=r'''(async()=>{
 const out={};
 const set=(id,val)=>{const e=$(id); if(!e)return; e.value=val; e.dispatchEvent(new Event('change',{bubbles:true})); e.dispatchEvent(new Event('input',{bubbles:true}));};
 function scan(name){
   const o=info(), n=o.frames??(o.poses?o.poses.length:1); const mx=Array(22).fill(0), qlo=Array(22).fill(1e9), qhi=Array(22).fill(-1e9); let peak=0,pf=-1,pj=null,bad=0;
   for(let f=0;f<n;f++){ idx=f; const a=row(), w=fk(a.q,a.rt); let load=null;
     try{ load=r10IsMotion()?r10LoadFor(a,w):currentLoad(); }catch(e){ bad++; }
     for(let j=0;j<22;j++){ qlo[j]=Math.min(qlo[j],a.q[j]); qhi[j]=Math.max(qhi[j],a.q[j]); }
     if(load&&load.tau){ for(let j=0;j<22;j++){ const t=load.tau[j]; if(t!=null&&Math.abs(t)>mx[j]) mx[j]=Math.abs(t);} }
     if(load&&load.ratio>peak){peak=load.ratio;pf=f;pj=load.joint;}
     if(!load) bad++;
   }
   out[name]={frames:n,maxTau:mx,qlo,qhi,peak,peakFrame:pf,peakJoint:pj,missing:bad};
 }
 for(const m of ['home','sit','dance','walk']){ choose(m); scan(m); }
 choose('stairs'); for(const h of ['150','180']){ set('height',h); scan('stairs/'+h); }
 choose('turn'); for(const d of ['left','right']) for(const a of ['45','90','180','360']){ set('r10Direction',d); set('r10TurnAngle',a); scan('turn/'+a+'/'+d); }
 choose('pickup'); for(const ob of ['mug','sock','box']) for(const h of ['right','left','both']) for(const s of [...$('r10Surface').options].map(o=>o.value)){ set('r10Object',ob); set('r10Hands',h); set('r10Surface',s); scan('pickup/'+ob+'/'+h+'/'+s); }
 // heaviest mug case
 set('r10Object','mug'); set('r10Hands','right'); const mass=$('r10Mass'); mass.value=mass.max; mass.dispatchEvent(new Event('input',{bubbles:true})); scan('pickup/mug/right/max'+mass.max+'g');
 out.massMax=mass.max; out.limits=r9Loads.limitsNm;
 return out;})()'''
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1400,'height':1000}); errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file:///home/claude/sim/orig_hooked.html')
        await pg.wait_for_function('document.documentElement.dataset.ready==="true"',timeout=60000)
        await pg.select_option('#kAssembly','r9'); await pg.wait_for_timeout(500)
        res=await pg.evaluate('(js)=>__ev(js)',JS)
        json.dump(res,open('/home/claude/sim/scen.json','w')); print(len(res),errs[:3])
        for k,v in res.items():
            if isinstance(v,dict): print(k,v['frames'],'peak',round(v['peak'],3),v['peakJoint'],'missing',v['missing'])
        await b.close()
asyncio.run(main())
