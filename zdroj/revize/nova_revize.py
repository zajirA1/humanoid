"""Nová revize robota z prošlého přepočtu úpravy kloubů.

python3 -I zdroj/revize/nova_revize.py <složka přepočtu> [--bez-prepoctu]
Složka přepočtu = obsah prepocty/<id>/ z větve „prepocty“ (uprava.json, vysledek.json, volitelně pohyb.json).

Postup (nic nenasazuje):
 1. ověří, že přepočet prošel, byl plný (ne rychlý) a počítal se vůči současné revizi,
 2. pohyb přizpůsobený úpravě (pohyb.json z přepočtu, nebo ho spočítá znovu) se stane výchozím pohybem nové revize,
    posuny serv se zapečou do model.json jako „zaklad“ (osa, servo, hmotnost; visící díly přes E),
 3. plná kontrola nové revize s --vychozi (srovnávací hodnoty kontrola/data/vychozi*.json), musí projít,
 4. jmenovitá dynamika po polohách, statika ze stejného jádra jako stránka,
 5. stránka web/app/emil-h22.html: nový pohyb a zatížení, zapečené posuny (servo posunuté, rám přizpůsobený),
    nový oddíl revize nahoře (předchozí oddíl sbalený jako historie), texty a verze aplikace +0.1,
 6. podklady revize do zdroj/revize/R<N>/ (úprava, protokoly, pohyb, dynamika, rozpis mezer po dílech, info.json);
    rozpis (kontrola/rozpis.py) hlásí i dotyky posunutých serv s vlastním rámem – jen varování, revize kvůli nim nespadne.
Rám se posunu serva přizpůsobí plynulým přetvořením (kontrola/ram.py, v prohlížeči r14RamDeform), ne díl k tisku."""
import sys, os, re, json, shutil, subprocess, tempfile, datetime, html as H
TU = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(TU, '..', '..'))
KD = os.path.join(ROOT, 'kontrola'); DATA = os.path.join(KD, 'data'); STRANKA = os.path.join(ROOT, 'web', 'app', 'emil-h22.html')
UK = os.path.join(ROOT, 'zdroj', 'uprava-kloubu')
def log(*a): print('[nová revize]', *a, flush=True)
def cz(x, d=1): return f'{x:.{d}f}'.replace('.', ',')
def pct(x, d=1): return cz(100 * x, d) + ' %'
def get_block(s, bid):
    m = re.search(r'<script[^>]*id="' + re.escape(bid) + r'"[^>]*>', s); e = s.index('</script>', m.end()); return json.loads(s[m.end():e])
def set_block(s, bid, obj):
    m = re.search(r'<script[^>]*id="' + re.escape(bid) + r'"[^>]*>', s); assert m, bid
    e = s.index('</script>', m.end()); body = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
    return s[:m.end()] + body + s[e:]
def sub1(s, pat, new, flags=0):
    s2, k = re.subn(pat, lambda m: new, s, count=1, flags=flags); assert k == 1, pat; return s2
def merge(base, user):
    """stejné složení jako r14engine.mergeEdits: d se sčítá, E = posun visících dílů, natočení se sčítá"""
    out = {}
    for src in (base or {}, user or {}):
        for k, e in src.items():
            d = [float(x) for x in e.get('d', [0, 0, 0])]; E = [float(x) for x in e['E']] if 'E' in e else (d if e.get('carry') else [0.0, 0.0, 0.0])
            o = out.setdefault(str(k), dict(d=[0.0] * 3, E=[0.0] * 3, rot=0.0))
            for a in range(3): o['d'][a] = round(o['d'][a] + d[a], 4); o['E'][a] = round(o['E'][a] + E[a], 4)
            o['rot'] = round(o['rot'] + float(e.get('rot', 0) or 0), 3)
    return out
