# Nasazení Humanoida na Hetzner

Cíl: `https://robot.caribhaus.com`, soukromé, pod heslem, neindexované. Hosting KLIPHAUS (Webhosting M,
`www748.your-server.de`), stejně jako ostatní weby: vlastní složka a vlastní FTP účet.

## 1. Jednorázově na Hetzneru (konsoleH)

1. Složka `/public_html/humanoid/` (vedle `kliphaus`, `caribhaus`, `harmonie`).
2. Subdoména `robot.caribhaus.com` → složka `/public_html/humanoid`.
3. FTP účet jen pro tuto složku (domovská složka účtu = `/public_html/humanoid`). Jiný účet nepoužívat.
4. SSL Manager → Let's Encrypt pro `robot.caribhaus.com` (až po kroku 2 v DNS).
5. PHP 8.1 nebo novější.

## 2. Jednorázově v DNS (Porkbun, caribhaus.com)

Záznam `A` (a `AAAA`) pro `robot` na stejné adresy, jaké má `harmonie`. Nic jiného se nemění.

## 3. Jednorázově v GitHubu (Settings → Secrets and variables → Actions)

| Název | Druh | Hodnota |
|---|---|---|
| `FTP_USERNAME` | secret | jméno FTP účtu z kroku 1.3 |
| `FTP_PASSWORD` | secret | jeho heslo |
| `ROBOT_HESLO` | secret | heslo do simulátoru, aspoň 10 znaků |
| `FTP_SERVER_DIR` | variable | nenastavovat, pokud je FTP účet omezený na složku (výchozí `/`) |
| `PREPOCET_TOKEN` | secret | nepovinný – token pro tlačítko *Odeslat k přepočtu* (kap. 5) |

## 4. Nasazení

Actions → **Nasazení na Hetzner** → Run workflow → `zkouska`. Zkontrolovat výpis, pak znovu s `nasazeni`.
Na serveru se nic nemaže, jen nahrává. Změna hesla = změnit `ROBOT_HESLO` a nasadit znovu.

## Proč to neovlivní caribhaus.com ani jiné weby

- Vlastní složka, vlastní FTP účet (nedosáhne mimo ni), vlastní certifikát, jeden nový záznam v DNS.
- Přihlašovací cookie `ROBOTSID` je bez `domain`, platí jen pro `robot.caribhaus.com`.
- Kořenový `.htaccess` v `/public_html` se nemění. Pozor: zakazuje všude soubory `.zip`, `.md`, `.sql`, `.log`.
- `robots.txt` se zákazem je jen v této složce; `caribhaus.com/robots.txt` zůstává.

## Ochrana

Přihlášení heslem (`web/index.php`), 8 chybných pokusů za 15 minut z jedné adresy, přihlášení drží 14 dní.
Hlavička `X-Robots-Tag: noindex`, meta robots, `robots.txt`. Složky `app/` a `soukrome/` nejsou z webu dostupné.
Odhlášení: `https://robot.caribhaus.com/?odhlasit=1`.

## 5. Automatický přepočet úpravy (tlačítko v simulátoru)

Simulátor → *Úprava kloubů* → *Odeslat k přepočtu* spustí v GitHubu workflow **Přepočet úpravy**
(`.github/workflows/prepocet.yml`): přizpůsobení přelezu 21 cm, statika při tření 0,5/0,4/0,3, přesné mezery ze sítí,
dynamická simulace v šesti variantách a verdikt podle mezí (`MEZE` v `kontrola/prepocet.py`). **Nic nenasazuje.**
Výsledek: artefakt běhu (stránka návrhu, protokol), souhrn běhu a soubory ve větvi `prepocty/<id>/`.
Ručně lze spustit i z Actions (vstup = JSON exportu nebo cesta `upravy/<soubor>.json`).

Token pro server (jednorázově):
1. GitHub → Settings (účtu) → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
2. Repository access: **Only select repositories → zajirA1/humanoid**. Expiration: např. 1 rok.
3. Permissions → Repository: **Actions: Read and write**, **Contents: Read-only** (Metadata se doplní samo). Nic dalšího.
4. Token uložit do `zajirA1/humanoid` → Settings → Secrets → Actions jako `PREPOCET_TOKEN`, pak spustit *Nasazení na Hetzner*.
   Na serveru je jen v `soukrome/tajne.php` (z webu nedostupné). Kdo se přihlásí do simulátoru, může přepočet spustit,
   omezení je 10 přepočtů za hodinu.
