import asyncio, json, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1400,'height':950})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:errs.append('C:'+m.text) if m.type=='error' else None)
        await pg.goto('file:///home/claude/sim/r14_test.html')
        await pg.wait_for_function('document.documentElement.dataset.ready==="true"',timeout=60000)
        ev=lambda s: pg.evaluate('(s)=>__ev(s)',s)
        base=await ev("JSON.stringify({mode,idx,pk:Math.max(...r9Loads.climb.loads.map(l=>l.ratio)),ready:r14Ready})"); print('base',base)
        await pg.click('#r14Toggle'); await pg.wait_for_timeout(300)
        await pg.screenshot(path='/home/claude/out/t1.png')
        await pg.select_option('#r14Joint','5')
        await pg.fill('#r14N1','3'); await pg.dispatch_event('#r14N1','change')
        await pg.fill('#r14N2','8'); await pg.dispatch_event('#r14N2','change')
        print('edits',await ev("JSON.stringify(r14Edits)"))
        print('facts',await pg.inner_text('#r14Facts'))
        await pg.click('#r14RunBtn')
        await pg.wait_for_function("document.querySelector('#r14Results table')",timeout=120000)
        print('res',await ev("JSON.stringify({pk:r14Result.pk,at:r14Result.at,bad:r14Result.bad.length,drift:r14Result.drift,shift:r14Result.shift,selfMin:r14Result.selfMin,envMin:r14Result.envMin,walks:r14Result.walks,bw:r14Base.walks})"))
        print(await pg.inner_text('#r14Results'))
        await pg.screenshot(path='/home/claude/out/t2.png')
        # go to peak, check the page readout
        await ev("r14Go(r14Result.at)"); await pg.wait_for_timeout(200)
        print('metrics',(await pg.inner_text('#metrics'))[:300].replace('\n',' | '))
        # drag a handle
        box=await pg.evaluate("(()=>{const c=document.querySelector('#r14Layer circle[data-j=\"8\"]').getBoundingClientRect();return [c.x+c.width/2,c.y+c.height/2]})()")
        await pg.mouse.move(*box); await pg.mouse.down(); await pg.mouse.move(box[0]+25,box[1]-18,steps=5); await pg.mouse.up()
        print('after drag',await ev("JSON.stringify([r14Sel,r14Edits[8],r14Edits[18]])"))
        await pg.screenshot(path='/home/claude/out/t3.png')
        # reset all -> identical to baseline
        await pg.click('#r14ResetAll'); await pg.wait_for_timeout(200)
        print('reset',await ev("JSON.stringify({pk:Math.max(...r9Motion.poses.map((p,i)=>{r14Climb(i);return r9Loads.climb.loads[i].ratio})),same:r9Motion.poses.every(p=>{const r=r14Store.get(p);return !r||JSON.stringify(r.q0)===JSON.stringify(p.q)}),P:JSON.stringify(r9Pivots)===JSON.stringify(r14P0)})"))
        print('errors',errs)
        await b.close()
asyncio.run(main())
