"""Stránka simulátoru pro revizi R15: ze stránky R13 udělá stránku R15 (pohyb, statika, dynamika, texty, nový oddíl R15).
Výsledek je vstupem pro zdroj/uprava-kloubu/build_r14.py (panel Úprava kloubů). Zároveň obnoví srovnávací data panelu
v zdroj/uprava-kloubu/r14page.json (ref, selfBase, envBase) podle R15.

python3 -I zdroj/r15/stranka_r15.py <Emil-H22-R13-prelez-21cm.html> <výstup.html>
Potřebuje: zdroj/r15/data/ (model.json a vychozi*.json revize R15, zmrazené), zdroj/r15/pohyb-R15.json,
zdroj/r15/dynamika-R15.json (zdroj/r15/dynamika.py) a node (statika ze stejného jádra jako simulátor)."""
import sys, os, re, json, subprocess, tempfile, html as H
TU = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(TU, '..', '..'))
KD = os.path.join(ROOT, 'kontrola'); UK = os.path.join(ROOT, 'zdroj', 'uprava-kloubu')
DATA = os.path.join(TU, 'data')   # zmrazená data R15 (model, srovnávací hodnoty)
VERZE_APLIKACE = '0.5'
src, out = sys.argv[1], sys.argv[2]

def cz(x, d=1): return f'{x:.{d}f}'.replace('.', ',')
def pct(x, d=1): return cz(100 * x, d) + ' %'
def get_block(s, bid):
    m = re.search(r'<script[^>]*id="' + re.escape(bid) + r'"[^>]*>', s); e = s.index('</script>', m.end()); return json.loads(s[m.end():e])
def set_block(s, bid, obj):
    m = re.search(r'<script[^>]*id="' + re.escape(bid) + r'"[^>]*>', s); assert m, bid
    e = s.index('</script>', m.end()); body = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
    return s[:m.end()] + body + s[e:]
def rep(s, old, new, cnt=1):
    assert s.count(old) == cnt, (old[:70], s.count(old)); return s.replace(old, new)

M = json.load(open(os.path.join(DATA, 'model.json'))); assert M.get('revize') == 'R15', 'model.json není R15'
JN = M['JN']; n = len(M['q']); HZ = M['hz']
Q = json.load(open(os.path.join(TU, 'pohyb-R15.json'))); DYN = json.load(open(os.path.join(TU, 'dynamika-R15.json')))
V = json.load(open(os.path.join(DATA, 'vychozi.json'))); ROB = json.load(open(os.path.join(DATA, 'vychozi-robustnost.json')))
assert V.get('revize') == 'R15' and len(Q['q']) == n

def statika(model, pohyb):
    with tempfile.TemporaryDirectory() as d:
        o = os.path.join(d, 's.json'); subprocess.run(['node', os.path.join(TU, 'statika.js'), model, pohyb, o], check=True, capture_output=True)
        return json.load(open(o))
ST = statika(os.path.join(DATA, 'model.json'), os.path.join(TU, 'pohyb-R15.json'))
assert all(ST), 'R15 bez rovnováhy v některé poloze'

s = open(src, encoding='utf-8').read()
assert '<title>Emil H22 R13 · podepření podle Konda a nový přelez 21 cm</title>' in s, 'vstupem musí být stránka R13'

# ---------- R13 hodnoty pro srovnání (stejné jádro) ----------
C13 = get_block(s, 'r9ClimbData')
with tempfile.TemporaryDirectory() as d:
    p13 = os.path.join(d, 'p.json'); json.dump(dict(q=[p['q'] for p in C13['poses']], rt=[p['rt'] for p in C13['poses']]), open(p13, 'w'))
    m13 = os.path.join(d, 'm.json'); M13 = dict(M); M13['q'] = [p['q'] for p in C13['poses']]; M13['rt'] = [p['rt'] for p in C13['poses']]; json.dump(M13, open(m13, 'w'))
    ST13 = statika(m13, p13)
L13 = get_block(s, 'r9LoadsData')['climb']['loads']

# ---------- pohyb ----------
C = dict(C13); C['poses'] = []
for i, p in enumerate(C13['poses']):
    p = dict(p); p['q'] = [round(float(x), 6) for x in Q['q'][i]]; p['rt'] = [round(float(x), 9) for x in Q['rt'][i]]; C['poses'].append(p)
