# Kontrola úpravy kloubů – PROŠLO

Úprava `0712f033f771` · 1141 poloh přelezu 21 cm · 1423 s výpočtu

## Úprava

- Rameno · předozadní pohyb · L: posun [-26.5, 0.0, 0.0] mm, nese další díly – podél osy kloubu 26.5 mm, napříč 0.0 mm
- Rameno · předozadní pohyb · P: posun [26.5, 0.0, 0.0] mm, nese další díly – podél osy kloubu 26.5 mm, napříč 0.0 mm

## Kontroly

| Kontrola | Výsledek | Hodnota |
|---|---|---|
| Rovnováha ve všech polohách (tření 0,5 / 0,4 / 0,3) | ✅ | bez rovnováhy 0 / 0 / 0 z 1141 |
| Nejvyšší využití serva ≤ 85 % | ✅ | 70.3 % (Kyčel · předozadní pohyb · P, 166.2 s) |
| Mezera mezi díly ≥ 9 mm | ✅ | 9.51 mm (52.0 s) |
| Odstup od podlahy a schodu ≥ 3 mm | ✅ | 3.40 mm (47.2 s) |
| Opory zůstávají na místě (≤ 0.5 mm) | ✅ | 0.062 mm |
| Dynamická simulace doběhne (nominální) | ✅ | odchylka na konci 7.8 mm |
| Schod o ±5 mm jiný (205 a 215 mm) – dynamika doběhne | ✅ | 205 mm: OK, 215 mm: OK |

## Srovnání s výchozím R15

| | R15 | Po úpravě |
|---|---|---|
| Nejvyšší využití serva (tření 0,5) | 70.3 % | 70.3 % |
| Nejmenší mezera mezi díly | 9.97 mm | 9.51 mm |
| Polohy s mezerou pod 10 mm | 32 | 7 |
| Nejmenší odstup od schodu | 3.58 mm | 3.40 mm |
| Největší posun trupu oproti R15 | 0 mm | 12.1 mm |

## Doladění volných končetin

Doladěné úseky švihu: 5 (71 poloh), klouby volné končetiny pootočeny nejvýš o 5.3° s plynulým náběhem; cíl 9.5 mm. Opory a trup beze změny.
- L noha 18.5–22.2 s: nejtěsnější místo úseku -1.65 mm vůči cíli → -1.08 mm, změna úhlů [-1.34, -0.05, -0.03, -0.0, -0.0, -0.0]°
- L noha 22.0–25.0 s: nejtěsnější místo úseku -0.40 mm vůči cíli → aspoň +0,8 mm, změna úhlů [-2.36, 0.05, -0.0, -0.0, -0.0, -0.0]°
- P noha 67.0–68.7 s: nejtěsnější místo úseku -0.15 mm vůči cíli → aspoň +0,8 mm, změna úhlů [3.78, 0.0, -0.0, -0.0, -0.0, 0.0]°
- P noha 114.8–117.5 s: nejtěsnější místo úseku -0.14 mm vůči cíli → aspoň +0,8 mm, změna úhlů [0.0, -0.0, -3.15, 0.06, -0.0, 0.03]°
- L noha 18.0–22.5 s: nejtěsnější místo úseku -1.08 mm vůči cíli → +0.34 mm, změna úhlů [1.42, 0.79, 5.37, 0.02, 0.0, 0.0]°

## Dynamická simulace

| Varianta | Doběhne | Odchylka na konci | Špička momentu |
|---|---|---|---|
| nominal | ✅ | 7.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| schod 205 mm | ✅ | 20.0 mm | 100 % (Kotník · předozadní pohyb · P), na mezi 1.5 % času |
| schod 215 mm | ✅ | 5.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| tření 0,35 | ✅ | 7.1 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| hmotnost +10 % | ✅ | 7.7 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.9 % času |
| o 5 mm blíž | ✅ | 12.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |
| serva 85 % | ✅ | 7.9 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 2.6 % času |
| schod 202 mm | ✅ | 21.3 mm | 100 % (Kotník · boční náklon · P), na mezi 2.7 % času |
| schod 218 mm | ✅ | 2.2 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.1 % času |

## Robustnost (rezerva těžiště a předzatížení opor)

Slabé místo = rezerva těžiště pod 15 mm nebo opora, bez které by robot nestál, nese méně než 5 N.

| | R15 | Po úpravě |
|---|---|---|
| Slabých poloh | 208 | 211 |
| Nejmenší rezerva těžiště | 5.4 mm | 5.6 mm |
| Nejmenší zatížení nezbytné opory | 0.5 N | 0.8 N |

- 16.0–25.3 s: rezerva 25.1 mm, nejslabší nezbytná opora P dlaň 0.8 N
- 39.7–44.2 s: rezerva 9.4 mm, nejslabší nezbytná opora L holeň 2.8 N
- 49.0–54.5 s: rezerva 5.6 mm, nejslabší nezbytná opora L dlaň 1.7 N
- 70.0–71.3 s: rezerva 18.2 mm, nejslabší nezbytná opora L holeň 4.6 N
- 77.3–78.5 s: rezerva 12.4 mm, nejslabší nezbytná opora L dlaň 3.5 N
- 82.3–86.8 s: rezerva 9.4 mm, nejslabší nezbytná opora P dlaň 2.1 N
- 96.0–100.8 s: rezerva 48.5 mm, nejslabší nezbytná opora P dlaň 2.8 N
- 130.5–133.0 s: rezerva 36.4 mm, nejslabší nezbytná opora P dlaň 3.0 N

Mezery v simulovaném pohybu: díly 5.3 mm, schod -0.5 mm (informativní).

## Co tato kontrola nedělá

- Pohyb se přizpůsobí nové geometrii a doladí se jen švih volných končetin; trup ani rozložení sil se znovu neoptimalizují.
- Rámy a vidlice v modelu se nepřekreslují – posouvá se servo a osa. Střet serva s vlastním rámem se nekontroluje.
- Chůze, sed a další pohyby se v této kontrole nepočítají (přepočítá je simulátor v prohlížeči).
- Dynamika je předkorigovaná podle statiky (jako u R13); bez předkorekce přelez nedoběhne. Krátké špičky na mezi serva má i výchozí R15.
- Zkoušky jiné výšky schodu počítají s tím, že robot výšku změří přesně a od 30. s přelez přizpůsobí (chyba měření ±2 mm toleranci zužuje; doladění švihu se u nich neopakuje).
- Robot se v simulaci řídí jen předem spočítanými povely bez zpětné vazby (bez IMU); skutečný robot s vyvažováním bude robustnější, bez něj méně.
- Fyzicky nic neověřeno.
