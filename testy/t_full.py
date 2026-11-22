import asyncio, json, sys
from playwright.async_api import async_playwright
async def run(url,hooked):
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1400,'height':950})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)+' || '+(e.stack or '')[:600])); pg.on('console',lambda m:errs.append('C:'+m.text) if m.type=='error' else None)
        await pg.goto(url); await pg.wait_for_function('document.documentElement.dataset.ready==="true"',timeout=60000)
        await pg.evaluate("document.getElementById('stage').scrollIntoView({block:'center'})")
        await pg.click('#r14Toggle')
        await pg.select_option('#r14Joint','4'); await pg.check('#r14Carry')
        await pg.fill('#r14N2','-12'); await pg.dispatch_event('#r14N2','change')
        await pg.select_option('#r14Joint','8'); await pg.fill('#r14N0','4'); await pg.dispatch_event('#r14N0','change'); await pg.fill('#r14N2','6'); await pg.dispatch_event('#r14N2','change')
        await pg.evaluate("(()=>{const r=document.getElementById('r14Rot');r.value=45;r.dispatchEvent(new Event('input'))})()")
        await pg.select_option('#r14Joint','5'); await pg.fill('#r14N1','3'); await pg.dispatch_event('#r14N1','change'); await pg.fill('#r14N2','8'); await pg.dispatch_event('#r14N2','change')
        await pg.click('#r14RunBtn'); await pg.wait_for_function("document.querySelector('#r14Results table')",timeout=180000)
        txt=await pg.inner_text('#r14Results'); print(txt[:520])
        if hooked: print('res',await pg.evaluate('(s)=>__ev(s)',"JSON.stringify({pk:r14Result.pk,at:r14Result.at,bad:r14Result.bad,drift:r14Result.drift,shift:r14Result.shift})"))
        await pg.click('#r14Results .r14-link'); await pg.wait_for_timeout(300); await pg.screenshot(path='/home/claude/out/t4.png')
        for m in ['walk','home','sit','dance','stairs','turn','pickup','climb']:
            btn=await pg.query_selector(f'button[data-mode="{m}"]')
            if btn: await btn.click(); await pg.wait_for_timeout(350); print(m,len(errs),(await pg.inner_text('#metrics'))[:110].replace('\n',' | '))
            else: print('no mode',m)
        await pg.click('#play'); await pg.wait_for_timeout(1500); await pg.click('#play')
        opts=await pg.evaluate("[...document.getElementById('kAssembly').options].map(o=>o.value)"); print(opts)
        cur='r9'; print('before asm',len(errs))
        for v in opts+[cur]:
            await pg.evaluate("(v)=>{const e=document.getElementById('kAssembly');e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}))}",v); await pg.wait_for_timeout(600)
        print('kondo class',await pg.evaluate("document.body.classList.contains('kondo-active')"));print('panel visible',await pg.is_visible('#r14Toggle'))
        await pg.click('#r14ExportBtn') if False else None
        await pg.evaluate("document.querySelector('#r14 details').open=true")
        async with pg.expect_download() as dl: await pg.click('#r14ExportBtn')
        d=await dl.value; path=await d.path(); js=json.load(open(path)); print('export',list(js['upravy'].keys()),js['souhrn'] is not None)
        await pg.click('#r14ResetAll'); await pg.click('#r14ImportBtn'); await pg.wait_for_timeout(300)
        print('state',await pg.inner_text('#r14State'), '|', await pg.inner_text('#r14Progress'))
        k=await pg.query_selector('#kAssembly')
        print('errors',errs)
        await b.close()
asyncio.run(run('file:///home/claude/out/Emil-H22-R14-uprava-kloubu.html',False))

