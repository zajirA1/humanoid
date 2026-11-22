# Humanoid – simulátor robota Emil H22

Soukromý prohlížeč a simulátor humanoida Emil H22. Vše se počítá v prohlížeči, server jen po přihlášení
vydá jeden soubor. Běží na Hetzner Webhostingu (bez SSH), cílová adresa `robot.caribhaus.com`.

Číslování: **aplikace** a **revize robota** zvlášť. Teď: aplikace 0.2 · robot H22 R13 (přelez schodu 21 cm) + R14 (úprava kloubů v modelu).

| Složka | Co v ní je |
|---|---|
| `web/` | přesně to, co je na serveru: přihlášení (`index.php`), simulátor (`app/emil-h22.html`), zákazy |
| `zdroj/uprava-kloubu/` | zdroj úpravy kloubů (R14): výpočetní jádro, ovládání, data a skript, který je vloží do stránky |
| `vypocty/` | Python skripty, kterými vznikl přelez R13 (hledání pohybu, statika, mezery, dynamika, testy) |
| `testy/` | kontrola výpočtu sil proti referenci a testy stránky v prohlížeči |
| `docs/NASAZENI.md` | jak se nasazuje a co nastavit na Hetzneru a v DNS |

Velké soubory (3MF, výsledky simulací, mezivýsledky) jsou na IDrive e2 v `ai-projekty/Humanoid/`.

## Předávání mezi Claudem a GPT

Pravidla v `CLAUDE.md` / `AGENTS.md`. Platný stav projektu: e2 `ai-projekty/Humanoid/AKTUALNI_STAV.md`, předání v `Humanoid/K_PREVZETI/`.

## Nasazení

Ručně z GitHubu: **Actions → Nasazení na Hetzner → Run workflow**, nejdřív `zkouska`, pak `nasazeni`.
Nic se nenasazuje samo. Podrobně v [docs/NASAZENI.md](docs/NASAZENI.md).

## Kontrola

```
bash .github/kontrola.sh     hesla v repozitáři, PHP, výpočet sil proti referenci (1141 poloh)
```

## Známá omezení

- Simulátor je jeden soubor HTML o 14,9 MB. Sestavuje se z předchozí verze stránky skriptem
  `zdroj/uprava-kloubu/build_r14.py`; rozdělení na kód a data zatím není hotové.
- Skripty ve `vypocty/` mají cesty natvrdo (`/home/claude/sim`, `/home/claude/work`) a potřebují data
  vytěžená z původní stránky a mezivýsledky z e2. Jsou uložené kvůli dohledatelnosti, ne jako hotový nástroj.
- Nasazovací workflow zatím neběželo proti serveru.
