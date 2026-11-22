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

## Sestavení stránky

`python3 -I zdroj/uprava-kloubu/build_r14.py <vstupní R13.html> web/app/emil-h22.html` (cesty ke zdrojům ve
skriptu jsou zatím natvrdo na `/home/claude/sim`). Vstupní R13 je na e2 v `ai-projekty/Humanoid/revize/H22/R13/`.

## Příkazy

```
bash .github/kontrola.sh      kontrola před commitem (stejná běží v GitHubu)
node testy/t_engine.js        výpočet sil v JS proti referenci z Pythonu (1141 poloh, shoda do 1e-4)
```
