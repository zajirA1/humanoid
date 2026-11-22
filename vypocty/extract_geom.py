import asyncio, json, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1400,'height':900})
        errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file:///home/claude/sim/orig_hooked.html')
        await pg.wait_for_function('document.documentElement.dataset.ready==="true"',timeout=60000)
        await pg.evaluate('__ev("choose(\'climb\')")')
        await pg.wait_for_timeout(1000)
        res=await pg.evaluate('''()=>__ev(`(()=>{
          const items=[];
          const keyOf=o=>['L_knee_ram','r8_L_knee_ram'].includes(o.key)?o.key+'_R5':o.key;
          for(const o of r9RenderItems) items.push({key:keyOf(o),link:o.link,t:o.t,owner:o.owner,frame:!!o.frame,minor:!!o.minor,kind:'cad'});
          for(const c of r9Covers()) items.push({key:c.key,link:c.link,t:null,kind:'cover',name:c.name});
          for(const o of r11ShinItems('climb')) items.push({key:o.key,link:o.link,t:o.t,kind:'shin'});
          const meshes={};
          for(const it of items){ if(!meshes[it.key]&&sourceMeshes[it.key]) meshes[it.key]=sourceMeshes[it.key]; }
          const missing=items.filter(i=>!sourceMeshes[i.key]).map(i=>i.key);
          return {items,meshes,missing,mode,assembly:$('r8Assembly').value,nposes:climbData.poses.length,P:P};
        })()`)''')
        print(len(res['items']),len(res['meshes']),set(res['missing']),res['mode'],res['assembly'],res['nposes'],errs)
        json.dump(res,open('/home/claude/sim/geom.json','w'))
        await pg.screenshot(path='/home/claude/sim/orig_climb.png',full_page=False)
        await b.close()
asyncio.run(main())
