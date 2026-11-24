# R16 · audit doby přelezu schodu 210 mm

Původní referenční přelez má 1 141 uzlů za 190 s. Nové fyzické rozvrhy časují tytéž polohy nerovnoměrně. Při výpočtu zůstává gravitace, krok dynamiky 1 ms a model serv v běžném čase. Rychlost přehrávače na výpočet nemá vliv.

| Doba povelů | Výsledek na 210 mm | Odchylka trupu při posledním povelu | Chodidla na horní ploše při posledním povelu | Alespoň jedno servo na projektové mezi momentu¹ |
|---|---|---|---|---|
| 33 s | Obě chodidla nahoře, po 3 s stojí dál | 10,5 mm | L 14,1 N / P 15,7 N | 2,1 % |
| 18,5 s | Obě chodidla nahoře, po 3 s stojí dál | 23,6 mm | L 13,9 N / P 15,5 N | 20,1 % |
| 10 s | Pád při přenosu váhy na kolenou. První zjištěná odchylka trupu přes 60 mm v 7,42 s | Pokus selhal | — | 57,4 % včetně pádu |

¹ Od začátku pohybu do konce třísekundového ustálení; sepnutí meze se porovnává v každém integračním kroku. U 10 s klouby po ztrátě rovnováhy dále sledují původní povelový plán. Simulátor nemá kolizní povrchy pro dopad celého těla. Záznam končí sekundou po ztrátě přesnosti.

## Výška, zátěž a volné vzdálenosti

Pro 33 s skončilo sedm jednotlivých zkoušek stabilním postojem na schodu. Jde o výšky 205/210/215 mm, na 210 mm také o tření 0,35, hmotnost zvýšenou o 10 %, serva omezená na 85 % a výchozí pozici o 5 mm blíž. Snížené a zvýšené schody používají výškové přizpůsobení z R16. Profil 18,5 s při 205 ani 215 mm nedokončil přelez. U 33 s a 205 mm byla po ustálení odchylka od plánu 23,4 mm při mezi 25 mm.

Sítě skutečně dosažených simulovaných poloh byly porovnány s celými povrchy dílů, podlahou a schodem 25× za sekundu. Kontrola záměrné opory vyřazuje podle pravidel projektu. Nejistota geometrie je přibližně ±2 mm.

| Profil a výška | Nejmenší mezera mezi díly | Nejmenší odstup od okolí |
|---|---|---|
| 33 s, 205 mm | 5,5 mm | průnik 2,5 mm |
| 33 s, 210 mm | 5,9 mm | 1,6 mm |
| 33 s, 215 mm | 5,3 mm | 3,4 mm |
| 18,5 s, 210 mm | 4,7 mm | 4,5 mm |

Při nominální výšce ani jeden dokončený rozvrh nedosahuje přibližně 10mm rezervy mezi díly. Na 205mm schodu dynamický model opor dokončí pohyb, zatímco kontrola plných povrchů najde zásah pravého stehna do okolí. Statický protokol pro plán R16 nadále uvádí 9,51 mm mezi díly a 3,40 mm od okolí. Hardware ani spojité vzdálenosti mezi vzorky ověřeny nebyly.

## Jak jsme hledali rychlejší pohyb

Při prostém zkrácení celé dráhy na 10 s požaduje některý kloub 4,48násobek katalogové rychlosti naprázdno. První nerovnoměrný pokus vyhověl samotné rychlosti serv, ale při nástupu na levé koleno překročil v 2,22 s odchylku trupu 60 mm. Další rozvrhy přerozdělily čas k přesunům mezi chodidly, dlaněmi a koleny. V desítkách nominálních zkoušek jsme ladili délky skupin fází i lokální prodloužení u jednotlivých přenosů váhy. Výsledný 10s rozvrh vyžaduje nejvýše 96,2 % katalogové rychlosti naprázdno a překoná první přenosy až na obě kolena. Další přenos už nedokončí. Nejkratším nalezeným dokončeným pokusem při 210 mm zůstal rozvrh 18,5 s. Tyto zkoušky neurčují teoretické minimum jiné trajektorie.

## Přepočet a data

Z kořene repozitáře spusťte s Pythonem obsahujícím numpy, scipy, mujoco 3.3.7 a python-fcl 0.7.0.11 a s dostupným Node.js:

```bash
OPENBLAS_NUM_THREADS=1 python kontrola/tempo_schodu.py /tmp/tempo-schodu.json --procesy 4
```

Model vychází z pracovních limitů jednotlivých kloubů R16. Moment je v motorickém směru omezen lineární aproximací mezi katalogovým blokovacím momentem a rychlostí naprázdno. Brzdný moment zůstává omezen projektovou mezí. Pro dvojici serv v boční kyčli zůstává nerovnoměrné rozdělení zátěže z R16. Charakteristika celého pohonu pod zátěží, ohřev, hystereze a chování napájecího zdroje vyžadují měření.

Soubor `tempo-schodu.json` obsahuje časové uzly, špičky momentů ze vzorků nejbližších každému uzlu a záznam skutečného simulovaného pohybu pro tři profily. `odchylka_mm` porovnává referenční bod trupu s povelovým cílem; `panev_mm` obsahuje světové souřadnice středu pánve v mm a `odchylka_panve_mm` jeho odchylku. Při pádu jsou data za koncem použitelného záznamu prázdná.

Katalogové vstupy pro STS3215-C018 a STS3250-C001 platí při 12 V, pro XL330-M288-T při 5 V. [Feetech STS3215-C018](https://ftservo.github.io/ftservo-wiki/en/products/models/st-3215-c018/main/) · [Feetech STS3250](https://www.feetechrc.com/Data/feetechrc/upload/file/20240120/6384135881578380868917773.pdf) · [ROBOTIS XL330-M288-T](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)
