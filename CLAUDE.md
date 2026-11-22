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

`python3 -I zdroj/uprava-kloubu/build_r14.py <vstupní R13.html> web/app/emil-h22.html`. Vstupní R13 je na e2 v `ai-projekty/Humanoid/revize/H22/R13/`.

## Přepočet úpravy

Workflow *Přepočet úpravy* smí Claude/GPT spustit kdykoli (nic nenasazuje). Meze verdiktu jsou v `kontrola/prepocet.py`
(`MEZE`); měnit je jen na pokyn majitele. `kontrola/r14engine.js` musí být shodný se `zdroj/uprava-kloubu/r14engine.js`.
Po změně `zdroj/uprava-kloubu/*` znovu sestavit `web/app/emil-h22.html`.

## Příkazy

```
bash .github/kontrola.sh      kontrola před commitem (stejná běží v GitHubu)
python3 -I kontrola/prepocet.py <úprava.json> <výstup> [--rychle]   plná kontrola úpravy kloubů
node testy/t_engine.js        výpočet sil v JS proti referenci z Pythonu (1141 poloh, shoda do 1e-4)
```
