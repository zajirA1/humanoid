"""Časová optimalizace přelezu a její nezávislé přehrání v kontaktním modelu.

python kontrola/tempo_schodu.py zdroj/revize/R16/tempo-schodu.json
Výpočet vyžaduje Node, numpy, scipy, mujoco==3.3.7 a python-fcl==0.7.0.11.
"""
import argparse
import hashlib
import json
import tempfile
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

import mujoco
import numpy as np
from scipy.ndimage import gaussian_filter1d, maximum_filter1d
import prepocet as P

KONTROLA = Path(__file__).resolve().parent
MODEL = KONTROLA / "data" / "model.json"
RYCHLY_CAS = 18.5
ZDROJE = {
    "STS3215-C018": "https://ftservo.github.io/ftservo-wiki/en/products/models/st-3215-c018/main/",
    "STS3250-C001": "https://www.feetechrc.com/Data/feetechrc/upload/file/20240120/6384135881578380868917773.pdf",
    "XL330-M288-T": "https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/",
}
# Pořadí z modelu (krk, dále levá a pravá končetina). Dvě serva v boční kyčli
# zvyšují moment. Otáčky výstupu při spřažení zůstávají stejné.
OSY = ["XL330-M288-T"] * 2 + ([
    "STS3215-C018", "STS3250-C001", "STS3250-C001", "STS3250-C001",
    "STS3250-C001", "STS3215-C018", "STS3215-C018", "STS3215-C018",
    "STS3215-C018", "XL330-M288-T",
] * 2)
RYCHLOST = {"XL330-M288-T": 103*6, "STS3215-C018": 60/0.222, "STS3250-C001": 60/0.133}
RYCHLOST_OS = np.array([RYCHLOST[nazev] for nazev in OSY])
# Přepočet poměru blokovacího a jmenovitého momentu zachová projektové
# nerovnoměrné rozdělení zátěže ve dvojici. XL330 má projektovou mez 0,104 Nm.
POMER_MOMENTU = {"XL330-M288-T": 0.52/0.104, "STS3215-C018": 30/10, "STS3250-C001": 50/16}
POHON = {
    "naprazdno_deg_s": RYCHLOST_OS,
    "blokovani_nm": P.LIM * [POMER_MOMENTU[nazev] for nazev in OSY],
}
ZATEZ = {
    "nominál": (210, {}),
    "schod 205 mm": (205, {}),
    "schod 215 mm": (215, {}),
    "tření 0,35": (210, {"mu": 0.35}),
    "hmotnost +10 %": (210, {"mass_scale": 1.1}),
    "serva 85 %": (210, {"lim_scale": 0.85}),
    "o 5 mm blíž": (210, {"y_offset": -5.0}),
}

def nacti_prizpusobeni():
    vystup = {}
    with tempfile.TemporaryDirectory() as adresar:
        vstup = Path(adresar) / "uprava.json"
        soubor = Path(adresar) / "polohy.json"
        for vyska in (205, 210, 215):
            vstup.write_text(json.dumps({"vyska_dh": vyska-P.STEP}))
            subprocess.run(["node", str(KONTROLA/"prizpusob.js"), str(MODEL),
                            str(vstup), str(soubor)], check=True, capture_output=True)
            data = json.loads(soubor.read_text())
            polohy = data["frames"]
            ff = np.array([p["ff"] or [0]*22 for p in polohy])
            ff[:, [11, 21]] = 0
            data["dopredny_moment"] = gaussian_filter1d(ff, 1.5, axis=0, mode="nearest")
            vystup[vyska] = data
    return vystup

