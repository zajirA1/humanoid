"""Připojí ověřené dráhy Kobry ke konkrétním tiskovým projektům vydání R16."""
import gzip
import hashlib
import json
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    source = root / 'zdroj/revize/R16/kobra'
    output = root / 'web/app/tisk/R16'
    catalog_file = output / 'catalog.json'
    catalog = json.loads(catalog_file.read_bytes())
    results = json.loads((source / 'vysledky.json').read_bytes())
    parts = {part['id']: part for part in catalog['parts'] if part['printable']}
    if catalog['revision'] != 'R16' or len(parts) != 54 or parts.keys() != results.keys():
        raise ValueError('Seznam výsledků Kobry nesouhlasí s katalogem R16.')
    (output / 'kobra').mkdir(exist_ok=True)
    names = set()
    for ident, part in parts.items():
        result = results[ident]
        name = result['file']
        if not re.fullmatch(r'kobra/[a-zA-Z0-9-]+\.gcode', name) or name in names:
            raise ValueError(f'Neplatný název souboru u {ident}.')
        names.add(name)
        project_hash = catalog['file_checksums'][part['files']['project3mf']]
        material = 'TPU 95A' if part['process_id'] == 'flexible-contact' else 'PETG'
        if result['project_sha256'] != project_hash or result['material'] != material:
            raise ValueError(f'Jiný zdrojový projekt nebo materiál u {ident}.')
        raw = gzip.decompress((source / (Path(name).name + '.gz')).read_bytes())
        if len(raw) != result['bytes'] or hashlib.sha256(raw).hexdigest() != result['sha256']:
            raise ValueError(f'Poškozený G-code u {ident}.')
        (output / name).write_bytes(raw)
        part['kobra'] = result
        catalog['file_checksums'][name] = result['sha256']
    catalog_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=1)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
