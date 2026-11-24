"""Zařazení instancí R16. Popisky kupovaných podsestav popisují jejich geometrii, ne objednací položku."""
import re

RAMY = [
    "Rám otáčení krku", "Rám předklonu hlavy", "Rám otočné kyčle", "Rám boční kyčle s vidlicí",
    "Stehenní rám", "Bércový rám", "Rám kotníku", "Chodidlo", "Rám předozadního ramene",
    "Rám bočního ramene", "Rám předloktí", "Pohyblivý prst",
]
KOV = {
    'r11_ST3250_case':'Pouzdro serva STS3250', 'r11_ST3250_inboard_hub':'Výstupní unašeč',
    'r11_ST3250_active_center_screw':'Středový šroub unašeče', 'r11_ST3250_pair_drive_pins':'Hnací kolíky páru serv',
    'r11_ST3250_pair_bushings':'Pouzdra hnacích kolíků', 'r11_ST3250_case_screws':'Upevňovací šrouby serva',
    'r11_ST3250_idler_hub':'Pasivní unašeč', 'r11_ST3250_idler_bearing':'Ložisko pasivní strany',
    'r11_ST3250_idler_center_screw':'Středový šroub pasivní strany',
    'r8_horn_driver':'Výstupní páka serva', 'r8_horn_idler':'Pasivní páka serva',
    'r8_horn_screws':'Šrouby páky', 'r8_ST_case_screw':'Šrouby pouzdra STS', 'r8_XL_case_screw':'Šrouby pouzdra XL',
    'r8_ankle_case_screw':'Šrouby kotníkového serva',
    'baterie_obalka':'Baterie · montážní obálka', 'rizeni_obalka':'Řídicí elektronika · montážní obálka',
    'pasek_baterie':'Upevňovací pásek baterie',
}
NOSNIK = {'mount','back_brace','rail','rail_offset','rail_distal','fixed_yoke','yoke_bend','joint_boss','fixed_stem'}
PRST = {'finger','moving_stem'}
PRISLUSENSTVI = {
    'nosnik':'Pevný nosník úchopového nástavce', 'prst':'Pohyblivý prst nástavce',
    'clamp_front':'Přední čelist objímky', 'clamp_back':'Zadní čelist objímky',
    'pad_fixed':'Pružná ploška pevného prstu', 'pad_moving':'Pružná ploška pohyblivého prstu',
}
KLASIFIKACE = {'rigid-structure':'Nosný díl', 'rigid-cover':'Kryt', 'small-detail':'Drobný díl',
               'flexible-contact':'Pružný díl', 'hardware':'Kupovaná součást', 'reference':'Konstrukční reference'}


def strana(o):
    k, l = o['key'], o['link']
    if l is not None and 2 <= l <= 21:
        return 'L' if l < 12 else 'P'
    if re.search(r'(_l(?:[01]|_fitting)?$)', k): return 'L'
    if re.search(r'(_r(?:[01]|_fitting)?$)', k): return 'P'
    return None


def klasifikuj(o):
    k, l, j, typ = o['key'], o['link'], o['owner'], o['kind']
    if o.get('frame'):
        return 'rigid-structure', 'Rám trupu' if l==22 else RAMY[l if l < 12 else l-10], f'ram-{l:02d}'
    if typ=='palm': return 'flexible-contact','Kulová opora dlaně','opora-dlane'
    if typ=='cover':
        if 'fitting' in k: return 'hardware',o['name'],k
        return 'rigid-cover',o['name'],k
    if typ=='shin':
        if 'TPU' in k: return 'flexible-contact','Pružný návlek holeně','navlek-holene'
        return 'hardware',('Závitová vložka do holeně' if 'insert' in k else 'Šroub M2 návleku'),k
    if typ=='pickup':
        part=k.split('_',2)[-1]
        group='nosnik' if part in NOSNIK else 'prst' if part in PRST else part
        if re.fullmatch(r'clamp_(front|back)_(in|out)',part):group=part.rsplit('_',1)[0]
        if group in PRISLUSENSTVI:
            return ('flexible-contact' if group.startswith('pad_') else 'rigid-structure'),PRISLUSENSTVI[group],'n-'+group
        if any(t in part for t in ('screw','head','nut','pin','axle','eye','crank','tie_rod','coupler','driver')):
            if 'screw' in part: name='Šroub svorky nástavce'
            elif 'head' in part: name='Hlava šroubu svorky'
            elif 'nut' in part: name='Matice svorky'
            elif 'crank' in part: name='Kovová klika převodu'
            elif 'pin' in part or 'axle' in part: name='Čep převodu'
            elif 'eye' in part: name='Oko táhla'
            elif part=='tie_rod': name='Spojovací táhlo'
            else: name='Kovová spojka úchopu'
            return 'hardware',name,k
    if 'knee_index' in k: return 'reference','Kontrastní značka na povrchu kolena',k
    if k=='podlozka_baterie':return 'flexible-contact','Podložka baterie',k
    if k in KOV:return 'hardware',KOV[k],k
    if re.fullmatch(r'(XL|ST)\d+',k):return 'hardware',('Díl serva XL330' if k.startswith('XL') else 'Díl serva STS3215')+' · '+k,k
    if k.startswith('XL_screw'):return 'hardware','Šroub serva XL330',k
    return 'reference','Konstrukční díl '+k,k


def sestav_skupiny(items):
    grouped = {}
    for i,o in enumerate(items):
        kind,name,key=klasifikuj(o)
        side=strana(o)
        slug=key.lower().replace('_','-')
        # Kupované podsestavy popíšeme na konkrétním kloubu; všechny geometrické úseky
        # stejných šroubů v párových servech zůstávají dohledatelné přes ordinal a index.
        if kind in ('hardware','reference') and o['owner'] is not None:
            slug += f"-j{o['owner']:02d}-l{o['link']:02d}"
        slug += ('-'+side.lower()) if side else ''
        group=grouped.setdefault(slug,{'id':slug,'name':name,'side':side,'category':KLASIFIKACE[kind],
                                      'process_id':kind,'source_objects':[],'items':[]})
        source={k:o.get(k) for k in ['key','kind','owner','link']}
        source['ordinal']=sum(all(p.get(k)==source[k] for k in ('key','kind','owner','link')) for p in group['source_objects'])
        source['index']=i
        group['source_objects'].append(source)
        group['items'].append(o)
    return list(grouped.values())