def casova_osa(delka, profil):
    # Δt se prodlouží tam, kde se některé servo skutečně rychle otáčí.
    q = np.array([p["q"] for p in DATA[210]["frames"]])
    minima = np.max(np.abs(np.diff(q, axis=0))/RYCHLOST_OS, axis=1)
    if profil == "rovnoměrný":
        return np.linspace(0., delka, len(q))
    if profil in ("10 s přenos opor", "rychlý 210 mm"):
        okoli = gaussian_filter1d(maximum_filter1d(minima, 3), 2)
        dolni_mez = np.maximum(minima/0.98, okoli*0.72) + 0.0002
        if profil == "10 s přenos opor":
            # Čas navíc kolem vstupu na koleno, přenesení váhy z chodidla
            # a usazení obou kolen. Tato varianta stále selhává při dalším přenosu.
            stredy = [114, 190, 270, 325, 460, 728, 870]
            sirky = [38, 40, 40, 38, 55, 65, 60]
            zesileni = [14.644302002987121, 17.72923967944406, 1.9327490460095291,
                        3.143957026444997, 6.377949540486385, 0.4336092963312265, 0.12217137409815916]
            x = np.arange(len(minima))[:, None]
            vaha = 0.18 + np.exp(-0.5*((x-stredy)/sirky)**2) @ zesileni
        else:
            skupiny = [(2,3), (4,5,6), (7,8), (9,10,11,12), (13,14), (0,1,15,16)]
            zesileni = [1., 0.91, 0.93, 1.18, 1.18, 0.9]
            faze = np.array(P.M["phase"][:-1])
            vaha = gaussian_filter1d(sum(np.isin(faze,g)*v for g,v in zip(skupiny,zesileni)), 4)
        vaha *= okoli+0.002
        zbyva = delka - dolni_mez.sum()
        if zbyva < 0:
            raise ValueError("Doba je kratší než spodní mez rychlosti zvoleného profilu.")
        return np.r_[0., np.cumsum(dolni_mez+zbyva*vaha/vaha.sum())]
    # Širší filtr dává běžnému profilu čas na přenos váhy a navázání opory.
    okno, sigma, zaklad = (3, 2, 0.0008) if profil == "10 s" else (7, 5, 0.0035)
    okoli = gaussian_filter1d(maximum_filter1d(minima, okno), sigma)
    intervaly = np.maximum(minima, okoli) + zaklad
    return np.r_[0., np.cumsum(intervaly) / sum(intervaly) * delka]

def geometrie_pohybu(stavy, casy, data, vyska):
    # Stejná pravidla záměrných opor a sítě jako v základní kontrole. Vlastní
    # kopie procesu dovoluje použít skutečnou výšku schodu v kontrole povrchů.
    puvodni = P.STEP
    P.STEP = vyska
    minima = {"dily": (float("inf"), None, None), "okoli": (float("inf"), None, None)}
    vzorku = 0
    try:
        for R, poloha, uhly, t in stavy[::2]:   # 50 Hz záznam → 25 Hz kontrola sítí
            if t < 0:
                continue
            i = int(np.rint(np.interp(t, casy, np.arange(len(casy)))))
            svet = P.fk(uhly, list(R.T.ravel()) + list(poloha), data["P"], data["E"])
            d, par, e, dil = P.mezery(G, PARY, svet, P.M["ex"][i])
            vzorku += 1
            if d < minima["dily"][0]:
                minima["dily"] = (d, t, par)
            if e < minima["okoli"][0]:
                minima["okoli"] = (e, t, dil)
    finally:
        P.STEP = puvodni
    return {
        "vzorky": vzorku, "hz": 25,
        **{k: {"mm": round(float(mm), 3), "t_s": round(float(t), 3), "dil": dil}
           for k, (mm, t, dil) in minima.items()},
    }

def vypocti(zadani):
    delka, profil, varianta, detaily, kontroluj_mezery = zadani
    vyska, parametry = ZATEZ[varianta]
    data = DATA[vyska]
    polohy = data["frames"]
    casy = casova_osa(delka, profil)
    pomery = np.abs(np.diff([p["q"] for p in polohy], axis=0)) / (np.diff(casy)[:,None] * RYCHLOST_OS)
    uzel, kloub = np.unravel_index(pomery.argmax(), pomery.shape)
    r, stavy = P.simuluj(polohy, data["P"], data["E"], data["links"], G,
                        data["dopredny_moment"], casy_s=casy, pohon=POHON,
                        hz_zaznamu=50, step_h=vyska, momenty="uzly" if detaily else False,
                        **parametry)
    r["rychlost_povelu_pomer"] = float(pomery[uzel, kloub])
    r["rychlost_povelu_kloub"] = P.JN[kloub]
    r["rychlost_povelu_cas_s"] = float(casy[uzel])
    # Vyžadujeme dokončení už na konci rozvrhu a znovu po 3 s ustálení.
    r["dokoncil"] = bool(r["uspech"] and r["pad_s"] is None and
                         r["odchylka_pri_dokonceni_mm"] < 25 and
                         r["naklon_pri_dokonceni_deg"] < 8 and
                         min(r["chodidla_na_schodu_N"] + r["chodidla_po_ustaleni_N"]) > 0.5 and
                         r["rychlost_povelu_pomer"] <= 1)
    if kontroluj_mezery:
        r["mezery_skutecne_simulace"] = geometrie_pohybu(stavy, casy, data, vyska)
    if detaily:
        r["moment"] = r.pop("_momenty_uzlu")
        r["casy_s"] = np.round(casy, 8).tolist()
        # Stav po integračním kroku nese čas t+dt, původní kontrola vrací t.
        # Vzorky z náběhu a ustálení slouží i k interpolaci přesných krajů.
        dt = 0.001
        zaznam_t = np.array([t + dt for _, _, _, t in stavy])
        zaznam_xyz = np.array([p for _, p, _, _ in stavy])
        panev = np.array(P.M["PEL"])
        skutecna_panev = np.array([R @ panev + p for R, p, _, _ in stavy])
        cil_trupu = np.array([P.rt2T(p["rt"])[1] for p in polohy])
        cil_panve = np.array([P.rt2T(p["rt"])[0] @ panev + p["rt"][9:] for p in polohy])
        def interpoluj(body):
            return np.stack([np.interp(casy, zaznam_t, osa) for osa in body.T], axis=1)
        skutecny_trup = interpoluj(zaznam_xyz)
        panev_v_case = interpoluj(skutecna_panev)
        r["odchylka_mm"] = np.linalg.norm(skutecny_trup - cil_trupu, axis=1).round(3).tolist()
        r["odchylka_panve_mm"] = np.linalg.norm(panev_v_case - cil_panve, axis=1).round(3).tolist()
        r["panev_mm"] = panev_v_case.round(3).tolist()
        # Po pádu model nemá kolizní povrchy celého těla. Ukazujeme jen
        # začátek pádu, původ souřadnic a pořadí matic jsou shodné s R16.
        konec = delka if r["dokoncil"] else min(delka, (r["pad_s"] or delka) + 1.0)
        idx = np.flatnonzero((zaznam_t >= -dt/2) & (zaznam_t <= konec + dt/2))
        vybrane = sorted(set([*idx[::2], idx[-1]]))
        r["zaznam"] = [
            {"t": round(float(zaznam_t[j]), 4), "q": np.round(stavy[j][2], 4).tolist(),
             "rt": np.round(np.r_[stavy[j][0].T.ravel(), stavy[j][1]], 6).tolist()}
            for j in vybrane
        ]
        if not r["dokoncil"]:
            for j in np.flatnonzero(casy > r["zaznam"][-1]["t"]):
                r["odchylka_mm"][j] = r["odchylka_panve_mm"][j] = r["panev_mm"][j] = None
    return r

