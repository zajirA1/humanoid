# Kontrola úpravy kloubů – NEPROŠLO

Úprava `20b1302bc2b6` · 1141 poloh přelezu 21 cm · 589 s výpočtu

## Úprava

- Rameno · předozadní pohyb · L: posun [-40.0, 5.5, 4.5] mm – podél osy kloubu 40.0 mm, napříč 7.1 mm
- Rameno · předozadní pohyb · P: posun [40.0, 5.5, 4.5] mm – podél osy kloubu 40.0 mm, napříč 7.1 mm

## Kontroly

| Kontrola | Výsledek | Hodnota |
|---|---|---|
| Rovnováha ve všech polohách (tření 0,5 / 0,4 / 0,3) | ✅ | bez rovnováhy 0 / 0 / 0 z 1141 |
| Nejvyšší využití serva ≤ 85 % | ✅ | 71.1 % (Kyčel · předozadní pohyb · P, 166.2 s) |
| Mezera mezi díly ≥ 9 mm | ✅ | 9.26 mm (156.0 s) |
| Odstup od podlahy a schodu ≥ 3 mm | ✅ | 3.27 mm (68.5 s) |
| Opory zůstávají na místě (≤ 0.5 mm) | ✅ | 0.009 mm |
| Dynamická simulace doběhne (nominální) | ✅ | odchylka na konci 8.0 mm |
| Schod o ±5 mm jiný (205 a 215 mm) – dynamika doběhne | ❌ | 205 mm: OK, 215 mm: pád |

## ⚠️ Varování (verdikt neovlivňují)

- Dynamická simulace ve variantě „schod 218 mm“ nedoběhla (robot se odchýlil o 848 mm). Nezvládá ji ani výchozí R13 – slabina přelezu, ne úpravy.

## Srovnání s výchozím R13

| | R13 | Po úpravě |
|---|---|---|
| Nejvyšší využití serva (tření 0,5) | 70.3 % | 71.1 % |
| Nejmenší mezera mezi díly | 9.22 mm | 9.26 mm |
| Polohy s mezerou pod 10 mm | 39 | 41 |
| Nejmenší odstup od schodu | 3.26 mm | 3.27 mm |
| Největší posun trupu oproti R13 | 0 mm | 2.3 mm |

## Doladění volných končetin

Doladěné úseky švihu: 2 (42 poloh), klouby volné končetiny pootočeny nejvýš o 2.0° s plynulým náběhem; cíl 9.5 mm. Opory a trup beze změny.
- L noha 122.5–125.3 s: nejtěsnější místo úseku -0.52 mm vůči cíli → aspoň +0,8 mm, změna úhlů [0.0, -0.0, -0.0, -0.59, -0.0, 0.0]°
- P noha 50.2–54.0 s: nejtěsnější místo úseku -0.31 mm vůči cíli → aspoň +0,8 mm, změna úhlů [-0.0, -1.97, 0.09, 0.0, -0.0, -0.0]°

## Dynamická simulace

| Varianta | Doběhne | Odchylka na konci | Špička momentu |
|---|---|---|---|
| nominal | ✅ | 8.0 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.7 % času |
| schod 205 mm | ✅ | 19.4 mm | 100 % (Rameno · předozadní pohyb · L), na mezi 3.8 % času |
| schod 215 mm | ❌ | 782.3 mm | 100 % (Kotník · boční náklon · P), na mezi 48.6 % času |
| tření 0,35 | ✅ | 6.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.7 % času |
| hmotnost +10 % | ✅ | 8.7 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 1.3 % času |
| o 5 mm blíž | ✅ | 13.1 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.7 % času |
| serva 85 % | ✅ | 9.0 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 2.7 % času |
| schod 202 mm | ✅ | 22.8 mm | 100 % (Rameno · předozadní pohyb · L), na mezi 6.7 % času |
| schod 218 mm | ❌ | 848.1 mm | 100 % (Kotník · boční náklon · P), na mezi 48.7 % času |

## Robustnost (rezerva těžiště a předzatížení opor)

Slabé místo = rezerva těžiště pod 15 mm nebo opora, bez které by robot nestál, nese méně než 5 N.

| | R13 | Po úpravě |
|---|---|---|
| Slabých poloh | 239 | 240 |
| Nejmenší rezerva těžiště | 5.4 mm | 5.5 mm |
| Nejmenší zatížení nezbytné opory | 0.0 N | 0.0 N |

- 14.3–15.5 s: rezerva 11.0 mm, nejslabší nezbytná opora L dlaň 3.2 N
- 16.7–30.0 s: rezerva 12.2 mm, nejslabší nezbytná opora P dlaň 0.0 N
- 39.8–44.3 s: rezerva 10.3 mm, nejslabší nezbytná opora P dlaň 2.9 N
- 47.2–54.5 s: rezerva 5.5 mm, nejslabší nezbytná opora L dlaň 1.7 N
- 69.8–71.7 s: rezerva 16.8 mm, nejslabší nezbytná opora L holeň 4.1 N
- 82.5–86.8 s: rezerva 9.5 mm, nejslabší nezbytná opora P dlaň 2.1 N
- 97.2–100.8 s: rezerva 57.9 mm, nejslabší nezbytná opora P dlaň 2.8 N
- 130.7–133.0 s: rezerva 36.3 mm, nejslabší nezbytná opora P dlaň 3.1 N

Mezery v simulovaném pohybu: díly 9.4 mm, schod -0.8 mm (informativní).

## Co tato kontrola nedělá

- Pohyb se přizpůsobí nové geometrii a doladí se jen švih volných končetin; trup ani rozložení sil se znovu neoptimalizují.
- Rámy a vidlice v modelu se nepřekreslují – posouvá se servo a osa. Střet serva s vlastním rámem se nekontroluje.
- Chůze, sed a další pohyby se v této kontrole nepočítají (přepočítá je simulátor v prohlížeči).
- Dynamika je předkorigovaná podle statiky (jako u R13); bez předkorekce R13 nedoběhne. Krátké špičky na mezi serva má i výchozí R13.
- Robot se v simulaci řídí jen předem spočítanými povely bez zpětné vazby (bez IMU); skutečný robot s vyvažováním bude robustnější, bez něj méně.
- Fyzicky nic neověřeno.
