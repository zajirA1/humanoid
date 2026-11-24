"""Sestaví katalog součástí a tiskových prototypů přímo z konstrukce vydané revize."""
import argparse
import hashlib
import json
import sys
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT/'kontrola'))
from katalog import sestav_skupiny
from geometrie import priprav, okraje, kontrola, orientace, objem, rozmer, sjednot, regularizuj
from soubory import stl, zapis3mf
from process import process_for, write_presets, PROFILES
import ram


def vstup(html, model):
    with TemporaryDirectory() as temp:
        extracted=Path(temp)/'sestava.json'
        subprocess.run(['node',str(HERE/'cti-sestavu.cjs'),str(html),str(extracted)],check=True)
        scene=json.loads(extracted.read_bytes())
    items=scene['items']
    for o in items:
        v,f=[np.asarray(x).reshape(-1,3) for x in scene['meshes'][o['key']]]
        t=np.asarray(o['t']); basis=t[:9].reshape(3,3)
        o['v']=v@basis+t[9:];o['f']=f if np.linalg.det(basis)>0 else f[:,::-1]
        o.setdefault('frame',False)
    edits=model['zaklad']
    ram.prizpusob(items,edits,model['PAR'])
    # Společný tuhý posun článku nemění volný díl, ale je důležitý pro polohu
    # zesilovacích oblastí vůči skutečným namontovaným pohonům.
    offsets={22:np.zeros(3)}
    for i,p in enumerate(model['PAR'][:22]):
        e=edits.get(str(i),{})
        carried=e.get('E',e.get('d',[0,0,0]) if e.get('carry') else [0,0,0])
        offsets[i]=offsets[p]+np.asarray(carried)
    for o in items:
        if o['kind']=='cad' and not o['frame'] and o['owner'] is not None and o['owner']<22:
            j=o['owner'];e=edits.get(str(j),{})
            if e:
                if e.get('rot'):raise ValueError('Rotovaná montáž potřebuje nový výpočet tiskových zón.')
                d=np.asarray(e['d']);carry=np.asarray(e.get('E',d if e.get('carry') else [0,0,0]))
                o['v']+=d-carry if o['link']==j else d
        o['v']+=offsets[o['link']]
    return items, offsets


def zones_for(group, model, offsets, bbox, matrix, shift):
    if not group['items'][0].get('frame'):return []
    l=group['items'][0]['link'];zones=[]
    axes=[j for j,p in enumerate(model['PAR'][:22]) if j==l or p==l]
    for j in axes:
        e=model['zaklad'].get(str(j),{})
        p=np.asarray(model['P'][j])+offsets[model['PAR'][j]]+np.asarray(e.get('d',[0,0,0]))
        # Osa vede volným prostorem serva. Zesilujeme konkrétní plastovou stěnu
        # na každé straně uložení, nikoli dutou oblast uprostřed pouzdra.
        axis=np.asarray(model['AX'][j],float)
        axis/=np.linalg.norm(axis)
        vertices=group['items'][0]['v']
        for sign,side in ((-1,'A'),(1,'B')):
            target=p+sign*16*axis
            delta=np.linalg.norm(vertices-target,axis=1)
            found=int(np.argmin(delta))
            if delta[found]>29:continue
            center=vertices[found]@matrix.T+shift
            a=np.maximum(center-8,bbox[0]);b=np.minimum(center+8,bbox[1])
            if np.all(b-a>1) and not any(np.linalg.norm((a+b)/2-(np.array(z['min'])+np.array(z['max']))/2)<7 for z in zones):
                zones.append({'name':model['JN'][j]+' · uložení '+side,
                              'min':a.round(4).tolist(),'max':b.round(4).tolist()})
    return zones


