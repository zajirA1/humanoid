# Dvě USB kamery Yahboom na Emilovi

Tento nástroj počítá kalibraci z uložených dvojic fotografií. Připraví obrázky, ve kterých odpovídající body leží na stejném řádku, a vypočte **hloubku podél společné optické osy kamer**. Běží lokálně na počítači s Pythonem 3, OpenCV a NumPy.

```sh
python -m pip install opencv-python-headless numpy
```

## 1. Zamkni mechaniku a pořiď snímky

Připevni těla obou kamer k sedlům lišty v rozteči přibližně 110 mm. Nastav manuální ostření a zafixuj klouby. Označ **levou** kameru při pohledu ve směru jízdy. Nastav shodné rozlišení obou kamer, stejné jako pro další měření. Během celé série zachovej rozlišení, ostření, montáž a orientaci. Po změně proveď novou kalibraci.

Použij rovnou šachovnici s **9 × 6 vnitřními rohy** (10 × 7 polí). Změř skutečnou šířku vytištěného políčka. Pořiď alespoň 15–25 párů při různém náklonu a vzdálenosti. Pokryj střed, kraje a rohy společného obrazu. V obou záběrech vždy zachyť celou desku, její světlý okraj a ostré rohy. Během pořízení každé dvojice nech robota i šachovnici stát. U samostatných USB streamů porovnávej časové značky, pohyb desky nebo scény mezi snímky měření znehodnotí.

Do složek `sada/leva` a `sada/prava` ulož páry pod odpovídajícími názvy, například v každé složce `001.png`, `002.png`. Podporované jsou PNG, JPG a BMP.

## 2. Vypočti geometrii

Následující příklad používá políčko 20 mm.

```sh
python stereo.py kalibrovat sada/leva sada/prava profil --sloupce 9 --radky 6 --policko 20
```

V adresáři `profil` vznikne `kalibrace.npz` a `parametry.json`. Hodnota `fx_px` je ohnisková vzdálenost v pixelech pro narovnaný obraz, `baseline_mm` je změřená rozteč. Obě hodnoty použij ve stereopanelu simulátoru. Zkontroluj, že rozteč odpovídá skutečné liště. `rms_px` vyjadřuje reprojekční chybu a `vertical_p95_px` 95. percentil rozdílu řádků odpovídajících rohů v kalibrační sadě. Vyšší chyby nebo zjevně chybná rozteč vyžadují kontrolu rohů, směru kamer a velikosti políčka.

## 3. Změř bod v nové dvojici

```sh
python stereo.py narovnat profil/kalibrace.npz nova/leva.png nova/prava.png vysledek
```

V souborech `vysledek/leva-rekt.png` a `vysledek/prava-rekt.png` odečti souřadnice stejného ostrého bodu. V levém i pravém obraze se měří od levého horního rohu v původním rozlišení. Vyber bod viditelný v obou záběrech. V následujícím příkladu jsou souřadnice (600, 330) a (460, 330).

```sh
python stereo.py zmerit profil/kalibrace.npz 600 330 460 330
```

Hloubka v mm je `fx_px × baseline_mm / (x_levé − x_pravé)`. U vzdálených předmětů malá chyba výběru pixelu znamená větší chybu hloubky. Přesnost ověř na nezávislém snímku několika terčů ve známých vzdálenostech měřených podél optické osy. Pro bezpečnou jízdu a automatický pohyb ruky by bylo potřeba ověřit také pohybové zpoždění a slepé oblasti.

Podklady k hardwaru a výpočtu. [Yahboom USB kamera s mikrofonem](https://www.yahboom.store/products/camera-mic) a [OpenCV – kalibrace a rektifikace](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).