def popisy_ui(vystup):
    bezny, pokus = vystup["vybrany"], vystup["cil_10_s"]
    def cs(hodnota, mista):
        return f"{hodnota:.{mista}f}".replace(".", ",")
    minima = bezny["mezery_skutecne_simulace"]
    zvolene_zkousky = next(z["varianty"] for z in vystup["zkousky"] if z["delka_s"]==bezny["delka_s"] and z["profil"]=="běžný")
    mezera205 = zvolene_zkousky["schod 205 mm"]["mezery_skutecne_simulace"]["okoli"]["mm"]
    odhad205 = (f"Na 205mm schodu kontrola povrchů zjistila průnik {cs(-mezera205,1)} mm."
                if mezera205<0 else f"Na schodu 205 mm je mezera od okolí {cs(mezera205,1)} mm.")
    bezny["popis_ui"] = (
        f"Přelez {bezny['delka_s']} s. Všech sedm kontaktních zkoušek ověřilo dokončení a stabilitu. "
        f"Na schodu 210 mm byla nejmenší vzorkovaná mezera mezi díly {cs(minima['dily']['mm'],1)} mm "
        f"a od okolí {cs(minima['okoli']['mm'],1)} mm při nejistotě ±2 mm. "
        f"{odhad205} Fyzicky neověřeno."
    )
    rychly = vystup.get("rychly_210")
    if rychly:
        mezery = rychly["mezery_skutecne_simulace"]
        srovnani = next(z["varianty"] for z in vystup["zkousky"] if z["profil"]=="rychlý 210 mm")
        vysky = ", ".join(f"{h} mm " + ("dokončil" if srovnani[f"schod {h} mm"]["dokoncil"] else "nedokončil")
                          for h in (205,215))
        rychly["popis_ui"] = (
            f"Experimentální přelez {cs(rychly['delka_s'],1)} s pro 210 mm. "
            f"Na 210 mm robot dokončil přelez s odchylkou trupu {cs(rychly['odchylka_pri_dokonceni_mm'],1)} mm. "
            f"Nejmenší vzorkovaná mezera mezi díly {cs(mezery['dily']['mm'],1)} mm, od okolí {cs(mezery['okoli']['mm'],1)} mm. "
            f"Při změně výšky: {vysky}. Fyzicky neověřeno."
        )
    pokus["popis_ui"] = (
        f"Povelový plán na {pokus['delka_s']} s. Kontaktní simulace skončila pádem. "
        f"V {cs(pokus['pad_s'],2)} s překročila odchylka trupu 60 mm při přenosu váhy na kolenou. "
        "Záznam ukazuje začátek pádu. Povelové polohy ukazují celý požadovaný přelez."
    )

