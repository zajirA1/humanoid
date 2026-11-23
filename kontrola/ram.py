"""Rám se sám přizpůsobí posunu serva (stejný výpočet je v prohlížeči: r14ui.js, r14RamDeform).

U každého posunutého kloubu j se rám nosného článku (rodič j) v okolí pouzdra serva, páky a vidlice posune spolu
se servem o d a rám hnaného článku (j) v okolí páky a vidlice o d − E (E nese kinematika). Oblast = obálka (AABB)
těchto dílů v původní poloze (souřadnice článku v základní poloze) rozšířená o R0; za ní posun plynule klesá k nule na vzdálenosti R = max(R_MIN, K·|posun|),
takže se rám nepřeloží (spád posunu je nejvýš 1/K). Posuny od více kloubů se sčítají.
Zjednodušení: tvar rámu se jen plynule přetvoří (žádné nové žebro ani výřez), tloušťka stěn v přechodu se mění.
Není to díl k tisku; střety přetvořeného rámu s ostatními díly hlásí kontrola (rozpis.py).
"""
import numpy as np
R0 = 5.0       # mm kolem obálky dílů serva, kde se rám posouvá celý (stejně jako r14Ram.R0 v r14ui.js)
R_MIN = 25.0   # mm nejkratší přechod
K = 1.6        # přechod nejméně 1,6 × posun

def _hladke(t):
    t = np.clip(t, 0.0, 1.0); return 1.0 - t * t * (3.0 - 2.0 * t)

def oblasti(items, edits, PAR):
    """[(link rámu, lo, hi, posun)] pro každou posunutou stranu kloubu; items s klíči link/owner/kind/frame/v (původní poloha)."""
    out = []
    for k, e in (edits or {}).items():
        j = int(k)
        if j >= 22: continue
        d = np.array(e.get('d', [0, 0, 0]), float)
        E = np.array(e['E'], float) if 'E' in e else (d.copy() if e.get('carry') else np.zeros(3))
        for link, D in ((PAR[j], d), (j, d - E)):
            if np.linalg.norm(D) < 0.05: continue
            # nosný rám: obálka pouzdra serva i páky a vidlice (ty se v souhrnu posunou také o d); hnaný rám: páka a vidlice
            kde = (PAR[j], j) if link == PAR[j] else (j,)
            vs = [it['_v0'] for it in items if it['owner'] == j and it['link'] in kde and it['kind'] == 'cad' and not it['frame']]
            if not vs: continue
            V = np.vstack(vs); out.append((link, V.min(0) - R0, V.max(0) + R0, D))
    return out

def posun_bodu(P, link, obl):
    """posun vrcholů P (n×3, souřadnice článku) rámu na článku link"""
    S = np.zeros_like(P)
    for l, lo, hi, D in obl:
        if l != link: continue
        g = np.maximum(np.maximum(lo - P, P - hi), 0.0); dist = np.sqrt((g * g).sum(1))
        R = max(R_MIN, K * float(np.linalg.norm(D)))
        S += _hladke(dist / R)[:, None] * D[None, :]
    return S

def prizpusob(items, edits, PAR):
    """items: seznam dictů s 'v' (n×3 numpy, původní poloha) – rámy se přetvoří na místě; vrátí počet změněných rámů"""
    for it in items: it['_v0'] = it['v']
    obl = oblasti(items, edits, PAR); n = 0
    if obl:
        for it in items:
            if it['frame'] and it['kind'] == 'cad' and any(l == it['link'] for l, *_ in obl):
                S = posun_bodu(it['v'], it['link'], obl)
                if np.abs(S).max() > 1e-6: it['v'] = it['v'] + S; it['_ram'] = True; n += 1
    for it in items: it.pop('_v0', None)
    return n