def part_export(group,base,model,offsets,with_projects=True):
    its=group['items']; sources=[]
    for o in its:
        v,f=priprav(o['v'],o['f']);bad,counts=okraje(f)
        # Jediná bodová vada R16 je shodná u obou kolen. Spojíme konce
        # přibližně 0,008 mm dlouhé hrany. Změna objemu je pod 0,10 mm³.
        if len(bad)==1 and counts[0]==4 and o['key']=='r12_L_knee_ram':
            a,b=bad[0];dist=np.linalg.norm(v[a]-v[b]);vol=objem(v,f)
            if dist>=.01:raise ValueError('Neočekávaná hrana kolena')
            v[a]=v[b]=(v[a]+v[b])/2
            v,f=priprav(v,f)
            if abs(vol-objem(v,f))>=.1:raise ValueError('Změna objemu mimo mez opravy')
            group['mesh_repair_mm']=round(float(dist)/2,5)
        sources.append((v,f))
    v,f=sources[0] if len(sources)==1 else sjednot(sources)
    checks=kontrola(v,f)
    name=group['name']+(' · '+group['side'] if group['side'] else '')
    group['dimensions_mm']=rozmer(v)
    p,m,offset,contact,overhang=orientace(v,f,group['process_id']=='rigid-structure')
    # Jednotné absolutní souřadnice pro díl, případné modifikátory a profil X1C.
    dims=np.ptp(p,axis=0)
    shift=np.array([(256-dims[0])/2,(256-dims[1])/2,0])
    p=p+shift
    if p[:,0].min()<18 and p[:,1].min()<28:
        raise ValueError('Půdorys může zasahovat do vyloučeného předního rohu X1C')
    slug=group['id']; file3=f'parts/{slug}.3mf';filestl=f'parts/{slug}.stl'
    # Fáze STL převádí souřadnice na float32. U dlouhého stehenního rámu
    # to může sloučit několik vrcholů. Oba formáty dostanou tutéž ověřenou síť.
    volume_before=objem(p,f)
    p,f=priprav(p.astype(np.float32).astype(float),f)
    p,f,intersections=regularizuj(p,f)
    checks=kontrola(p,f)
    checks['source_intersection_pairs']=intersections
    checks['final_intersection_pairs']=0
    if abs(objem(p,f)-volume_before)>max(.02,abs(volume_before)*.00001):
        raise ValueError('Přesnost výměnných formátů změnila objem dílu')
    zapis3mf(base/file3,name,p,f)
    stl(base/filestl,p,f)
    index=group['process_id']
    status='Geometrie pro zkušební tisk'
    # Při záměrně složených tvarech gripperu se zatížení a uložení ověří zvlášť.
    notes='Tisk je prototyp. Zkontroluj vrstvy a dosednutí při montáži.'
    if its[0].get('_ram'):notes='Pro R16 je tento rám přetvořen v okolí ramen. Po tisku ověř souosost, tloušťku stěn a uložení obou serv.'
    if its[0]['kind']=='pickup':notes='Odnímatelný nástavec pro úchop. Geometrie prototypu vyžaduje ověření spojů, přenosu síly a upevnění.'
    if intersections:
        notes+=' Při přípravě tisku se odstranily lokálně překryté trojúhelníky. Vnitřní dutiny a montážní rozměry jsou zachovány.'
    if dims[2] < 0.6:notes='Tenký ozdobný prvek. Při výšce vrstvy 0,20 mm vycházejí přibližně dvě vrstvy. Ověř přilnavost a obrys ve sliceru. Není určen k přenosu zatížení.'
    if index=='flexible-contact':notes='Ověř tření, deformaci i připevnění vzorku TPU. Model sám neurčuje skutečnou tvrdost ani dovolené zatížení.'
    group.update({'printable':True,'status':status,'quantity':1,'files':{'model3mf':file3,'stl':filestl},
                  'print_dimensions_mm':rozmer(p), 'volume_cm3':round(objem(p,f)/1000,5),
                  'solid_mass_reference_g':round(objem(p,f)/1000*(1.21 if index=='flexible-contact' else 1.27),2),
                  'solid_reference_density_g_cm3':1.21 if index=='flexible-contact' else 1.27,
                  'weight_estimate_g':None,'checks':checks,
                  'orientation':f'Plocha kontaktu první vrstvy přibližně {contact:.1f} mm². Výška {dims[2]:.2f} mm.',
                  'contact_mm2':round(contact,2),'overhang_mm2':round(overhang,2), 'notes':notes})
    zones=zones_for(group,model,offsets,(p.min(0),p.max(0)),m,offset+shift)
    group['reinforcement']=zones
    if with_projects:
        from reinforcement import write_reinforced_project,write_process_project
        project=f'parts/{slug}-x1c.3mf'
        try:
            result=(write_reinforced_project(base/file3,base/project,zones,index,name) if zones else
                    write_process_project(base/file3,base/project,index,name))
        except ValueError as exc:
            if str(exc)!='Ve zvolených zónách se průsečíky s materiálem dílu nepotvrdily.': raise
            result=write_process_project(base/file3,base/project,index,name)
        group['files']['project3mf']=project
        group['project']=result
        group['reinforcement']=result['zones']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'web/app/tisk/R16')
    parser.add_argument('--html',type=Path,default=ROOT/'web/app/emil-h22.html')
    parser.add_argument('--without-projects',action='store_true')
    args=parser.parse_args()
    model=json.loads((ROOT/'kontrola/data/model.json').read_bytes())
    if model.get('revize')!='R16':raise ValueError('Pro tuto sadu tiskových přípravků je nutná revize R16')
    items,offsets=vstup(args.html,model)
    groups=sestav_skupiny(items)
    base=args.output; (base/'parts').mkdir(parents=True,exist_ok=True)
    write_presets(base)
    for g in groups:
        if g['process_id'] in PROFILES:
            part_export(g,base,model,offsets,not args.without_projects)
        else:
            g.update(printable=False,files={},quantity=1,status=g['category'],
                     notes='Model znázorňuje zakoupený prvek nebo jeho montážní prostor.' if g['process_id']=='hardware' else 'Povrchová značka nebo pracovní geometrie. Je součástí návrhu sestavy.')
        del g['items']
    count=sum(g['printable'] for g in groups)
    catalog={'revision':'R16','unit':'mm','parts':groups,
             'profiles':{key:process_for(key) for key in PROFILES},
             'summary':{'source_instances':len(items),'catalog_entries':len(groups),'printable_count':count,
                        'prototype_only':True,'physically_tested':False},
             'mass_note':'Objem × referenční hustota znamená plný materiál bez výplně a podpor. Hmotnost navrženého výtisku dopočítá slicer dle procesu a filamentu.'}
    filenames={path for group in groups for path in group.get('files',{}).values()}
    filenames.update(p['preset_file'] for p in catalog['profiles'].values())
    catalog['file_checksums']={path:hashlib.sha256((base/path).read_bytes()).hexdigest() for path in sorted(filenames)}
    (base/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=1)+'\n')
    print('Katalog R16:',len(items),'instancí,',len(groups),'položek,',count,'tiskových dílů.')


if __name__=='__main__':
    main()