def main():
    global DATA, G, PARY
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("vystup", type=Path)
    cli.add_argument("--procesy", type=int, default=4)
    args = cli.parse_args()
    DATA = nacti_prizpusobeni()
    G, PARY = P.nacti_geometrii(DATA[210]["edits"])
    zdroj = KONTROLA.parent / "zdroj" / "revize" / "R16" / "pohyb.json"
    plan = json.loads(zdroj.read_text())
    if P.M["revize"] != "R16" or not np.array_equal(plan["q"], P.M["q"]) or not np.array_equal(plan["rt"], P.M["rt"]):
        raise ValueError("Tyto výsledky vyžadují ověřenou geometrii a pohyb R16.")
    # Zahrnujeme i sousední neúspěšné časy. Kritéria neposouváme podle výsledku.
    pokusy = [(10, "rovnoměrný"), (10, "10 s"), (10,"10 s přenos opor"), (RYCHLY_CAS,"rychlý 210 mm"), (20,"běžný"), (25,"běžný"), (30,"běžný"),
              (32,"běžný"), (33,"běžný"), (34,"běžný")]
    mereni = {}
    with ProcessPoolExecutor(max_workers=args.procesy, mp_context=get_context("fork")) as pool:
        ukoly = [(t,p,v,False,False) for t,p in pokusy for v in list(ZATEZ)[:3]]
        for (t,p,v,_,_), r in zip(ukoly, pool.map(vypocti, ukoly)):
            mereni.setdefault((t,p), {})[v] = r
        for (t,p), vysledky in mereni.items():
            if all(r["dokoncil"] for r in vysledky.values()):
                dalsi = [(t,p,v,False,False) for v in list(ZATEZ)[3:]]
                for (_,_,v,_,_), r in zip(dalsi, pool.map(vypocti, dalsi)):
                    vysledky[v] = r
                if all(r["dokoncil"] for r in vysledky.values()):
                    vybrany, profil = t, p
                    break
        else:
            raise ValueError("Žádný prověřený rozvrh nedokončil všechny varianty.")
        ukoly = [(vybrany,profil,v,v=="nominál",True) for v in list(ZATEZ)[:3]]
        ukoly += [(10,"10 s přenos opor","nominál",True,False),
                  (RYCHLY_CAS,"rychlý 210 mm","nominál",True,True)]
        audit = list(pool.map(vypocti, ukoly))
    vybrana_data = audit[0]
    for v, r in zip(list(ZATEZ)[:3], audit[:3]):
        mereni[(vybrany, profil)][v] = {k:x for k,x in r.items() if k not in ("moment","casy_s","odchylka_mm","odchylka_panve_mm","panev_mm","zaznam")}
    vystup = {
        "revize": "R16", "kontrolni_soucet_pohybu": hashlib.sha256(zdroj.read_bytes()).hexdigest(),
        "mujoco": mujoco.__version__, "zdrojovy_cas_s": (len(plan["q"])-1)/P.HZ,
        "krok_dynamiky_s": 0.001, "ustaleni_pred_s": 1, "ustaleni_po_s": 3,
        "vybrany": {"delka_s": vybrany, **vybrana_data},
        "cil_10_s": {"delka_s": 10, **audit[3]},
        "rychly_210": {"delka_s": RYCHLY_CAS, **audit[4]},
        "zkousky": [{"delka_s": t, "profil": p, "varianty": v} for (t,p), v in mereni.items()],
        "zdroje_pohonu": ZDROJE, "predpoklady": [
            "R16, plánované polohy a pořadí opor zachovány. Úseky s rychlou změnou kloubů mají více času.",
            "Model používá projektové pracovní meze momentu a pracovní lineární aproximaci směrové závislosti momentu na otáčkách ze dvou katalogových bodů. Měření křivek pod zatížením, napájení ani ohřevu není k dispozici.",
            "Odchylka trupu <25 mm a <8° na konci povelů i po 3 s, dvě chodidla na horní ploše s normálovou reakcí >0,5 N, dráha trupu bez odchylky >60 mm a příkaz pod otáčkami naprázdno. Tato kritéria hodnotí dokončení. Sítě na ujeté dráze kontrolovány zvlášť.",
            "Ruční, kolenní a chodidlové kontakty v dynamice jsou zjednodušené. Vzorkování sítí 25 Hz včetně ustálení není souvislá kontrola. Záporné mezery signalizují průnik. Odhad nejistoty geometrie projektu ±2 mm.",
            "Varianty zátěže jsou testované jednotlivě. Nejde o provozní povolení ani měření skutečného robota.",
        ],
    }
    popisy_ui(vystup)
    args.vystup.parent.mkdir(exist_ok=True, parents=True)
    args.vystup.write_text(json.dumps(vystup, ensure_ascii=False, separators=(",",":"))+"\n")
    print(f"Vybráno {vybrany} s; výsledek {args.vystup}")

if __name__ == "__main__":
    main()