def prepocet(uprava, vystup, vychozi=False):
    cmd = [sys.executable, '-I', os.path.join(KD, 'prepocet.py'), uprava, vystup] + (['--vychozi'] if vychozi else [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(vystup, 'log.txt'), 'w').write(p.stdout + p.stderr)
    if p.returncode != 0: sys.exit('Přepočet skončil chybou:\n' + (p.stdout + p.stderr)[-3000:])
    return json.load(open(os.path.join(vystup, 'vysledek.json')))

def main():
    src = sys.argv[1]; bez = '--bez-prepoctu' in sys.argv
    U = json.load(open(os.path.join(src, 'uprava.json'))); R = json.load(open(os.path.join(src, 'vysledek.json')))
    M = json.load(open(os.path.join(DATA, 'model.json'))); prev = M.get('revize', 'R13'); N = int(prev[1:]) + 1; rev = f'R{N}'
    idp = os.path.basename(os.path.normpath(src))
    if not R.get('proslo'): sys.exit('Přepočet neprošel – nová revize z něj vzniknout nemůže.')
    if R.get('rychla'): sys.exit('Přepočet byl rychlý – pro novou revizi je potřeba plná kontrola.')
    if R.get('revize', 'R13') != prev: sys.exit(f'Přepočet se počítal vůči {R.get("revize")}, současná revize je {prev}. Odešli úpravu znovu.')
    if not U.get('upravy'): sys.exit('Úprava je prázdná.')
    user = {str(j): dict(d=e['posun_mm'], carry=bool(e.get('nese_dalsi_dily')), rot=float(e.get('natoceni_serva_deg', 0) or 0)) for j, e in U['upravy'].items()}
    work = tempfile.mkdtemp(prefix='revize-')
    # ---- 1. pohyb přizpůsobený úpravě ----
    pohyb = os.path.join(src, 'pohyb.json')
    if os.path.exists(pohyb) and json.load(open(pohyb)).get('upravy') == U['upravy']:
        log('pohyb z přepočtu', idp)
    else:
        if bez: sys.exit('V přepočtu chybí pohyb.json a --bez-prepoctu nedovoluje ho spočítat.')
        log('počítám pohyb přizpůsobený úpravě (plná kontrola, asi 12 min)')
        d1 = os.path.join(work, 'uprava'); os.makedirs(d1); json.dump(U, open(os.path.join(d1, 'uprava.json'), 'w'), ensure_ascii=False)
        R1 = prepocet(os.path.join(d1, 'uprava.json'), d1)
        if not R1['proslo']: sys.exit('Úprava při opakovaném přepočtu neprošla.')
        pohyb = os.path.join(d1, 'pohyb.json')
    P1 = json.load(open(pohyb))
    # ---- 2. model nové revize ----
    stare = {f: json.load(open(os.path.join(DATA, f))) for f in ('vychozi.json', 'vychozi-robustnost.json', 'vychozi-dynamika.json')}
    zaklad = merge(M.get('zaklad', {}), user)
    kl = ', '.join(f"{M['JN'][int(j)]} {[round(float(x), 1) for x in e['posun_mm']]} mm" for j, e in U['upravy'].items())
    M2 = dict(M); M2['zaklad'] = zaklad; M2['q'] = P1['q']; M2['rt'] = P1['rt']; M2['revize'] = rev
    M2['revize_popis'] = f'{prev} + úprava kloubů z přepočtu {idp}: {kl}'
    M2['historie'] = (M.get('historie') or []) + [dict(revize=rev, z=prev, prepocet=idp, upravy=U['upravy'], zaklad_z=M.get('zaklad', {}), datum=datetime.date.today().isoformat())]
    json.dump(M2, open(os.path.join(DATA, 'model.json'), 'w'), separators=(',', ':'))
    log('model', rev, 'zapečeno kloubů', len(zaklad))
    # ---- 3. plná kontrola nové revize + srovnávací hodnoty ----
    d2 = os.path.join(work, 'vychozi'); os.makedirs(d2); json.dump({}, open(os.path.join(d2, 'nula.json'), 'w'))
    log('plná kontrola nové revize (--vychozi, asi 12 min)')
    R2 = prepocet(os.path.join(d2, 'nula.json'), d2, vychozi=True)
    if not R2['proslo']:
        json.dump(M, open(os.path.join(DATA, 'model.json'), 'w'), separators=(',', ':'))
        for f, v in stare.items(): json.dump(v, open(os.path.join(DATA, f), 'w'))
        sys.exit('Nová revize v plné kontrole neprošla – model vrácen. Protokol: ' + os.path.join(d2, 'protokol.md'))
    V = json.load(open(os.path.join(DATA, 'vychozi.json'))); ROB = json.load(open(os.path.join(DATA, 'vychozi-robustnost.json')))
    # ---- 4. podklady revize, dynamika, statika ----
    out = os.path.join(ROOT, 'zdroj', 'revize', rev); os.makedirs(out, exist_ok=True)
    Q = json.load(open(os.path.join(d2, 'pohyb.json'))); json.dump(dict(revize=rev, q=Q['q'], rt=Q['rt']), open(os.path.join(out, 'pohyb.json'), 'w'), separators=(',', ':'))
    for f in ('uprava.json', 'vysledek.json', 'protokol.md'):
        if os.path.exists(os.path.join(src, f)): shutil.copy(os.path.join(src, f), os.path.join(out, 'prepocet-' + f))
    shutil.copy(os.path.join(d2, 'protokol.md'), os.path.join(out, 'kontrola-revize.md')); shutil.copy(os.path.join(d2, 'vysledek.json'), os.path.join(out, 'kontrola-revize.json'))
    log('rozpis mezer po dílech a posunutá serva × vlastní rám')
    subprocess.run([sys.executable, '-I', os.path.join(KD, 'rozpis.py'), os.path.join(out, 'rozpis.json'), '--krok', '2'], check=True)
    RZ = json.load(open(os.path.join(out, 'rozpis.json')))
    log('dynamika po polohách')
    subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'zdroj', 'r15', 'dynamika.py'), os.path.join(out, 'pohyb.json'), os.path.join(out, 'dynamika.json')], check=True)
    DYN = json.load(open(os.path.join(out, 'dynamika.json')))
    with tempfile.TemporaryDirectory() as d:
        o = os.path.join(d, 's.json'); subprocess.run(['node', os.path.join(ROOT, 'zdroj', 'r15', 'statika.js'), os.path.join(DATA, 'model.json'), os.path.join(out, 'pohyb.json'), o], check=True, capture_output=True)
        ST = json.load(open(o))
    assert all(ST), 'bez rovnováhy'
    # ---- 5. stránka ----
    s = open(STRANKA, encoding='utf-8').read(); n = len(ST); JN = M['JN']; HZ = M['hz']
    P14 = get_block(s, 'r14Data'); assert P14.get('revize', 'R13') == prev, f'stránka je {P14.get("revize")}, model {prev}'
    m = re.search(r'APLIKACE (\d+)\.(\d+)', s); va = f'{m.group(1)}.{int(m.group(2)) + 1}'
    Lold = get_block(s, 'r9LoadsData'); rprev = [l['ratio'] for l in Lold['climb']['loads']]
    C = get_block(s, 'r9ClimbData')
    stare_q = [[round(float(v), 4) for v in p['q']] for p in C['poses']]; stare_rt = [[round(float(v), 5) for v in p['rt']] for p in C['poses']]
    for i, p in enumerate(C['poses']): p['q'] = [round(float(x), 6) for x in Q['q'][i]]; p['rt'] = [round(float(x), 9) for x in Q['rt'][i]]
    s = set_block(s, 'r9ClimbData', C)
    loads = []
    for i, x in enumerate(ST):
        F = {int(k): v for k, v in x['F'].items()}; lN, rN = F.get(10, 0.0), F.get(20, 0.0)
        loads.append(dict(tau=x['tau'], ratio=x['s'], cm=x['com'], joint=JN[x['j']], palmN=round(max(lN, rN), 3), rightN=round(rN, 3), leftN=round(lN, 3),
                          margin=round(ROB[i]['marg'], 3), kneeN=[round(F.get(5, 0.0), 2), round(F.get(15, 0.0), 2)], footN=[round(F.get(7, 0.0), 2), round(F.get(17, 0.0), 2)],
                          moving=DYN['pomer'][i], movingTau=DYN['moment'][i]))
    ratios = [l['ratio'] for l in loads]; k = max(range(n), key=lambda i: ratios[i])
    by = {}
    for ph in sorted(set(p['phase'] for p in C['poses'])):
        idx = [i for i, p in enumerate(C['poses']) if p['phase'] == ph]; kk = max(idx, key=lambda i: ratios[i])
        by[str(ph)] = dict(peak=[ratios[kk], kk, loads[kk]['joint']], failed=[], over=0, evaluated=len(idx))
    Lold['climb'] = dict(loads=loads, check=dict(peak=[ratios[k], k, loads[k]['joint']], failed=[], over=sum(r > 1 for r in ratios), evaluated=n), byPhase=by)
    Lold['climbSummary'] = f'{rev} · {n} / {n} poloh s rovnováhou · maximum {pct(ratios[k])} při součiniteli tření 0,50.'
    s = set_block(s, 'r9LoadsData', Lold)
    emin = min(range(n), key=lambda i: V['env'][i]); smin = min(range(n), key=lambda i: V['self'][i])
    Gd = get_block(s, 'r9GeometryData'); Gd['climb']['minima']['environment'].update(mm=round(V['env'][emin], 3), frame=emin); s = set_block(s, 'r9GeometryData', Gd)
    Cl = get_block(s, 'r12ClearanceData')
    for c in Cl['cases']:
        if c['name'] == 'climb': c['minMm'] = round(V['self'][smin], 4); c['nearFrames'] = sum(v < 10 for v in V['self'])
    Cl['summaryCs'] = re.sub(r'^R\d+: .*?(?=V \d+ pohybech|R13 nahrazuje)', '', Cl['summaryCs'])
    Cl['summaryCs'] = (f'{rev}: přelez schodu 21 cm má nejmenší mezeru mezi díly {cz(V["self"][smin], 2)} mm a odstup od schodu {cz(V["env"][emin], 2)} mm '
                       f'(přesný výpočet ze sítí v automatické kontrole, s posunutými servy). Rozpis po jednotlivých dílech níže je z R13. ' + Cl['summaryCs'])
    s = set_block(s, 'r12ClearanceData', Cl)
    HIST = P14.get('historie') or []
    for h in HIST:
        if h.get('aktualni'):
            h['aktualni'] = False; h.update(q=stare_q, rt=stare_rt, zaklad=M.get('zaklad', {}))
    HIST.append(dict(rev=rev, datum=datetime.date.today().isoformat(), popis=f'Posunutá serva z přepočtu {idp}: {kl}.', max=round(ratios[k], 4), self=round(V['self'][smin], 2),
                  env=round(V['env'][emin], 2), dyn=f"{sum(bool(v.get('uspech')) for v in R2['dynamika'].values())}/{len(R2['dynamika'])} variant doběhne", zaklad=zaklad, aktualni=True))
    P14['historie'] = HIST
    P14.update(ref=ratios, selfBase=[round(v, 3) for v in V['self']], envBase=[round(v, 3) for v in V['env']], revize=rev, zaklad=zaklad, hz=HZ,
               vyska_od_s=M2.get('vyska_od_s', 30.0), vyska_nabeh_s=M2.get('vyska_nabeh_s', 2.0))
    s = set_block(s, 'r14Data', P14)
    # texty
    s = sub1(s, r'<title>Emil H22 R\d+ · [^<]*</title>', f'<title>Emil H22 {rev} · přelez schodu 21 cm, posunutá serva</title>')
    s = sub1(s, r'<div class="brand">EMIL H22 / R\d+ · APLIKACE [\d.]+</div>', f'<div class="brand">EMIL H22 / {rev} · APLIKACE {va}</div>')
    s = sub1(s, r'<option value="r9" selected>R\d+ · pracovní sestava \(přelez 21 cm\)</option>', f'<option value="r9" selected>{rev} · pracovní sestava (přelez 21 cm)</option>')
    s = sub1(s, r'<option value="r9">Emil H22 R\d+</option>', f'<option value="r9">Emil H22 {rev}</option>')
    s = sub1(s, r'"R\d+ · Rovnováha vyšla ve všech[^"]*"', json.dumps(f'{rev} · Rovnováha vyšla ve všech {n} polohách, nejvyšší statické využití pohonu je {pct(ratios[k])}. '
             f'Díly, které se schodu dotýkat nemají, od něj drží nejméně {cz(V["env"][emin], 1)} mm. Serva jsou posunutá podle úpravy {idp}, rám se jim přizpůsobí zjednodušeně. '
             'Jde o simulaci, fyzický přelez potvrzený není.', ensure_ascii=False))
    s = sub1(s, r"'R\d+ · statický moment při nejvýhodnějším rozdělení sil mezi opory", f"'{rev} · statický moment při nejvýhodnějším rozdělení sil mezi opory")
    s = sub1(s, r"vk\('Dynamická simulace R\d+ · špička momentu serva'", f"vk('Dynamická simulace {rev} · špička momentu serva'")
    s = sub1(s, r"link\.download='Emil-H22-R\d+-prelez-21cm\.html'", f"link.download='Emil-H22-{rev}-prelez-21cm.html'")
    s = sub1(s, r'zvolte pracovní sestavu R\d+ \(konstrukce R12[^)]*\)', f'zvolte pracovní sestavu {rev} (konstrukce R12 s posunutými servy, pohyb přelezu {rev})')
    s = sub1(s, r'vybere pracovní sestavu R\d+\.', f'vybere pracovní sestavu {rev}.')
    # oddíl revize
    dyn_prev = stare['vychozi-dynamika.json']; dyn_new = {kk: bool(v.get('uspech')) for kk, v in R2['dynamika'].items()}
    rows_j = ''.join(f'<tr><th scope="row">{H.escape(M["JN"][int(j)])}</th><td>{" / ".join(cz(float(x), 1) for x in e["posun_mm"])}</td><td>{"ano" if e.get("nese_dalsi_dily") else "ne"}</td></tr>' for j, e in sorted(U['upravy'].items(), key=lambda x: int(x[0])))
    rows_d = ''.join(f'<tr><th scope="row">{H.escape(kk)}</th><td class="{"r13-ok" if dyn_prev.get(kk) else "r13-no"}">{"doběhne" if dyn_prev.get(kk) else "pád"}</td>'
                     f'<td class="{"r13-ok" if dyn_new[kk] else "r13-no"}">{"doběhne" if dyn_new[kk] else "pád"} · {cz(R2["dynamika"][kk].get("odchylka_konec_mm", 0), 1)} mm</td></tr>' for kk in dyn_new)
    rows_k = ''.join(f'<tr><th scope="row">{H.escape(x["nazev"])}</th><td class="{"r13-ok" if x["ok"] else "r13-no"}">{H.escape(x["hodnota"])}</td></tr>' for x in R2['kontroly'])
    W, Hh, ml, mr, mt, mb = 980, 260, 46, 14, 20, 30; T = (n - 1) / HZ
    X = lambda i: ml + (W - ml - mr) * (i / HZ) / T; Y = lambda v: mt + (Hh - mt - mb) * (1 - min(v, 1.0))
    g = []
    for v in (0, .25, .5, .75, 1): g.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#dbe4dc"/><text x="{ml - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="#5d6f67">{int(v * 100)} %</text>')
    for t in range(0, int(T) + 1, 20): g.append(f'<text x="{ml + (W - ml - mr) * t / T:.1f}" y="{Hh - mb + 18}" text-anchor="middle" font-size="11" fill="#5d6f67">{t} s</text>')
    path = lambda arr: 'M' + ' L'.join(f'{X(i):.1f} {Y(v):.1f}' for i, v in enumerate(arr))
    pid = 'rev' + rev
    svg = (f'<svg id="{pid}Chart" viewBox="0 0 {W} {Hh}" role="img" aria-label="Využití nejzatíženějšího serva, {prev} a {rev}" style="width:100%;height:auto;display:block">' + ''.join(g) +
           f'<path d="{path(rprev)}" fill="none" stroke="#c2571a" stroke-width="2" stroke-linejoin="round"/><path d="{path(ratios)}" fill="none" stroke="#2a78d6" stroke-width="2" stroke-linejoin="round"/>'
           f'<circle cx="{X(k):.1f}" cy="{Y(ratios[k]):.1f}" r="4.5" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2"/><text x="{X(k) - 8:.1f}" y="{Y(ratios[k]) - 8:.1f}" text-anchor="end" font-size="12" fill="#193733">{rev} · {pct(ratios[k])}</text>'
           f'<line id="{pid}Cross" x1="0" x2="0" y1="{mt}" y2="{Hh - mb}" stroke="#193733" visibility="hidden"/><rect id="{pid}Hit" x="{ml}" y="{mt}" width="{W - ml - mr}" height="{Hh - mt - mb}" fill="transparent" style="cursor:pointer"/></svg>')
    rp, rn = stare['vychozi-robustnost.json'], ROB
    slab = lambda L: sum(1 for o in L if o['marg'] < 15 or o['fnez'] < 5)
    sec = f'''<section id="{pid}" class="rev-sec" data-revize="{rev}" aria-labelledby="{pid}Title">
<div class="brand">{rev} · SIMULACE, FYZICKÝ PŘELEZ ZATÍM NEPOTVRZEN</div>
<h2 id="{pid}Title">Posunutá serva podle úpravy {H.escape(idp)}</h2>
<p class="r13-lead">{rev} vychází z {prev}. Serva níže jsou natrvalo posunutá, přelez je přizpůsobený nové geometrii a znovu prošel plnou kontrolou. Rám se v modelu sám přizpůsobí posunu serva: okolí pouzdra, páky a vidlice se posune spolu se servem a plynule přejde do zbytku rámu – zjednodušené přetvoření, ne díl k tisku.</p>
<div class="r13-kpis"><div class="r13-kpi"><span>Nejvyšší využití serva</span><b>{pct(ratios[k])}</b><small>{prev}: {pct(max(rprev))} · statika, tření 0,50</small></div>
<div class="r13-kpi"><span>Mezera mezi díly</span><b>{cz(V["self"][smin], 1)} mm</b><small>{prev}: {cz(min(stare["vychozi.json"]["self"]), 1)} mm · mez 9 mm</small></div>
<div class="r13-kpi"><span>Odstup dílů od schodu</span><b>{cz(V["env"][emin], 1)} mm</b><small>{prev}: {cz(min(stare["vychozi.json"]["env"]), 1)} mm · mez 3 mm</small></div>
<div class="r13-kpi"><span>Slabá místa rovnováhy</span><b>{slab(rn)} poloh</b><small>{prev}: {slab(rp)}</small></div></div>
<details class="rev-more"><summary>Celá zpráva {rev} – graf, posunutá serva, kontroly, dynamika a předchozí revize</summary>
<div class="r13-chartwrap"><div class="r13-legend"><span><i style="background:#c2571a"></i>{prev}</span><span><i style="background:#2a78d6"></i>{rev}</span><span style="color:#5d6f67">Využití nejzatíženějšího serva během přelezu, 100 % = pracovní moment.</span></div>{svg}<div id="{pid}Tip" class="rev-tip"></div></div>
<details open><summary>Posunutá serva</summary><div class="r13-scroll"><table><thead><tr><th>Kloub</th><th>Posun do strany / dozadu / nahoru, mm</th><th>Posunout i visící díly</th></tr></thead><tbody>{rows_j}</tbody></table></div>
<p>Posun je v základní poloze robota: x + k levému boku, y + dozadu, z + nahoru. Další úpravy v panelu Úprava kloubů se k těmto posunům přičítají.</p></details>
<details><summary>Plná kontrola {rev}</summary><div class="r13-scroll"><table><thead><tr><th>Kontrola</th><th>{rev}</th></tr></thead><tbody>{rows_k}</tbody></table></div></details>
<details><summary>Dynamická simulace ({prev} → {rev})</summary><div class="r13-scroll"><table><thead><tr><th>Varianta</th><th>{prev}</th><th>{rev}</th></tr></thead><tbody>{rows_d}</tbody></table></div></details>
<details><summary>Co tato revize neověřuje</summary><ul><li>Rám je přizpůsobený jen plynulým přetvořením (kontrola/ram.py); pevnost a tvar pro tisk se nekontrolují, střety přetvořeného rámu hlásí rozpis po dílech.</li>
<li>Pohyb je přizpůsobený nové geometrii a švih volných končetin doladěný; trup ani rozložení sil se znovu neoptimalizují.</li>
<li>Rozpis mezer po dílech v dialogu Mezery dílů je z R13. Odstupy mají nejistotu asi ±2 mm.</li><li>Fyzicky nic neověřeno.</li></ul></details>
<details class="r15-hist"><summary>Předchozí revize {prev}</summary>'''
    JS = ("(function(){const D=JSON.parse($('" + pid + "Data').textContent),svg=$('" + pid + "Chart'),tip=$('" + pid + "Tip'),cross=$('" + pid + "Cross'),hit=$('" + pid + "Hit'),wrap=svg.parentElement;const pc=v=>(100*v).toFixed(0)+' %';"
          "function at(e){const r=svg.getBoundingClientRect(),vx=(e.clientX-r.left)/r.width*D.W,t=Math.max(0,Math.min(D.T,(vx-D.ml)/(D.W-D.ml-D.mr)*D.T));return {t,vx}}"
          "hit.addEventListener('pointermove',e=>{const {t,vx}=at(e),i=Math.round(t*D.hz),w=wrap.getBoundingClientRect();cross.setAttribute('x1',vx);cross.setAttribute('x2',vx);cross.setAttribute('visibility','visible');"
          "tip.replaceChildren(...[t.toFixed(0)+' s',D.rev+' · '+pc(D.n[i]),D.prev+' · '+pc(D.b[i])].map(x=>{const d=document.createElement('div');d.textContent=x;return d}));tip.style.left=Math.max(80,Math.min(w.width-80,e.clientX-w.left))+'px';tip.style.top=(e.clientY-w.top)+'px';tip.style.visibility='visible'});"
          "hit.addEventListener('pointerleave',()=>{tip.style.visibility='hidden';cross.setAttribute('visibility','hidden')});"
          "hit.addEventListener('click',e=>{if(mode!=='climb'){for(const b of document.querySelectorAll('button[data-mode]'))if(b.dataset.mode==='climb'){b.click();break}}stop();idx=Math.max(0,Math.min(Math.round(at(e).t*D.hz),climbData.poses.length-1));render();$('stage').scrollIntoView({behavior:'smooth',block:'center'})});})();")
    D = dict(n=[round(v, 4) for v in ratios], b=[round(v, 4) for v in rprev], hz=HZ, W=W, ml=ml, mr=mr, T=T, rev=rev, prev=prev)
    css = ('<style>.rev-sec{border:1px solid #c9a17e;border-radius:13px;background:#fffdf6;padding:clamp(14px,2vw,26px);margin:0 0 22px}.rev-sec h2{font:normal clamp(24px,3vw,36px)/1.12 Georgia,serif;letter-spacing:-.02em;margin:2px 0 8px}'
           '.rev-sec p{max-width:95ch;margin:6px 0}.rev-sec .r13-lead{font-size:16px}.rev-sec .r13-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:14px 0}'
           '.rev-sec .r13-chartwrap{position:relative;border:1px solid #cfdbd1;border-radius:9px;background:#fcfcfb;padding:8px 8px 2px;margin:8px 0}.rev-sec .r13-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#274f46;padding:2px 6px 6px}'
           '.rev-sec .r13-legend i{display:inline-block;width:18px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}.rev-tip{position:absolute;pointer-events:none;background:#193733;color:#fff;font-size:12.5px;line-height:1.35;padding:6px 9px;border-radius:6px;white-space:nowrap;transform:translate(-50%,-110%);visibility:hidden;z-index:2}'
           '.rev-sec table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0}.rev-sec th,.rev-sec td{border-bottom:1px solid #dbe4dc;padding:5px 8px;text-align:left;vertical-align:top}.rev-sec thead th{font-weight:600;color:#3d5a50;border-bottom:1px solid #9fb5a9}'
           '.rev-sec details{border-top:1px solid #cfdbd1;padding:9px 0}.rev-sec summary{cursor:pointer;font-weight:600;font-size:15px}.rev-sec .r13-scroll{overflow-x:auto}.rev-sec ul{margin:6px 0;padding-left:20px;max-width:95ch}</style>')
    a_ = s.index('<aside id="r14"'); i0 = s.index('<section', a_)
    depth, pos = 0, i0                         # konec předchozího horního oddílu (vnořené <section> se počítají)
    for mm in re.finditer(r'<section\b|</section>', s[i0:]):
        depth += 1 if mm.group(0) != '</section>' else -1
        if depth == 0: pos = i0 + mm.end(); break
    s = s[:i0] + ('' if '.rev-sec{' in s else css) + sec + s[i0:pos] + '</details></details></section>' + f'<script type="application/json" id="{pid}Data">' + json.dumps(D, separators=(',', ':')) + '</script>' + s[pos:]
    s = sub1(s, r"choose\('climb'\);", "choose('climb');" + JS)
    sys.path.insert(0, TU); import rozpis_stranka
    s = rozpis_stranka.vloz(s, RZ, rev, prev)
    open(STRANKA, 'w', encoding='utf-8').write(s)
    info = dict(revize=rev, predchozi=prev, prepocet=idp, verze_aplikace=va, datum=datetime.datetime.now().isoformat(timespec='seconds'), upravy=U['upravy'], zaklad=zaklad,
                souhrn=dict(max_vyuziti=ratios[k], mezera_dilu_mm=V['self'][smin], odstup_schod_mm=V['env'][emin], dynamika=dyn_new), varovani_serva_ram=RZ.get('varovani', []))
    json.dump(info, open(os.path.join(out, 'info.json'), 'w'), ensure_ascii=False, indent=1)
    log(f'hotovo: {rev}, aplikace {va}, max {pct(ratios[k])}, mezera {cz(V["self"][smin], 2)} mm, odstup {cz(V["env"][emin], 2)} mm, dynamika {sum(dyn_new.values())}/{len(dyn_new)}')
    print(f'REVIZE={rev}\nVERZE={va}')

if __name__ == '__main__': main()
