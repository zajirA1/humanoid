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

## Třetí kolo (16:30–18:45) – vyvažování v simulaci (NEFUNKČNÍ)

Kód: `kontrola/vyvazovani.py` (třídy `Vyvazovani` a `ReflexDlani`), zapojení `prepocet.simuluj(..., vyvazovani=dict(trida=…, cile=…, nez=…, zesileni=…))`,
testy `vv.py` (výšky schodu, zesílení jako JSON), `znam.py` (zkouška směru oprav těžiště), `dbg.py`. Automatická kontrola vyvažování nepoužívá.

Postup a nálezy:
1. Silová složka (posun těžiště k odlehčené opoře) bez sledování plánu → rozkmit, pád v 15–19 s.
2. Chyba nalezena: opravy se počítaly od už opraveného stavu (dvojí započtení) → přepsáno na integrační sledování plánovaného těžiště a náklonu.
3. Chyba nalezena: rozřešení „platilo“ posun těžiště volným pohybem trupu a měkce posouvalo opory; chodidla držena jen v bodě → robot se
   mohl zdarma překlopit kolem spojnice chodidel. Opraveno (opory pevně, chodidla i natočením, holeně dvěma body, cena jen na kloubech);
   kontrola `znam.py`: cíl 5 mm → skutečně 5,8 / 4,8 mm.
4. I tak: sledování těžiště samo padá ve 50 s už na 210 mm (drží robota v nejslabší poloze plánu); se silovou složkou pád ve 23–69 s
   podle zesílení; reflex dlaní (natažení ruky k podložce) pád v 19 s na 210 mm.
Závěr: jednoduché regulátory nad pozičními servy s plánem R13 robustnost nezvýšily. Další možnosti: regulace síly v oporách přes QP
(rozdělení sil + momenty kloubů), nebo nový plán přelezu s vyrovnaným zatížením opor ve fázích na třech oporách (nejlépe obojí).

## Čtvrté kolo (22. 11., večer) – nový plán s vyrovnanými oporami + přizpůsobení výšce → revize R15

Skripty (cesty počítají s pracovní složkou `/tmp/plan`, kopie R13 = `model_R13.json` z commitu 8529369):
`posun2.js` (dávkové přizpůsobení s posunem trupu `off`, posunem cíle dlaně/chodidla `shift`, zdvihem nad schodem `lift`),
`planB.py` (statické hledání položení dlaní), `dynopt.py` (hledání s MuJoCo ve smyčce), `schody.py`, `vyska.js`, `eng_lift.js`
(přizpůsobení výšce), `genR15.py` (sestavení R15 z R13 + `off.json`), `noha.py` (volná levá noha ve fázi 3), `envscan.py` (odstupy).

Postup a nálezy:
1. Statické vylepšení rezerv (planB: slabých poloh 239 → 218) v dynamice padalo (50,8 s na 210 mm) → hledání přímo s dynamikou.
2. Mřížka 25 položení pravé dlaně s posunem trupu ×0,5: pád ve 50 s na 218 mm nespravila žádná. Pevný plán fázi s kolenem
   na schodu při jiné výšce schodu nezvládne.
3. **Přizpůsobení výšce**: robot výšku schodu změří dotykem dlaně (je na schodu od začátku fáze 3) a od 30 s plynule (2 s) zvedne
   cíle nad schodem o rozdíl `dh` a pánev o `dh` × podíl opor na schodu (`retarget(..., liftdz)`, `prizpusob.js` `vyska_dh`).
   Plná dynamika, posun trupu ve fázi 3 ×0,5:

   | Skutečný schod | Plánované dh | Výsledek |
   |---|---|---|
   | 202 / 205 / 210 / 215 / 218 mm | přesně | doběhne |
   | 225 mm | +15 | pád 21,7 s (ještě před přizpůsobením) |
   | 218 mm | +6 / +10 (chyba měření ∓2 mm) | pád |
   | 210 mm | ±2, ±3 | doběhne |
   | 202 mm | −6 / −10 | doběhne / neprošlo (chyba konce 28 mm) |

   Výška se tedy musí změřit zhruba na ±1–2 mm; větší chyba toleranci zužuje.