PH = [dict(x) for x in C13['phases']]
PH[2]['description'] = (PH[2]['description'].rstrip() + ' R15: trup je v této fázi posunutý asi o 12 mm ke schodu a 12 mm doprava, aby víc nesla pravá dlaň; '
                        'levá noha zvedá koleno tak, aby minulo hranu schodu nejméně o 3,6 mm.')
C['phases'] = PH
s = set_block(s, 'r9ClimbData', C)

# ---------- zatížení ----------
loads = []
for i, x in enumerate(ST):
    F = {int(k): v for k, v in x['F'].items()}
    lN, rN = F.get(10, 0.0), F.get(20, 0.0)
    loads.append(dict(tau=x['tau'], ratio=x['s'], cm=x['com'], joint=JN[x['j']], palmN=round(max(lN, rN), 3), rightN=round(rN, 3), leftN=round(lN, 3),
                      margin=round(ROB[i]['marg'], 3), kneeN=[round(F.get(5, 0.0), 2), round(F.get(15, 0.0), 2)], footN=[round(F.get(7, 0.0), 2), round(F.get(17, 0.0), 2)],
                      moving=DYN['pomer'][i], movingTau=DYN['moment'][i]))
ratios = [l['ratio'] for l in loads]; k = max(range(n), key=lambda i: ratios[i])
check = dict(peak=[ratios[k], k, loads[k]['joint']], failed=[], over=sum(r > 1 for r in ratios), evaluated=n)
by = {}
for ph in sorted(set(p['phase'] for p in C['poses'])):
    idx = [i for i, p in enumerate(C['poses']) if p['phase'] == ph]; kk = max(idx, key=lambda i: ratios[i])
    by[str(ph)] = dict(peak=[ratios[kk], kk, loads[kk]['joint']], failed=[], over=0, evaluated=len(idx))
L = get_block(s, 'r9LoadsData'); L['climb'] = dict(loads=loads, check=check, byPhase=by)
L['climbSummary'] = f'R15 · {n} / {n} poloh s rovnováhou · maximum {pct(ratios[k])} při součiniteli tření 0,50.'
s = set_block(s, 'r9LoadsData', L)

# ---------- mezery (souhrn; rozpis po dílech zůstává z R13) ----------
emin = min(range(n), key=lambda i: V['env'][i]); smin = min(range(n), key=lambda i: V['self'][i])
Gd = get_block(s, 'r9GeometryData'); Gd['climb']['minima']['environment'].update(mm=round(V['env'][emin], 3), frame=emin)
s = set_block(s, 'r9GeometryData', Gd)
Cl = get_block(s, 'r12ClearanceData')
for c in Cl['cases']:
    if c['name'] == 'climb': c['minMm'] = round(V['self'][smin], 4); c['nearFrames'] = sum(v < 10 for v in V['self'])
Cl['summaryCs'] = (f'R15: přelez schodu 21 cm má nejmenší mezeru mezi díly {cz(V["self"][smin], 2)} mm a odstup od schodu {cz(V["env"][emin], 2)} mm '
                   f'(přesný výpočet ze sítí v automatické kontrole). Rozpis po jednotlivých dílech níže je z R13; R15 se od něj liší jen ve fázi 3 (14–33 s). ' + Cl['summaryCs'])
s = set_block(s, 'r12ClearanceData', Cl)

# ---------- srovnávací data panelu Úprava kloubů ----------
P14 = json.load(open(os.path.join(UK, 'r14page.json')))
assert P14['contacts'] == M['contacts'] and P14['ex'] == M['ex']
P14['ref'] = ratios; P14['selfBase'] = [round(v, 3) for v in V['self']]; P14['envBase'] = [round(v, 3) for v in V['env']]; P14['revize'] = 'R15'
P14['historie'] = [
    dict(rev='R13', datum='2026-11-21', popis='Přelez schodu 21 cm s oporou dlaní a bérců (podle Konda).', max=round(max(x['s'] for x in ST13), 4), self=9.97, env=3.26, dyn='202–215 mm',
         zaklad={}, q=[[round(float(v), 4) for v in p['q']] for p in C13['poses']], rt=[[round(float(v), 5) for v in p['rt']] for p in C13['poses']]),
    dict(rev='R15', datum='2026-11-22', popis='Posun trupu ve fázi 3 (zatížená pravá dlaň), levá noha dál od hrany, přizpůsobení výšce schodu od 30 s.',
         max=round(ratios[k], 4), self=round(V['self'][smin], 2), env=round(V['env'][emin], 2), dyn='202–218 mm', zaklad={}, aktualni=True)]
