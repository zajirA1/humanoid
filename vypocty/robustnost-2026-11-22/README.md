# Pokus o přeplánování slabých míst přelezu (22. 11. 2026) – NEPŘIJATO

Cíl: zvýšit robustnost přelezu R13 na výšku schodu (R13 padá v simulaci na 218 mm ve 24,7 s).

- `metriky.py` – rozdělení svislých sil mezi opory (stejná tuhost opor) a „nezbytné“ opory; stejné měřítko je teď v `kontrola/robustnost.py`.
- `posun.js` – dávkové přizpůsobení s posunem trupu (`retarget(..., off)` v `r14engine.js`).
- `plan.py` – statické hledání posunu trupu po úsecích (mřížka ±24 mm, náběh 2 s).
- `podmnozina.py`, `schody2.py` – varianty jen s vybranými úseky a test výšek schodu; `f6hledej.py`, `f6run.py` – dynamické hledání posunu ve fázi 6.

Výsledek: statické přeplánování všech úseků dynamicky selhalo (pád kolem 50 s na všech výškách). Přeplánování jen fáze 3 (14–30 s)
odstraní pád ve 24,7 s, ale robot pak padá ve 50,4 s už na 215 mm (R13 215 mm zvládá). Fáze 6 (zvedání zadní nohy ve 48–49 s,
opora levá holeň + obě dlaně, levá dlaň 1,6–2,8 N, rezerva 5,4 mm) se posunem trupu ±8–16 mm opravit nedá. Další krok: přeplánovat
časování odlehčení zadní nohy a polohu holeně s dynamikou ve smyčce. Cesty ve skriptech jsou natvrdo na /tmp/plan.

## Druhé kolo (15:40–17:30) – zvedání zadní nohy, přizpůsobení výšce

Skript `exp.py` (volby: `f3` = násobek posunu trupu ve fázi 3, `zpomal` = [od s, do s, faktor], `sigma`/`nabeh` = plynulost předkorekce,
`vyska` = přelez přizpůsobený výšce schodu přes `vyska.js` + `eng_lift.js`, `trace` = průběh sil a náklonu). Výsledky (MuJoCo, schod 210/215/218 mm):

| Varianta | 210 | 215 | 218 |
|---|---|---|---|
| R13 | OK | OK | pád 24,7 s |
| předkorekce plynulejší (σ 3) / lineární náběh 2 s | OK | OK | pád 24,7–25,1 s |
| zpomalení 46–52 s ×2 | OK | OK | pád 24,7 s |
| posun trupu fáze 3 ×1 / ×0,7 / ×0,5 | OK | pád 50,3 / 50,6 / **OK** | pád 50,4 s |
| f3 ×0,5 + přelez přizpůsobený výšce (plán = skutečná výška) | – | – | pád 31,1 s (202 mm: pád 52,6 s) |

Rozbor pádu ve 50 s na 218 mm: koleno leží o 8 mm výš, robot je naklopen o 3° dozadu, levá dlaň nedosáhne (0 N), pravé chodidlo pořád nese
9–12 N; když ho plán „zvedne“, robot nemá oporu. Rozbor přizpůsobení výšce: pravá dlaň ve fázi 3 je i v plánu skoro nezatížená a v simulaci
klesne na 0 N. Závěr: předem spočítaný pohyb bez zpětné vazby má ve fázích na třech oporách tak malou rezervu, že posunem trupu ani
přizpůsobením výšce se robustnost nad ±5 mm zvýšit nedá. Další krok: jednoduché vyvažování v simulaci (IMU náklon + síly v dlaních →
korekce trupu), které bude mít i skutečný robot; teprve s ním znovu posun trupu a přizpůsobení výšce. Výchozí pohyb zůstává R13.
