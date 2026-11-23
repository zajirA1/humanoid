"""Vloží do horního oddílu revize rozpis mezer po dílech a kontrolu posunutých serv vůči vlastnímu rámu.

python3 -I zdroj/revize/rozpis_stranka.py <rozpis.json> [stránka]   (výchozí stránka web/app/emil-h22.html)
rozpis.json vytváří kontrola/rozpis.py. Opakované spuštění blok nahradí (nic se nezdvojí).
"""
import sys, os, re, json, html as H
TU = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(TU, '..', '..'))
STRANKA = os.path.join(ROOT, 'web', 'app', 'emil-h22.html')
def cz(x, d=1): return f'{x:.{d}f}'.replace('.', ',')
CSS = ('<style id="revRozpisCss">.rev-warn{border:1px solid #c0392b;background:#fff4f1;border-radius:9px;padding:10px 14px;margin:10px 0;max-width:95ch}'
       '.rev-warn b{color:#9b2c1f}.rev-sec td.r13-no{color:#9b2c1f;font-weight:600}</style>')

def vloz(s, rz, rev=None, prev=None):
    rev = rev or rz.get('revize'); pid = 'rev' + rev
    a = s.index(f'<section id="{pid}" class="rev-sec"')
    # staré vložení pryč (idempotentní)
    s = re.sub(r'<p class="rev-warn" id="revServa">.*?</p>', '', s, flags=re.S)
    s = re.sub(r'<details id="revRozpis"[^>]*>.*?</details><!--/revRozpis-->', '', s, flags=re.S)
    if 'id="revRozpisCss"' not in s: s = s[:a] + CSS + s[a:]
    a = s.index(f'<section id="{pid}" class="rev-sec"')
    var = rz.get('varovani') or []
    zm = [r for r in rz.get('sousedni', []) if r['stav'] != 'beze změny']
    novy = [r for r in zm if r['stav'] in ('nový dotyk', 'blíž pod 2 mm')]
    if var:
        dily = list(dict.fromkeys(r['a'].split(' (')[0] + ' × ' + r['b'].split(' (')[0] for r in novy))
        warn = (f'<p class="rev-warn" id="revServa"><b>Pozor – posunutá serva se v modelu dotýkají rámu i po jeho přizpůsobení.</b> Kontrola po jednotlivých dílech našla {len(novy)} nových dotyků nebo průniků '
                f'(proti {H.escape(prev or "předchozí revizi")}): {H.escape("; ".join(dily[:4]))}{" a další" if len(dily) > 4 else ""}. Automatická kontrola mezery mezi články kloubu a uvnitř jednoho článku '
                'nevidí, proto revize prošla. Než se podle ní bude stavět, je potřeba rám upravit ručně nebo změnit posun serva. Podrobně v rozpisu níže.</p>')
    else:
        warn = ''
    k = s.index('</div></div>', s.index('class="r13-kpis"', a)) + len('</div></div>')
    s = s[:k] + warn + s[k:]
    rows_d = ''.join(f'<tr><th scope="row">{H.escape(d["a"])} × {H.escape(d["b"])}</th><td>{cz(d["mm"], 2)} mm</td><td>{cz(d["cas_s"], 1)} s</td></tr>' for d in rz.get('dvojice', [])[:12])
    rows_s = ''.join(f'<tr><th scope="row">{H.escape(r["a"])}</th><td>{H.escape(r["b"])}</td><td>{H.escape(r["druh"])}</td><td>{cz(r["mm"], 2)} mm</td><td>{cz(r["mm_pred"], 2)} mm</td>'
                     f'<td class="{"r13-no" if r in novy else ""}">{H.escape(r["stav"])}</td></tr>' for r in zm[:30])
    blok = (f'<details id="revRozpis"{" open" if var else ""}><summary>Mezery po dílech {H.escape(rev)} a posunutá serva × vlastní rám</summary>'
            f'<p>Nejbližší dvojice nezávislých dílů ve výchozím pohybu {H.escape(rev)} ({rz.get("poloh")} poloh, přesný výpočet ze sítí dílů jako v automatické kontrole):</p>'
            f'<div class="r13-scroll"><table><thead><tr><th>Dvojice dílů</th><th>Minimum</th><th>Čas</th></tr></thead><tbody>{rows_d}</tbody></table></div>')
    if zm:
        blok += (f'<p>Díly u posunutých kloubů po jednotlivých dílech proti {H.escape(prev or "předchozí revizi")} (servo a jeho rám, článek kloubu a rodič). Ve stejném článku a v kloubu se díly '
                 'stýkají záměrně, proto je automatická kontrola vynechává; tady se hlásí jen to, co se posunem změnilo. Rám je už přizpůsobený posunu (okolí serva se posune s ním). '
                 'Varování = nový dotyk nebo přiblížení pod 2 mm.</p>'
                 f'<div class="r13-scroll"><table><thead><tr><th>Díl</th><th>Proti</th><th>Kde</th><th>{H.escape(rev)}</th><th>{H.escape(prev or "předtím")}</th><th>Stav</th></tr></thead><tbody>{rows_s}</tbody></table></div>')
    blok += f'<p>{H.escape(rz.get("poznamka", ""))}</p></details><!--/revRozpis-->'
    k = s.index('<details><summary>Co tato revize neověřuje</summary>', a)
    s = s[:k] + blok + s[k:]
    # texty o tom, co se nekontroluje
    for stary in ('Úchyty jsou jen zjednodušené desky; pevnost, tvar pro tisk a střet serva s vlastním rámem se nekontrolují.',
                  'Úchyty jsou jen zjednodušené desky; pevnost a tvar pro tisk se nekontrolují. Střet serva s rámem se kontroluje jen po sítích původních dílů – dokreslené úchyty v nich nejsou.'):
        s = s.replace(stary, 'Rám je přizpůsobený jen plynulým přetvořením (kontrola/ram.py); pevnost a tvar pro tisk se nekontrolují, střety přetvořeného rámu hlásí rozpis po dílech.', 1)
    s = s.replace('Měděné desky v modelu jsou dokreslené úchyty (bočnice a příčka vidlice) – zjednodušené, rozměry podle původní vidlice, nejsou to díly k tisku.',
                  'Rám se v modelu sám přizpůsobí posunu serva: okolí pouzdra, páky a vidlice se posune spolu se servem a plynule přejde do zbytku rámu – zjednodušené přetvoření, ne díl k tisku.', 1)
    s = s.replace('úchyty jsou dokreslené zjednodušeně', 'rám se jim přizpůsobí zjednodušeně', 1)
    s = s.replace('Rozpis mezer po dílech v dialogu Mezery dílů je z R13.', f'Rozpis mezer po dílech pro přelez {rev} je v oddílu výše; dialog Mezery dílů (ostatní pohyby) je z R13.', 1)
    s = s.replace('Rozpis po jednotlivých dílech níže je z R13.', f'Rozpis přelezu po dílech je v oddílu {rev} nahoře; dialog níže (ostatní pohyby) je z R13.', 1)
    return s

if __name__ == '__main__':
    rz = json.load(open(sys.argv[1])); p = sys.argv[2] if len(sys.argv) > 2 else STRANKA
    M = json.load(open(os.path.join(ROOT, 'kontrola', 'data', 'model.json')))
    prev = ((M.get('historie') or [{}])[-1]).get('z')
    s = open(p, encoding='utf-8').read(); s = vloz(s, rz, rz.get('revize'), prev); open(p, 'w', encoding='utf-8').write(s)
    print('vloženo', rz.get('revize'), 'varování', len(rz.get('varovani') or []))