P14['hz'] = HZ; P14['vyska_od_s'] = M.get('vyska_od_s', 30.0); P14['vyska_nabeh_s'] = M.get('vyska_nabeh_s', 2.0)
json.dump(P14, open(os.path.join(UK, 'r14page.json'), 'w'), separators=(',', ':'))

# ---------- texty ----------
s = rep(s, '<title>Emil H22 R13 · podepření podle Konda a nový přelez 21 cm</title>', '<title>Emil H22 R15 · přelez schodu 21 cm s přizpůsobením výšce</title>')
s = rep(s, '<div class="brand">EMIL H22 / R13 · NEJLEPŠÍ Z OBOU</div>', f'<div class="brand">EMIL H22 / R15 · APLIKACE {VERZE_APLIKACE}</div>')
s = rep(s, '<option value="r9" selected>R13 · pracovní sestava (nový přelez 21 cm)</option>', '<option value="r9" selected>R15 · pracovní sestava (přelez 21 cm)</option>')
s = rep(s, '<option value="r9">Emil H22 R13</option>', '<option value="r9">Emil H22 R15</option>')
a = s.index('"R13 · Rovnováha vyšla ve všech'); b = s.index('"', a + 1)
s = s[:a] + json.dumps(f'R15 · Rovnováha vyšla ve všech {n} polohách, nejvyšší statické využití pohonu je {pct(ratios[k])}. Díly, které se schodu dotýkat nemají, '
                       f'od něj drží nejméně {cz(V["env"][emin], 1)} mm. Dynamická simulace doběhne na schodu 202–218 mm, pokud robot výšku změří a přelez od 30. s přizpůsobí. '
                       'Jde o simulaci, fyzický přelez potvrzený není.', ensure_ascii=False) + s[b + 1:]
s = rep(s, "'R13 · statický moment při nejvýhodnějším rozdělení sil mezi opory", "'R15 · statický moment při nejvýhodnějším rozdělení sil mezi opory")
s = rep(s, "vk('Dynamická simulace R13 · špička momentu serva'", "vk('Dynamická simulace R15 · špička momentu serva'")
s = rep(s, "link.download='Emil-H22-R13-prelez-21cm.html'", "link.download='Emil-H22-R15-prelez-21cm.html'")
s = rep(s, 'Pro kontrolu nových pohybů a dílů zvolte R12.', 'Pro kontrolu nových pohybů a dílů zvolte pracovní sestavu R15 (konstrukce R12, pohyb přelezu R15).')
s = rep(s, 'Přechod na uloženou polohu vybere R12.', 'Přechod na uloženou polohu vybere pracovní sestavu R15.')

# ---------- oddíl R15 ----------
dyn13 = {'202': 'doběhne', '205': 'doběhne', '210': 'doběhne', '215': 'doběhne', '218': 'pád 24,7 s', '222': 'nezkoušeno', '225': 'nezkoušeno'}
dyn15 = {'202': 'doběhne', '205': 'doběhne', '210': 'doběhne', '215': 'doběhne', '218': 'doběhne', '222': 'pád 25,2 s', '225': 'pád 21,7 s'}
r13s = [x['s'] for x in ST13]; r15s = ratios
names = [p['name'] for p in PH]
# graf: využití nejzatíženějšího serva R13 a R15 (stejné jádro, tření 0,5)
W, Hh, ml, mr, mt, mb = 980, 300, 46, 14, 26, 34; T = (n - 1) / HZ
X = lambda i: ml + (W - ml - mr) * (i / HZ) / T; Y = lambda v: mt + (Hh - mt - mb) * (1 - min(v, 1.0))
bands = []; starts = [0] + [i for i in range(1, n) if C['poses'][i]['phase'] != C['poses'][i - 1]['phase']] + [n]
g = []
for j in range(len(starts) - 1):
    a_, b_ = starts[j], starts[j + 1] - 1
    if j % 2 == 0: g.append(f'<rect x="{X(a_):.1f}" y="{mt}" width="{max(1, X(b_) - X(a_)):.1f}" height="{Hh - mt - mb}" fill="#eef1ea"/>')
    g.append(f'<text x="{(X(a_) + X(b_)) / 2:.1f}" y="{mt - 8}" text-anchor="middle" font-size="11" fill="#5d6f67">{j + 1}</text>')
