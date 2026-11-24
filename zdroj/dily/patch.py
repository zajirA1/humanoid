"""Vloží výběr a prohlížeč dílů do sestavené stránky. Opakované spuštění aktualizuje zdrojové bloky."""
from pathlib import Path
import argparse
import re

TU = Path(__file__).resolve().parent

def jednou(text, old, new):
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f"Nelze bezpečně vložit prohlížeč dílů: {old[:110]}")
    return text.replace(old, new, 1)

def aplikuj(text):
    # Ovládací prvky a vlastní modální okno patří k hlavnímu modelu.
    text = jednou(text, '<button id="region">', '<button type="button" id="r16PartToggle" aria-pressed="true">Výběr dílů</button><button type="button" id="r16PartCatalog">Katalog dílů</button><button id="region">')
    text = jednou(text, 'Kliknutím na servo zobrazíš jeho hodnoty.', 'Výběr dílů otevře klepnutím detail součásti. Vypnutím přepneš klepnutí zpět na výběr serva.')
    # Původní scéna (včetně podlahy a překážek) má hloubku; překrytý díl se tak nikdy nevybere skrz schod.
    text = jednou(text, 'return {add,paint};\n}\n\nconst rnd=', 'return {add,paint,geometry:key=>meshes[key]};\n}\n\nconst rnd=')
    text = jednou(text, 'cmd.push(form(key,mat(w[o.link],o.t),r12SelectedColor(r12Hit,key,o.link,r12ItemIndex,color)))', 'cmd.push([...form(key,mat(w[o.link],o.t),r12SelectedColor(r12Hit,key,o.link,r12ItemIndex,color)),{key:r9IsActive()?(r14Key0?.[r12ItemIndex]||o.key):o.key,index:r12ItemIndex,link:o.link,owner:o.owner,t:o.t}])')
    text = jednou(text, 'cmd.push(form(cover.key,w[cover.link],r12SelectedColor(r12Hit,cover.key,cover.link,r12Hit?r9RenderItems.length+r9Covers().indexOf(cover):null,hex(cover.color))))', 'cmd.push([...form(cover.key,w[cover.link],r12SelectedColor(r12Hit,cover.key,cover.link,r12Hit?r9RenderItems.length+r9Covers().indexOf(cover):null,hex(cover.color))),{key:cover.key,link:cover.link,owner:cover.link,t:I}])')
    text = jednou(text, "cmd.push(form('ball',mat(w[k],at(s*146,-12,205,12,12,12)),'pad'))", "cmd.push([...form('ball',mat(w[k],at(s*146,-12,205,12,12,12)),'pad'),{key:'opora_dlane',link:k,owner:k,t:at(s*146,-12,205,12,12,12)}])")
    text = jednou(text, 'cmd.push([o.key,mat(w[o.link],o.t),r12SelectedColor(r12Hit,o.key,o.link,null,o.color)])', 'cmd.push([o.key,mat(w[o.link],o.t),r12SelectedColor(r12Hit,o.key,o.link,null,o.color),{key:o.key,link:o.link,owner:o.owner,t:o.t}])')
    text = jednou(text, "o.move==='lower'?25:26),null,o.color)])", "o.move==='lower'?25:26),null,o.color),{key:o.key,link:o.link,owner:o.owner,t:o.t}])")
    text = jednou(text, 'r14Cmd(cmd,w);const project=', 'r14Cmd(cmd,w);r16Parts?.capture(cmd,target,az,el,span/zoom);const project=')
    text = jednou(text, 'const hit=r10HitMotor(e.clientX-rect.left,e.clientY-rect.top,e.pointerType', 'if(r16Parts?.tap(e))return;\n  const hit=r10HitMotor(e.clientX-rect.left,e.clientY-rect.top,e.pointerType')
    # Přepis zdrojových bloků funguje i při pozdější změně inspektoru.
    for name,data,opening,closing,anchor in [
        ('css', (TU/'panel.css').read_text(), '<style id="r16InspectorStyle">', '</style>', '</head>'),
        ('panel', (TU/'panel.html').read_text(), '<!--R16-DILY-PANEL-->', '<!--/R16-DILY-PANEL-->', '</main><main id="kViewer"'),
        ('script', (TU/'picking.js').read_text()+'\n'+(TU/'panel.js').read_text()+'\nvar r16Parts=r16CreateParts();', '/* R16-DILY-ZACATEK */', '/* R16-DILY-KONEC */', 'r14Ready=true;')
    ]:
        block=opening+'\n'+data+'\n'+closing
        if opening in text:
            text=re.sub(re.escape(opening)+'.*?'+re.escape(closing),lambda _:block,text,flags=re.S,count=1)
        else:
            text=jednou(text,anchor,block+'\n'+anchor)
    return text

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('soubor',type=Path);cli.add_argument('vystup',type=Path,nargs='?')
    args=cli.parse_args();(args.vystup or args.soubor).write_text(aplikuj(args.soubor.read_text()))
