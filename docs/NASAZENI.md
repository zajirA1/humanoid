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