4. Integrace jako R15 (`kontrola/data/model.json`): posun trupu přitáhl volnou levou nohu k hraně schodu (odstup 0,34 mm ve 23,5 s);
   rozšířené doladění v kontrole dotáhlo jen na 2,37 mm (jedna společná změna úhlů pro celý dlouhý úsek nestačí).
   Proto `noha.py`: po polohách (16–33 s) pootočení kloubů levé nohy tak, aby koleno a holeň minuly hranu o ≥ 6 mm, vyhlazení
   v čase (σ 2 polohy), 2 průchody → odstup v celém pohybu 3,26 mm (stejně jako R13), mezery dílů 9,22 mm, změna nohy ≤ 10°.

## Páté kolo (22. 11., večer) – regulace sil v oporách přes QP (NEPOMOHLA)

Kód: `kontrola/qp_sily.py` (třída `SilyQP`, v simulaci `vyvazovani=dict(trida='SilyQP', …)`, potřebuje `pip install quadprog`),
testy `qpt.py` (výšky, chyba měření `CHYBA`, jiný model `MODEL`), `statqp.py` (smyčka ve stojící poloze), `znamqp.py` (znaménko).
Každých 20 ms: požadovaná výslednice (tíha + PD těžiště + PD náklonu) → QP rozdělí do bodů opor (tření 0,35, nezbytná opora ≥ 5 N)
→ chyba sil po oporách → Δτ = −Jᵀ Δf → posun povelu serva Δq = Δτ / kp (polohová serva STS moment řídit neumějí), volitelně integrační složka.

Výsledky (R15, plná dynamika):

| Případ | Bez regulace | S QP |
|---|---|---|
| 210 mm (do 30 s) | doběhne | doběhne |
| 218 mm, chyba měření −2 / +2 / −5 mm | doběhne | doběhne |
| 222 mm | pád 25,2 s | pád 25,7 s (silnější zesílení: 23,4 s) |
| 225 mm | pád 21,7 s | pád 24,4 s |
| 198 mm | pád 133,3 s | pád 50,4 s (horší) |
| 222 mm, přizpůsobení výšce už od 9 s (první dotyk dlaně) | pád 30,2 s | pád 30,9–32,4 s (6 nastavení) |

Nálezy:
1. Znaménko ověřeno, ale účinnost je malá: požadavek +5 N na dlaň přes Δq = −JᵀΔf/kp dá +0,5 N (opory tvoří uzavřený řetězec, tělo uhne).
2. Ve stojící poloze s integrační složkou síly k požadovaným dojdou (pravá dlaň 4,0 → 6,7 N z 7,9 N), ale Δq roste až k 5°;
   v pohybu integrační složka robota rozkmitá (222 mm: pád už ve 23,7 s).
3. Pády nad 218 mm nejsou chybou rozdělení sil: na 222 mm se robot ve fázi 3 nakloní o 5–6° dozadu, těžiště uteče o 30–50 mm a pravá dlaň
   ztratí kontakt (0 N, QP chce 5 N). Regulace sil polohu nevrátí; potřebná je změna pohybu (dřív přizpůsobit výšku, jiné rozložení
   fáze 3/4), ne silnější regulace.
4. Bonus: R15 s přesným přizpůsobením snese chybu měření výšky aspoň −5 až +2 mm na 218 mm i bez regulace.
Závěr: QP regulace sil s polohovými servy v této podobě robustnost nezvýšila; kontrola ji nepoužívá. Rozumný další krok je skutečné
řízení momentu (serva s proudovou/momentovou smyčkou) nebo přeplánování fáze 3–4 pro vyšší schod s přizpůsobením od prvního dotyku dlaně.
