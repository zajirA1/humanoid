# Humanoid – poznámky pro práci na kódu

Soukromý simulátor humanoida Emil H22 (majitel Jiří, komunikuje česky; texty, komentáře a commity česky).
Hetzner Webhosting M bez SSH: na serveru jen statické soubory a PHP, všechny výpočty běží v prohlížeči.

## Pravidla, která platí vždy

- **Nic se nenasazuje bez výslovného pokynu majitele.** Nasazení je jen ruční workflow *Nasazení na Hetzner*,
  spouští ho majitel; výchozí režim `zkouska` nic nenahrává.
- **Hesla nikdy do Gitu.** `web/soukrome/tajne.php` vzniká až ve workflow ze secretu `ROBOT_HESLO`.
- Web je soukromý: heslo, `noindex`, `robots.txt` se zákazem. Tuto ochranu neoslabovat.
- Humanoid obsahem nesouvisí s Kliphausem ani Caribhausem. Nesahat na jejich složky, DNS ani kořenový `.htaccess`.
- `web/` = přesně stav serveru. Verze aplikace a revize robota se číslují zvlášť.
- U výsledků simulace vždy uvést, co je ověřené a co odhad (mezery ±2 mm, pohyb jen přizpůsobený, ne doladěný).

## Předávání GPT ↔ Claude (stejně jako u ostatních projektů)

Na projektu pracuje střídavě Claude i GPT. Platí společná pravidla `ai-projekty/_spolecne/GPT/2026-11-05/PRAVIDLA_PREDAVANI_v1.md`
(IDrive e2, bucket `ai-projekty`, region `Frankfurt-2`). Pro Humanoid:

- **e2 prefix `Humanoid/`** · platný přehled `Humanoid/AKTUALNI_STAV.md` · předání `Humanoid/K_PREVZETI/`
  (`RRRR-MM-DD_HHMM_Claude_<tema>_predani-pro-GPT.md`, `…_GPT_<tema>_predani-pro-Claude.md`, neměnná) ·
  větší výstupy `Humanoid/Claude/RRRR-MM-DD/`, `Humanoid/GPT/RRRR-MM-DD/` · revize robota `Humanoid/revize/H22/R<N>/` ·
  archiv souhrnu `Humanoid/archiv/AKTUALNI_STAV_v<N>_RRRR-MM-DD_HHMMSS_<autor>.md`.
- **Kód = tento repozitář**, větev `main`. ZIP na e2 je historický podklad, ne zdroj nasazení.
- **Začátek práce:** přečíst `AKTUALNI_STAV.md`, README na e2 a všechna nepřevzatá předání druhého autora; porovnat
  s GitHubem (HEAD, běhy Kontrola a Nasazení).
- **Konec práce:** commit + push, nové předání v osmi bodech (pravidla kap. 3) a aktualizace `AKTUALNI_STAV.md`
  (předchozí verzi nejdřív přesně uložit do `archiv/`), oboje po zápisu přečíst a ověřit.
- U nasazení vždy odděleně: kontrola kódu, zkouška, ostré nasazení, živé ověření (pravidla kap. 5).
- Do repozitáře, e2 ani chatu nepatří hesla, tokeny ani podepsané odkazy.

## Sestavení stránky

`python3 -I zdroj/r15/stranka_r15.py <vstupní R13.html> /tmp/r15.html` (pohyb, statika, dynamika a texty R15; obnoví i `zdroj/uprava-kloubu/r14page.json`),
pak `python3 -I zdroj/uprava-kloubu/build_r14.py /tmp/r15.html web/app/emil-h22.html`. Vstupní R13 je na e2 v `ai-projekty/Humanoid/revize/H22/R13/`.
Po změně výchozího pohybu: `python3 -I kontrola/prepocet.py <{}> <výstup> --vychozi`, `pohyb.json` z výstupu do `zdroj/r15/pohyb-R15.json`,
`python3 -I zdroj/r15/dynamika.py zdroj/r15/pohyb-R15.json zdroj/r15/dynamika-R15.json`, pak obě sestavení. Verze aplikace je v `stranka_r15.py` (`VERZE_APLIKACE`).

## Nová revize z úpravy kloubů

Workflow *Nová revize* (`.github/workflows/nova-revize.yml`, vstup = označení prošlého plného přepočtu) spustí
`zdroj/revize/nova_revize.py`: posuny serv zapeče do `kontrola/data/model.json` (`zaklad`: d = posun osy a serva, E = posun visících dílů),
převezme přizpůsobený pohyb (`pohyb.json` z přepočtu), spustí plnou kontrolu s `--vychozi`, přestaví `web/app/emil-h22.html`
(posunutá serva, dokreslené zjednodušené úchyty, oddíl revize nahoře, verze aplikace +0,1) a commitne do `main`. Podklady revize jsou
v `zdroj/revize/R<N>/`. Nic nenasazuje; kopii stránky na e2 `revize/H22/R<N>/` a předání dělá Claude/GPT. Smí ho spustit Claude/GPT
na pokyn majitele. Úpravy v panelu se k zapečeným posunům přičítají (`r14engine.mergeEdits`, `prizpusob.js`). Stránka R15 se staví
ze zmrazených dat `zdroj/r15/data/`; další revize se nanášejí na hotovou stránku.

## Přepočet úpravy

Workflow *Přepočet úpravy* smí Claude/GPT spustit kdykoli (nic nenasazuje). Meze verdiktu jsou v `kontrola/prepocet.py`
(`MEZE`, povinné varianty dynamiky `POVINNE` = nominál a schod 205/215 mm, `ROBUST`); měnit je jen na pokyn majitele.
Po změně výchozího pohybu (`kontrola/data/model.json`) přepočítat `vychozi*.json` (srovnávací hodnoty: `python3 -I kontrola/prepocet.py <prázdná úprava> <výstup> --vychozi`). `kontrola/r14engine.js` musí být shodný se `zdroj/uprava-kloubu/r14engine.js`.
Po změně `zdroj/uprava-kloubu/*` znovu sestavit `web/app/emil-h22.html`.

## Příkazy

```
bash .github/kontrola.sh      kontrola před commitem (stejná běží v GitHubu)
python3 -I kontrola/prepocet.py <úprava.json> <výstup> [--rychle]   plná kontrola úpravy kloubů
node testy/t_engine.js        výpočet sil v JS proti referenci z Pythonu (1141 poloh, shoda do 1e-4)
```
