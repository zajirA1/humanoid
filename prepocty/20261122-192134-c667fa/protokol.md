# Kontrola úpravy kloubů – PROŠLO

Úprava `20b1302bc2b6` · 1141 poloh přelezu 21 cm · 934 s výpočtu

## Úprava

- Rameno · předozadní pohyb · L: posun [-40.0, 5.5, 4.5] mm – podél osy kloubu 40.0 mm, napříč 7.1 mm
- Rameno · předozadní pohyb · P: posun [40.0, 5.5, 4.5] mm – podél osy kloubu 40.0 mm, napříč 7.1 mm

## Kontroly

| Kontrola | Výsledek | Hodnota |
|---|---|---|
| Rovnováha ve všech polohách (tření 0,5 / 0,4 / 0,3) | ✅ | bez rovnováhy 0 / 0 / 0 z 1141 |
| Nejvyšší využití serva ≤ 85 % | ✅ | 71.1 % (Kyčel · předozadní pohyb · P, 166.2 s) |
| Mezera mezi díly ≥ 9 mm | ✅ | 9.26 mm (156.0 s) |
| Odstup od podlahy a schodu ≥ 3 mm | ✅ | 3.35 mm (20.2 s) |
| Opory zůstávají na místě (≤ 0.5 mm) | ✅ | 0.009 mm |
| Dynamická simulace doběhne (nominální) | ✅ | odchylka na konci 8.8 mm |
| Schod o ±5 mm jiný (205 a 215 mm) – dynamika doběhne | ✅ | 205 mm: OK, 215 mm: OK |

## Srovnání s výchozím R15

| | R15 | Po úpravě |
|---|---|---|
| Nejvyšší využití serva (tření 0,5) | 70.3 % | 71.1 % |
| Nejmenší mezera mezi díly | 9.97 mm | 9.26 mm |
| Polohy s mezerou pod 10 mm | 32 | 41 |
| Nejmenší odstup od schodu | 3.58 mm | 3.35 mm |
| Největší posun trupu oproti R15 | 0 mm | 2.3 mm |

## Doladění volných končetin

Doladěné úseky švihu: 5 (74 poloh), klouby volné končetiny pootočeny nejvýš o 5.0° s plynulým náběhem; cíl 9.5 mm. Opory a trup beze změny.
- L noha 18.7–21.7 s: nejtěsnější místo úseku -0.54 mm vůči cíli → -0.23 mm, změna úhlů [-1.38, -0.01, -1.67, -0.0, -0.0, -0.0]°
- L noha 122.5–125.3 s: nejtěsnější místo úseku -0.52 mm vůči cíli → aspoň +0,8 mm, změna úhlů [0.0, -0.0, -0.0, -0.59, -0.0, 0.0]°
- P noha 50.2–54.0 s: nejtěsnější místo úseku -0.31 mm vůči cíli → aspoň +0,8 mm, změna úhlů [-0.0, -1.97, 0.09, 0.0, -0.0, -0.0]°
- P noha 67.0–68.7 s: nejtěsnější místo úseku -0.23 mm vůči cíli → aspoň +0,8 mm, změna úhlů [4.97, -0.0, -0.0, -0.0, -0.0, -0.07]°
- L noha 18.3–21.5 s: nejtěsnější místo úseku -0.23 mm vůči cíli → -0.15 mm, změna úhlů [-0.05, -0.02, 1.72, -0.0, -0.0, -0.0]°

## Dynamická simulace

| Varianta | Doběhne | Odchylka na konci | Špička momentu |
|---|---|---|---|
| nominal | ✅ | 8.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| schod 205 mm | ✅ | 18.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 1.6 % času |
| schod 215 mm | ✅ | 6.2 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| tření 0,35 | ✅ | 8.1 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| hmotnost +10 % | ✅ | 9.3 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 1.1 % času |
| o 5 mm blíž | ✅ | 13.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| serva 85 % | ✅ | 8.9 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 2.4 % času |
| schod 202 mm | ✅ | 23.0 mm | 100 % (Rameno · boční zdvih · L), na mezi 3.0 % času |
| schod 218 mm | ✅ | 3.0 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.0 % času |

## Robustnost (rezerva těžiště a předzatížení opor)

Slabé místo = rezerva těžiště pod 15 mm nebo opora, bez které by robot nestál, nese méně než 5 N.

| | R15 | Po úpravě |
|---|---|---|
| Slabých poloh | 208 | 207 |
| Nejmenší rezerva těžiště | 5.4 mm | 5.5 mm |
| Nejmenší zatížení nezbytné opory | 0.5 N | 0.6 N |

- 16.3–25.5 s: rezerva 22.6 mm, nejslabší nezbytná opora P dlaň 0.6 N
- 39.8–44.3 s: rezerva 10.3 mm, nejslabší nezbytná opora P dlaň 2.9 N
- 47.2–54.5 s: rezerva 5.5 mm, nejslabší nezbytná opora L dlaň 1.7 N
- 69.8–71.7 s: rezerva 16.8 mm, nejslabší nezbytná opora L holeň 4.1 N
- 82.5–86.8 s: rezerva 9.5 mm, nejslabší nezbytná opora P dlaň 2.1 N
- 97.2–100.8 s: rezerva 57.9 mm, nejslabší nezbytná opora P dlaň 2.8 N
- 130.7–133.0 s: rezerva 36.3 mm, nejslabší nezbytná opora P dlaň 3.1 N

Mezery v simulovaném pohybu: díly 9.4 mm, schod -1.3 mm (informativní).

## Co tato kontrola nedělá

- Pohyb se přizpůsobí nové geometrii a doladí se jen švih volných končetin; trup ani rozložení sil se znovu neoptimalizují.
- Rámy a vidlice v modelu se nepřekreslují – posouvá se servo a osa. Střet serva s vlastním rámem se nekontroluje.
- Chůze, sed a další pohyby se v této kontrole nepočítají (přepočítá je simulátor v prohlížeči).
- Dynamika je předkorigovaná podle statiky (jako u R13); bez předkorekce přelez nedoběhne. Krátké špičky na mezi serva má i výchozí R15.
- Zkoušky jiné výšky schodu počítají s tím, že robot výšku změří přesně a od 30. s přelez přizpůsobí (chyba měření ±2 mm toleranci zužuje; doladění švihu se u nich neopakuje).
- Robot se v simulaci řídí jen předem spočítanými povely bez zpětné vazby (bez IMU); skutečný robot s vyvažováním bude robustnější, bez něj méně.
- Fyzicky nic neověřeno.
