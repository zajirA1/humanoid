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