for v in (0, .25, .5, .75, 1):
    g.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#dbe4dc" stroke-width="1"/><text x="{ml - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="#5d6f67">{int(v * 100)} %</text>')
for t in range(0, int(T) + 1, 20):
    g.append(f'<text x="{ml + (W - ml - mr) * t / T:.1f}" y="{Hh - mb + 18}" text-anchor="middle" font-size="11" fill="#5d6f67">{t} s</text>')
path = lambda arr: 'M' + ' L'.join(f'{X(i):.1f} {Y(v):.1f}' for i, v in enumerate(arr))
k13 = max(range(n), key=lambda i: r13s[i])
svg = (f'<svg id="r15Chart" viewBox="0 0 {W} {Hh}" role="img" aria-label="Využití nejzatíženějšího serva během přelezu, R13 a R15">' + ''.join(g) +
       f'<path d="{path(r13s)}" fill="none" stroke="#c2571a" stroke-width="2" stroke-linejoin="round"/>'
       f'<path d="{path(r15s)}" fill="none" stroke="#2a78d6" stroke-width="2" stroke-linejoin="round"/>'
       f'<circle cx="{X(k)}" cy="{Y(r15s[k])}" r="4.5" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2"/>'
       f'<text x="{X(k) - 8:.1f}" y="{Y(r15s[k]) - 8:.1f}" text-anchor="end" font-size="12" fill="#193733">R15 · {pct(r15s[k])}</text>'
       f'<line id="r15Cross" x1="0" x2="0" y1="{mt}" y2="{Hh - mb}" stroke="#193733" stroke-width="1" visibility="hidden"/>'
       f'<rect id="r15Hit" x="{ml}" y="{mt}" width="{W - ml - mr}" height="{Hh - mt - mb}" fill="transparent"/></svg>')
a3, b3 = int(13 * HZ), int(34 * HZ)
X3 = lambda i: ml + (W - ml - mr) * (i - a3) / (b3 - a3); top3 = max(max(r13s[a3:b3]), max(r15s[a3:b3])) * 1.15
Y3 = lambda v: mt + (Hh - mt - mb) * (1 - v / top3)
g3 = []
for v in [x / 10 for x in range(0, 11) if x / 10 <= top3]:
    g3.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y3(v):.1f}" y2="{Y3(v):.1f}" stroke="#dbe4dc"/><text x="{ml - 6}" y="{Y3(v) + 4:.1f}" text-anchor="end" font-size="11" fill="#5d6f67">{int(v * 100)} %</text>')
for t in range(13, 35, 3): g3.append(f'<text x="{X3(t * HZ):.1f}" y="{Hh - mb + 18}" text-anchor="middle" font-size="11" fill="#5d6f67">{t} s</text>')
p3 = lambda arr: 'M' + ' L'.join(f'{X3(i):.1f} {Y3(arr[i]):.1f}' for i in range(a3, b3))
svg3 = (f'<div class="r13-chartwrap"><div class="r13-legend"><span><i style="background:#c2571a"></i>R13</span><span><i style="background:#2a78d6"></i>R15</span><span style="color:#5d6f67">Fáze 3 zblízka (13–34 s): kde se R15 od R13 liší.</span></div>'
        f'<svg id="r15Chart3" viewBox="0 0 {W} {Hh}" role="img" aria-label="Využití serva ve fázi 3, R13 a R15" style="width:100%;height:auto;display:block">' + ''.join(g3) +
        f'<path d="{p3(r13s)}" fill="none" stroke="#c2571a" stroke-width="2"/><path d="{p3(r15s)}" fill="none" stroke="#2a78d6" stroke-width="2"/></svg></div>')
D15 = dict(n=[round(v, 4) for v in r15s], b=[round(v, 4) for v in r13s], jn=[JN[x['j']] for x in ST], jb=[JN[x['j']] for x in ST13],
           ph=[p['phase'] for p in C['poses']], names=names, hz=HZ, geo=dict(ml=ml, mr=mr, W=W, tmax=T), peak=k, f3=int(14.4 * HZ) + 1)
