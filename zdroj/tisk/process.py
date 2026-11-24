"""Výchozí procesy pro zkušební výtisky Emila R16 na X1 Carbon s tryskou 0,4 mm."""

import json
from pathlib import Path
from urllib.parse import quote


MACHINE = "Bambu Lab X1 Carbon 0.4 nozzle"
STANDARD = "0.20mm Standard @BBL X1C"
STRENGTH = "0.20mm Strength @BBL X1C"

# Oba rodiče jsou tovární profily Bambu Studio pro X1C. Jejich teploty,
# rychlosti a limity průtoku zvoleného filamentu uživatel nastaví ve sliceru.
PROFILES = {
    "rigid-structure": {
        "name": "Nosný rám",
        "base": STRENGTH,
        "wall_loops": 6, "top_layers": 6, "bottom_layers": 6, "infill_pct": 25,
        "material": "Pro první osazení PETG s profilem odpovídajícím skutečné cívce. Stálé zatížení a teplo od serva vyžadují dlouhodobou zkoušku.",
        "orientation": "U vidlice posuď ohyb v kořeni ramen. Vrstvy orientuj tak, aby hlavní tah podél ramen vedla souvislá vlákna v jejich rovině.",
        "local_reinforcement": "U paty vidlice, objímky ložiska a šroubových sloupků prohlédni souvislé obvody. Pokud je mezi nimi řídké jádro, přidej v Bambu Studiu místní modifikátor a zkus šest obvodů s 50% výplní jen v namáhaném místě. Po změně porovnej hmotnost a tuhost.",
        "checks": "Změř souosost a průměry otvorů, usaď servo a ložisko a zkontroluj volný pohyb. Hmotnost a průhyb změř na výtisku, než jej použiješ na robotu.",
    },
    "rigid-cover": {
        "name": "Lehký kryt",
        "base": STANDARD,
        "wall_loops": 3, "top_layers": 4, "bottom_layers": 4, "infill_pct": 12,
        "material": "Pro kontrolu tvaru PLA, pro zkoušku s ohřátým motorem PETG se zvoleným profilem cívky.",
        "orientation": "Opři kryt o stabilní hranu nebo plochu. Zkontroluj převisy na vnitřní straně a dosednutí západek.",
        "local_reinforcement": "Výplň ponech lehkou v ploše krytu. Pokud v náhledu závěs nebo šroubový sloupek obklopuje řídké jádro, nastav v místním modifikátoru pět obvodů a zopakuj zkoušku přichycení.",
        "checks": "Ve vrstveném náhledu ověř uzavření horních ploch a klipy. Po osazení znovu zkontroluj odstup od pohybujícího se ramene.",
    },
    "flexible-contact": {
        "name": "Pružná kontaktní plocha",
        "base": STANDARD,
        "wall_loops": 3, "top_layers": 4, "bottom_layers": 4, "infill_pct": 18,
        "material": "Použij TPU požadované tuhosti. Pro prototyp lze zkusit TPU 95A, nastavit profil konkrétní cívky a kompatibilní způsob podávání.",
        "orientation": "Funkční dotykovou plochu polož na podložku jen tehdy, když její otisk poskytuje požadovaný kontakt. Posuď stranu opřenou o tělo i přístup k oporám.",
        "local_reinforcement": "Výplň ovlivní stlačitelnost. Porovnej vytištěný vzorek při skutečném přítlaku a rozmístění stěn uprav podle jeho deformace.",
        "checks": "Ověř přilnutí k podkladu, stlačení pod zatížením a přichycení k rámu. Hranici použitelného tření stanov měřením na povrchu, po kterém má robot chodit.",
    },
    "small-detail": {
        "name": "Drobná pevná součást",
        "base": STANDARD,
        "wall_loops": 4, "top_layers": 5, "bottom_layers": 5, "infill_pct": 30,
        "material": "Pro zkušební osazení použij stejný materiál jako u protikusu a jeho odpovídající profil.",
        "orientation": "V náhledu vrstev ověř obvody tenkých jazýčků a přesné vedení otvorů pro spojovací díly.",
        "local_reinforcement": "V tenkém průřezu mohou celý objem zaplnit čtyři obvody. Množství výplně měň až po prohlédnutí skutečné dráhy trysky.",
        "checks": "Přeměř funkční rozměry oproti protikusu a zkus usazení. Drobné díly i po seříznutí podpor musí mít volný rozsah pohybu.",
    },
}


def process_for(class_key):
    """Údaje pro uživatele aplikace a pro odkaz na soubor pro import profilu."""
    config = PROFILES[class_key]
    return {
        "id": class_key,
        **config,
        "machine": MACHINE, "layer_height_mm": 0.2, "infill_pattern": "gyroid",
        "preset_file": f"process/{class_key}.json",
        "base_source": "https://github.com/bambulab/BambuStudio/blob/master/resources/profiles/BBL/process/" + quote(config["base"] + ".json"),
        "import_steps": "V Bambu Studiu zapni systémový profil X1 Carbon s tryskou 0,4 mm. V Soubor → Import → Importovat konfigurace vyber stažený JSON a zvol jeho název mezi procesy. Nastav svoji cívku a podložku, spusť plátkování a v náhledu zkontroluj obvody, podpěry, odhad hmotnosti a času.",
        "kobra": {
            "machine": "Anycubic Kobra S1 Max Combo",
            "nozzle_mm": 0.4, "bed_mm": [350, 350, 350],
            "slicer": "Anycubic Slicer Next", "base_source": "https://eu.anycubic.com/products/kobra-s1-max-combo",
            "steps": "V Anycubic Slicer Next zvol přímo Kobra S1 Max s tryskou 0,4 mm. Do nového projektu vlož čistý díl STL nebo 3MF. Nastav výšku vrstvy, počet obvodů, horních a dolních vrstev i výplň podle karty dílu. Pro místní zesílení přidej modifikátor nad vyznačenou oblast, zvol šest obvodů a 50 % gyroidu. Zvol skutečnou cívku i podložku a zkontroluj náhled po rozřezání.",
        },
        "status": "Zkušební proces. Název továrního rodiče a pole nastavení ověřeny proti zdrojům Bambu Studio. Dráhy trysky, hmotnost a pevnost ověř pro konkrétní díl.",
    }


def write_presets(output_dir):
    """Vytvoří uživatelské profily pro Soubor → Import → Importovat konfigurace."""
    folder = Path(output_dir) / "process"
    folder.mkdir(parents=True, exist_ok=True)
    for profile_id, settings in PROFILES.items():
        name = f"Emil H22 R16 - {settings['name']} X1C 0.4"
        # Importér rozpoznává proces podle print_settings_id, semver a názvu
        # existujícího rodiče. Teploty, podložka a materiál patří profilu cívky.
        preset = {
            "from": "User", "version": "1.0.0.0", "name": name,
            "print_settings_id": name, "inherits": settings["base"],
            "compatible_printers": [MACHINE], "layer_height": "0.2",
            "wall_loops": str(settings["wall_loops"]),
            "top_shell_layers": str(settings["top_layers"]),
            "bottom_shell_layers": str(settings["bottom_layers"]),
            "top_shell_thickness": f"{settings['top_layers'] * 0.2:.1f}",
            "bottom_shell_thickness": f"{settings['bottom_layers'] * 0.2:.1f}",
            "sparse_infill_pattern": "gyroid",
            "sparse_infill_density": f"{settings['infill_pct']}%",
        }
        (folder / f"{profile_id}.json").write_text(
            json.dumps(preset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
