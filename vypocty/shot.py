import asyncio, json, sys
from playwright.async_api import async_playwright
async def main(src,out,frame,extra=''):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1400,'height':1000})
        errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
        await pg.goto('file://'+src)
        await pg.wait_for_function('document.documentElement.dataset.ready==="true"',timeout=60000)
        await pg.select_option('#kAssembly','r9')
        await pg.wait_for_timeout(500)
        await pg.evaluate('__ev("choose(\'climb\')")')
        await pg.evaluate(f'__ev("idx={frame};render()")')
        if extra: await pg.evaluate(extra)
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=out,full_page=False)
        print(errs)
        await b.close()
asyncio.run(main(sys.argv[1],sys.argv[2],int(sys.argv[3])))