diff = [i for i in range(n) if abs(r15s[i] - r13s[i]) > 0.005]
rows_ph = ''.join(f'<tr><th scope="row">{j + 1}. {H.escape(names[j])}</th><td>{pct(max(r13s[i] for i in range(n) if C["poses"][i]["phase"] == j), 0)}</td>'
                  f'<td><b>{pct(max(r15s[i] for i in range(n) if C["poses"][i]["phase"] == j), 0)}</b></td>'
                  f'<td>{cz(min(ROB[i]["marg"] for i in range(n) if C["poses"][i]["phase"] == j), 1)} mm</td></tr>' for j in range(len(names)))
rows_h = ''.join(f'<tr><th scope="row">{h} mm</th><td class="{"r13-ok" if dyn13[h] == "doběhne" else "r13-no" if dyn13[h].startswith("pád") else ""}">{dyn13[h]}</td>'
                 f'<td class="{"r13-ok" if dyn15[h] == "doběhne" else "r13-no"}">{dyn15[h]}</td></tr>' for h in dyn15)
r = json.load(open(os.path.join(DATA, 'vychozi-dynamika.json')))
sec = f'''<section id="r15" aria-labelledby="r15Title">
<div class="brand">R15 · SIMULACE, FYZICKÝ PŘELEZ ZATÍM NEPOTVRZEN</div>
<h2 id="r15Title">Přelez schodu 21 cm s vyrovnanějšími oporami a přizpůsobením výšce</h2>
<p class="r13-lead">R15 vychází z přelezu R13. Ve fázi 3 je trup posunutý tak, aby víc nesla pravá dlaň, která byla v R13 skoro bez zatížení, levá noha přenáší koleno dál od hrany schodu
a robot po změření výšky schodu (dotykem dlaně) od 30. sekundy přizpůsobí zbytek přelezu. V simulaci tak doběhne na schodu <b>202–218 mm</b> místo 202–215 mm.</p>
<div class="r13-kpis"><div class="r13-kpi"><span>Nejvyšší využití serva</span><b>{pct(ratios[k])}</b><small>R13: {pct(max(r13s))} · statika, tření 0,50</small></div>
<div class="r13-kpi"><span>Výška schodu, kterou zvládne</span><b>202–218 mm</b><small>R13: 202–215 mm · výška změřená přesně</small></div>
<div class="r13-kpi"><span>Odstup dílů od schodu</span><b>{cz(V["env"][emin], 1)} mm</b><small>R13: 3,3 mm · mezera mezi díly {cz(V["self"][smin], 1)} mm</small></div>
<div class="r13-kpi"><span>Slabá místa rovnováhy</span><b>208 poloh</b><small>R13: 239 · nejslabší opora 0,5 N (R13: 0,0 N)</small></div></div>
<div class="r13-actions"><button type="button" class="mainbtn" id="r15Play">Přehrát přelez R15 v modelu</button><button type="button" id="r15F3">Skočit na fázi 3 (změna oproti R13)</button><button type="button" id="r15Peak">Skočit na nejtěžší polohu</button></div>
<details class="rev-more"><summary>Celá zpráva R15 – graf zatížení, výška schodu, změny, kontroly a historie</summary>
<div class="r13-chartwrap"><div class="r13-legend"><span><i style="background:#c2571a"></i>R13</span><span><i style="background:#2a78d6"></i>R15</span><span style="color:#5d6f67">Využití nejzatíženějšího serva, 100 % = pracovní moment, tření 0,50. Čísla nahoře jsou fáze. Liší se jen fáze 3 ({len(diff)} poloh).</span></div>{svg}<div id="r15Tip"></div></div>
{svg3}
<div class="r13-note">Výšku schodu v modelu změníš vpravo u přelezu (Výška schodu v modelu): poloha a statika se přepočítají v prohlížeči. Zda robot nespadne, počítá jen dynamika v automatické kontrole. Výsledky jsou ze simulace bez zpětné vazby; skutečný robot musí výšku schodu změřit asi na ±2 mm.</div>
<details open><summary>Co se oproti R13 změnilo</summary><ul>
<li><b>Fáze 3 (14–30 s):</b> trup posunutý asi o 12 mm ke schodu a 12 mm doprava. Pravá dlaň, bez které by robot nestál, nese místo 0 N aspoň 0,5 N; v R13 se na vyšším schodu odlepila a robot se převrátil.</li>
<li><b>Levá noha ve fázi 3</b> zvedá koleno tak, aby minulo hranu schodu: odstup {cz(V["env"][emin], 2)} mm (bez úpravy by posun trupu přitáhl koleno ke hraně na 0,3 mm).</li>
<li><b>Přizpůsobení výšce schodu:</b> robot výšku změří dotykem dlaně a od 30. s ji během 2 s promítne do zbytku přelezu (cíle nad schodem a pánev o rozdíl výšky). Na 210 mm se nic nemění.</li>
<li>Ostatní fáze, místa opor, pohony a rozměry jsou stejné jako v R13.</li></ul></details>
<details open><summary>Výška schodu v dynamické simulaci</summary><div class="r13-scroll"><table><thead><tr><th>Schod</th><th>R13</th><th>R15</th></tr></thead><tbody>{rows_h}</tbody></table></div>
<p>R15 předpokládá, že robot výšku schodu změří. Na 218 mm vydrží chybu měření −5 až +2 mm. Nad 218 mm se robot ve fázi 3 nakloní o 5–6° dozadu a pravá dlaň ztratí kontakt, ještě než se přelez stihne přizpůsobit.</p></details>
<details><summary>Kontroly R15 (automatická kontrola v GitHubu)</summary><div class="r13-scroll"><table><thead><tr><th>Kontrola</th><th>R15</th></tr></thead><tbody>
<tr><th scope="row">Rovnováha ve všech polohách, tření 0,50 / 0,40 / 0,30</th><td class="r13-ok">všech {n}</td></tr>
<tr><th scope="row">Nejvyšší využití serva (mez 85 %)</th><td class="r13-ok">{pct(ratios[k])} · {H.escape(loads[k]["joint"])}, {cz(k / HZ, 1)} s</td></tr>
<tr><th scope="row">Mezera mezi díly (mez 9 mm)</th><td class="r13-ok">{cz(V["self"][smin], 2)} mm</td></tr>
<tr><th scope="row">Odstup od podlahy a schodu (mez 3 mm)</th><td class="r13-ok">{cz(V["env"][emin], 2)} mm</td></tr>
<tr><th scope="row">Opory zůstávají na místě</th><td class="r13-ok">0,0 mm</td></tr>
<tr><th scope="row">Dynamika: jmenovitě, tření 0,35, hmotnost +10 %, o 5 mm blíž, serva 85 %, schod 202–218 mm</th><td class="r13-ok">{sum(r.values())} z {len(r)} variant doběhne</td></tr>
</tbody></table></div><p>Statika a mezery jsou z výpočtu, odstupy mají nejistotu asi ±2 mm (zjednodušené sítě). Krátké špičky momentu na mezi serva ukazuje dynamika i v R13.</p></details>
<details><summary>Zatížení po fázích (R13 → R15)</summary><div class="r13-scroll"><table><thead><tr><th>Fáze</th><th>R13</th><th>R15</th><th>Nejmenší rezerva těžiště R15</th></tr></thead><tbody>{rows_ph}</tbody></table></div></details>
<details><summary>Co se zkoušelo a nepomohlo</summary><ul>
<li>Vyvažování v simulaci (těžiště, náklon, reflex dlaní) – robustnost nezvýšilo.</li>
<li>Regulace sil v oporách přes QP – serva STS řídí jen polohu, převod síly na povel je slabý (požadavek +5 N dá asi +0,5 N); schod 222 a 225 mm dál padá.</li>
<li>Pevný plán bez přizpůsobení výšce – na 218 mm vždy pád.</li></ul>
<p>Podrobnosti: repozitář <code>vypocty/robustnost-2026-11-22/README.md</code>.</p></details>
<details class="r15-hist"><summary>Předchozí revize R13 – původní zpráva</summary><p>Následující zpráva popisuje R13 (srovnání s R12). Model nahoře už přehrává R15; tlačítka ve zprávě skáčou do pohybu R15.</p>'''
JS = r"""(function(){const D=JSON.parse($('r15Data').textContent),svg=$('r15Chart'),tip=$('r15Tip'),cross=$('r15Cross'),hit=$('r15Hit'),wrap=svg.parentElement;
 const pc=v=>(100*v).toFixed(0)+' %';
 function at(e){const r=svg.getBoundingClientRect(),vx=(e.clientX-r.left)/r.width*D.geo.W,t=Math.max(0,Math.min(D.geo.tmax,(vx-D.geo.ml)/(D.geo.W-D.geo.ml-D.geo.mr)*D.geo.tmax));return {t,vx}}
 hit.addEventListener('pointermove',e=>{const {t,vx}=at(e),i=Math.round(t*D.hz),w=wrap.getBoundingClientRect();cross.setAttribute('x1',vx);cross.setAttribute('x2',vx);cross.setAttribute('visibility','visible');
  const rows=[t.toFixed(0)+' s · fáze '+(D.ph[i]+1)+' '+D.names[D.ph[i]],'R15 · '+pc(D.n[i])+' · '+D.jn[i],'R13 · '+pc(D.b[i])+' · '+D.jb[i]];
  tip.replaceChildren(...rows.map(x=>{const d=document.createElement('div');d.textContent=x;return d}));tip.style.left=Math.max(120,Math.min(w.width-120,e.clientX-w.left))+'px';tip.style.top=(e.clientY-w.top)+'px';tip.style.visibility='visible'});
 hit.addEventListener('pointerleave',()=>{tip.style.visibility='hidden';cross.setAttribute('visibility','hidden')});
 function go(i,play){if(document.body.classList.contains('kondo-active'))return;if(mode!=='climb'){for(const b of document.querySelectorAll('button[data-mode]'))if(b.dataset.mode==='climb'){b.click();break}}stop();idx=Math.max(0,Math.min(i,climbData.poses.length-1));render();$('stage').scrollIntoView({behavior:'smooth',block:'center'});if(play)$('play').click()}
 hit.addEventListener('click',e=>go(Math.round(at(e).t*D.hz)));hit.style.cursor='pointer';
 $('r15Play').onclick=()=>go(0,true);$('r15F3').onclick=()=>go(D.f3);$('r15Peak').onclick=()=>go(D.peak);
})();"""
i0 = s.index('<section id="r13" aria-labelledby="r13Title">'); i1 = s.index('</section>', i0) + len('</section>')
css = '<style>#r15{border:1px solid #9cb7d6;border-radius:13px;background:#fffdf6;padding:clamp(14px,2vw,26px);margin:0 0 22px}#r15 h2{font:normal clamp(24px,3vw,36px)/1.12 Georgia,serif;letter-spacing:-.02em;margin:2px 0 8px}#r15 p{max-width:95ch;margin:6px 0}#r15 .r13-lead{font-size:16px}#r15 .r13-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:14px 0}#r15 .r13-chartwrap{position:relative;border:1px solid #cfdbd1;border-radius:9px;background:#fcfcfb;padding:8px 8px 2px;margin:8px 0}#r15Chart{width:100%;height:auto;display:block}#r15 .r13-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#274f46;padding:2px 6px 6px}#r15 .r13-legend i{display:inline-block;width:18px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}#r15Tip{position:absolute;pointer-events:none;background:#193733;color:#fff;font-size:12.5px;line-height:1.35;padding:6px 9px;border-radius:6px;white-space:nowrap;transform:translate(-50%,-110%);visibility:hidden;z-index:2}#r15 table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0}#r15 th,#r15 td{border-bottom:1px solid #dbe4dc;padding:5px 8px;text-align:left;vertical-align:top}#r15 thead th{font-weight:600;color:#3d5a50;border-bottom:1px solid #9fb5a9}#r15 details{border-top:1px solid #cfdbd1;padding:9px 0}#r15 summary{cursor:pointer;font-weight:600;font-size:15px}#r15 .r13-scroll{overflow-x:auto}#r15 .r13-actions{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 4px}#r15 .r13-note{background:#f3ece0;border-left:3px solid #ad653a;padding:8px 12px;border-radius:0 7px 7px 0;margin:10px 0}#r15 ul{margin:6px 0;padding-left:20px;max-width:95ch}#r15 li{margin:3px 0}#r15 .r15-hist>section#r13{margin-top:10px}</style>'
s = s[:i0] + css + sec + s[i0:i1] + '</details></details></section>' + '<script type="application/json" id="r15Data">' + json.dumps(D15, separators=(',', ':'), ensure_ascii=False) + '</script>' + s[i1:]
s = rep(s, "choose('climb');(function(){const D=JSON.parse($('r13Data')", "choose('climb');" + JS + "(function(){const D=JSON.parse($('r13Data')")
open(out, 'w', encoding='utf-8').write(s)
print('R15 stránka', len(s), 'znaků · max', pct(ratios[k]), 'v', k, loads[k]['joint'], '· odstup', round(V['env'][emin], 2), 'mm · mezera', round(V['self'][smin], 2), 'mm')
