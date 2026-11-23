# Humanoid – simulátor robota Emil H22

Soukromý prohlížeč a simulátor humanoida Emil H22. Vše se počítá v prohlížeči, server jen po přihlášení
vydá jeden soubor. Běží na Hetzner Webhostingu (bez SSH), cílová adresa `robot.caribhaus.com`.

Číslování: **aplikace** a **revize robota** zvlášť. Teď: aplikace 0.7 · robot H22 R16 (R15 + ramena předozadně posunutá o 26,5 mm dovnitř k trupu; **v modelu zasahují do rámu trupu** – rozpis v oddílu R16). 0.7: rozpis mezer po dílech a kontrola posunutých serv vůči vlastnímu rámu (`kontrola/rozpis.py`, jen varování), směr posunu ven/dovnitř v panelu, export 3MF s posunutými servy a visícími díly, seznam přepočtů i z GitHubu; 0.6 = R16; 0.5 (audit: výška schodu v modelu, historie revizí, zpět/vpřed a uložení úprav, oznámení, úchyty v 3MF, lehčí stránka – data Konda až při otevření, mobil); dříve 0.4 (stránka převedená na R15, číslo verze v záhlaví), 0.3 (přepočet úpravy v GitHubu), 0.2 · robot H22 R15 (přelez schodu 21 cm s vyrovnanějšími oporami a přizpůsobením výšce; vychází z R13) + R14 (úprava kloubů v modelu).

| Složka | Co v ní je |
|---|---|
| `web/` | přesně to, co je na serveru: přihlášení (`index.php`), simulátor (`app/emil-h22.html`), zákazy |
| `zdroj/uprava-kloubu/` | zdroj úpravy kloubů (R14): výpočetní jádro, ovládání, data a skript, který je vloží do stránky |
| `zdroj/r15/` | převod stránky na R15: hotový pohyb, statika, dynamika, oddíl R15 a texty |
| `zdroj/revize/` | nástroj Nová revize (`nova_revize.py`) a podklady revizí vzniklých z úprav kloubů (`R16/`, …) |
| `vypocty/` | Python skripty, kterými vznikl přelez R13 (hledání pohybu, statika, mezery, dynamika, testy) |
| `testy/` | kontrola výpočtu sil proti referenci a testy stránky v prohlížeči |
| `kontrola/` | automatická kontrola úpravy kloubů (data, přizpůsobení v Node, statika, mezery FCL, dynamika MuJoCo) |
| `upravy/` | uložené úpravy kloubů ke kontrole |
| `docs/NASAZENI.md` | jak se nasazuje, co nastavit na Hetzneru a v DNS, token pro přepočet |

Velké soubory (3MF, výsledky simulací, mezivýsledky) jsou na IDrive e2 v `ai-projekty/Humanoid/`.

## Předávání mezi Claudem a GPT

Pravidla v `CLAUDE.md` / `AGENTS.md`. Platný stav projektu: e2 `ai-projekty/Humanoid/AKTUALNI_STAV.md`, předání v `Humanoid/K_PREVZETI/`.

## Nasazení

Ručně z GitHubu: **Actions → Nasazení na Hetzner → Run workflow**, nejdřív `zkouska`, pak `nasazeni`.
Nic se nenasazuje samo. Podrobně v [docs/NASAZENI.md](docs/NASAZENI.md).

## Přepočet úpravy kloubů

`python3 -I kontrola/prepocet.py upravy/<soubor>.json <výstup> [--rychle]` – totéž běží ve workflow *Přepočet úpravy*.
Knihovny: `numpy scipy python-fcl mujoco`, Node 18+.

## Nová revize z úpravy

V simulátoru úprava → *Odeslat k přepočtu* → když plná kontrola projde: **Actions → Nová revize → Run workflow** s označením přepočtu.
Vznikne commit s novou revizí (posunutá serva, dokreslené úchyty, verze aplikace +0,1). Na server až přes *Nasazení na Hetzner*.

## Kontrola

```
bash .github/kontrola.sh     hesla v repozitáři, PHP, výpočet sil proti referenci (1141 poloh)
```

## Známá omezení

- Simulátor je soubor HTML o 11,6 MB (zabalený 3,4 MB) + `web/app/kondo-data.json` (3,7 MB, stahuje se přes `index.php?data=kondo` až při otevření prohlížeče Konda). Sestavuje se ze stránky R13 dvěma skripty (`zdroj/r15/stranka_r15.py`,
  `zdroj/uprava-kloubu/build_r14.py`, postup v `CLAUDE.md`); rozdělení na kód a data zatím není hotové.
- Rozpis mezer po jednotlivých dílech (dialog Mezery dílů) a podrobná zpráva R13 jsou z R13; R15 se liší jen ve fázi 3 a souhrnné hodnoty R15 jsou v oddílu R15.
- Skripty ve `vypocty/` (původní hledání pohybu R13) mají cesty natvrdo (`/home/claude/sim`, `/home/claude/work`) a potřebují data
  vytěžená z původní stránky a mezivýsledky z e2. Jsou uložené kvůli dohledatelnosti, ne jako hotový nástroj.
