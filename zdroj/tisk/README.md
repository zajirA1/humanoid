# Tiskové podklady H22 R16

Katalog spojuje konkrétní výskyt součásti simulátoru (síť, stranu, článek, osu a pořadí) s jeho tiskovými soubory. Mechanické díly, kovové příslušenství, elektronika a značky mají rozdílné zařazení. Pevně spojené plastové úseky volitelného nástavce tvoří pro tisk jedno těleso. Pravé a levé díly vycházejí z transformací vlastní sestavy.

## Sestavení

Spusť z kořene repozitáře. Potřebuješ Node.js, Python 3.11 nebo 3.12 s NumPy, SciPy, libigl 2.6.3 a OpenSCAD CLI. Přísná závěrečná kontrola používá navíc Python SDK lib3mf a systémovou knihovnu GEOS C.

```sh
python3 -m pip install numpy scipy libigl==2.6.3 lib3mf
OPENBLAS_NUM_THREADS=1 python3 zdroj/tisk/generuj.py
OPENBLAS_NUM_THREADS=1 python3 testy/t_tisk.py --lib3mf --rezy --cgal
```

Volba `--output <adresář>` vytvoří samostatnou sadu. Podklady pro web patří do soukromého `web/app/tisk/R16/`; po přihlášení je vydává PHP. V katalogu jsou kontrolní součty všech 166 exportů a procesních předvoleb. Samostatné STL a 3MF obsahují stejný povrch. Projekt s koncovkou `-x1c.3mf` přidává odpovídající nastavení plátkování.

## Geometrie a tisk

Generátor čte přesnou geometrii vydané stránky, zahnuté a zrcadlené části i úchopový nástavec. Na rámy aplikuje posuny a plynulé přetvoření z R16. U obou kolen spojí konce poškozené hrany kratší než 0,01 mm. Odstraní trojúhelníky s nulovou plochou a použije přesný výpočet hranice materiálu na lokální přehyby sítě. Zachová orientaci povrchů vnitřních dutin. Před vydáním kontroluje uzavřenost, orientaci, obálku, změnu objemu i průniky v geometrii zaokrouhlené pro binární STL.

Polohu navrhuje podle kontaktu s podložkou, převisů a výšky stavby. U dlouhých nosných dílů zvýhodňuje průběh dlouhé osy v rovině vrstev. U rámů pevnostní projekt kombinuje průběžné obvody s gyroidní výplní. Lokální oblasti u uložení os se umisťují na skutečný plast poblíž serv. Výplň se mění výhradně uvnitř tělesa; geometrie otvorů, čepů a dosedacích ploch je společná pro všechny varianty. Tenké ozdoby a pružné kontakty mají vlastní procesy. Přesnou hmotnost, dobu, převisy, podpěry a povrch dosedacích otvorů je potřeba zkontrolovat po rozřezání pro konkrétní materiál a podložku.

Kontroly výměnných formátů, rovinných řezů a nastavení modifikátorů ověřují digitální konstrukci. Pevnost, souosost uložení, únava materiálu, tepelný průhyb a tření kontaktů čekají na zkoušky skutečných výtisků. Pro Anycubic Kobra S1 Max Combo se použije čistý model se samostatným profilem vlastní tiskárny a filamentu v Anycubic Slicer Next.
