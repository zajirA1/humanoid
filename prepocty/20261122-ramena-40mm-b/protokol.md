# Kontrola úpravy kloubů – PROŠLO

Úprava `dcdf48b0a030` · 1141 poloh přelezu 21 cm · 276 s výpočtu

## Úprava

- Rameno · předozadní pohyb · L: posun [-40.0, 0.5, 0.0] mm – podél osy kloubu 40.0 mm, napříč 0.5 mm
  - ⚠️ Posun vede jen podél osy: pohyb a síly se téměř nemění, mění se poloha a hmotnost serva a vidlice se musí prodloužit o 40 mm.
- Rameno · předozadní pohyb · P: posun [40.0, 0.5, 0.0] mm – podél osy kloubu 40.0 mm, napříč 0.5 mm
  - ⚠️ Posun vede jen podél osy: pohyb a síly se téměř nemění, mění se poloha a hmotnost serva a vidlice se musí prodloužit o 40 mm.

## Kontroly

| Kontrola | Výsledek | Hodnota |
|---|---|---|
| Rovnováha ve všech polohách (tření 0,5 / 0,4 / 0,3) | ✅ | bez rovnováhy 0 / 0 / 0 z 1141 |
| Nejvyšší využití serva ≤ 85 % | ✅ | 70.3 % (Kyčel · předozadní pohyb · L, 166.2 s) |
| Mezera mezi díly ≥ 9 mm | ✅ | 9.21 mm (51.8 s) |
| Odstup od podlahy a schodu ≥ 3 mm | ✅ | 3.26 mm (68.5 s) |
| Opory zůstávají na místě (≤ 0.5 mm) | ✅ | 0.001 mm |
| Dynamická simulace doběhne (nominální) | ✅ | odchylka na konci 8.8 mm |

## Srovnání s výchozím R13

| | R13 | Po úpravě |
|---|---|---|
| Nejvyšší využití serva (tření 0,5) | 70.3 % | 70.3 % |
| Nejmenší mezera mezi díly | 9.22 mm | 9.21 mm |
| Polohy s mezerou pod 10 mm | 39 | 41 |
| Nejmenší odstup od schodu | 3.26 mm | 3.26 mm |
| Největší posun trupu oproti R13 | 0 mm | 0.3 mm |

## Dynamická simulace

| Varianta | Doběhne | Odchylka na konci | Špička momentu |
|---|---|---|---|
| nominal | ✅ | 8.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.4 % času |
| tření 0,35 | ✅ | 7.6 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.7 % času |
| hmotnost +10 % | ✅ | 9.1 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 1.1 % času |
| schod 215 mm | ✅ | 5.2 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.4 % času |
| o 5 mm blíž | ✅ | 13.8 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 0.4 % času |
| serva 85 % | ✅ | 8.9 mm | 100 % (Rameno · předozadní pohyb · P), na mezi 2.8 % času |

Mezery v simulovaném pohybu: díly 5.3 mm, schod -1.3 mm (informativní).

## Co tato kontrola nedělá

- Pohyb se jen přizpůsobí nové geometrii (opory na místě, trup a volné končetiny ustoupí); znovu se neladí.
- Rámy a vidlice v modelu se nepřekreslují – posouvá se servo a osa. Střet serva s vlastním rámem se nekontroluje.
- Chůze, sed a další pohyby se v této kontrole nepočítají (přepočítá je simulátor v prohlížeči).
- Dynamika je předkorigovaná podle statiky (jako u R13); bez předkorekce R13 nedoběhne. Krátké špičky na mezi serva má i výchozí R13.
- Fyzicky nic neověřeno.
