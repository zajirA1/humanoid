"""Samostatná kontrola doručených modelů. Přepínače --rezy a --lib3mf přidají hloubkový test."""
import argparse
import ctypes
import ctypes.util
import json
import struct
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODEL = '3D/3dmodel.model'
STL = np.dtype([('normal','<f4',(3,)),('p','<f4',(3,3)),('attr','<u2')])
LINE_WKB = np.dtype([('order','u1'),('typ','<u4'),('n','<u4'),('p','<f8',(2,2))])


def over(podminka, popis):
    if not podminka:
        raise ValueError(popis)


class KontrolaUsecek:
    """GEOS kontroluje, zda se řezy protínají jinde než ve společných koncích úseček."""
    def __init__(self):
        soubor = ctypes.util.find_library('geos_c')
        if not soubor:
            raise ValueError('Pro --rezy je potřeba libgeos_c.')
        self.lib = ctypes.CDLL(soubor)
        pointer = ctypes.c_void_p
        signature = {
            'GEOS_init_r': (pointer, []),
            'GEOS_finish_r': (None,[pointer]),
            'GEOSGeomFromWKB_buf_r': (pointer,[pointer,ctypes.c_char_p,ctypes.c_size_t]),
            'GEOSisSimple_r': (ctypes.c_byte,[pointer,pointer]),
            'GEOSGeom_destroy_r': (None,[pointer,pointer]),
        }
        for name,(ret,params) in signature.items():
            fn = getattr(self.lib,name)
            fn.restype = ret
            fn.argtypes = params
        self.ctx = self.lib.GEOS_init_r()

    def simple(self, segments):
        lines = np.empty(len(segments),dtype=LINE_WKB)
        lines['order'],lines['typ'],lines['n'],lines['p']=1,2,2,segments
        data = struct.pack('<BII',1,5,len(lines))+lines.tobytes()
        g = self.lib.GEOSGeomFromWKB_buf_r(self.ctx,data,len(data))
        over(bool(g),'GEOS nepřečetl řez.')
        try:
            result = self.lib.GEOSisSimple_r(self.ctx,g)
            over(result in (0,1),'Chyba při kontrole průsečíků.')
            return bool(result)
        finally:
            self.lib.GEOSGeom_destroy_r(self.ctx,g)

    def close(self):
        self.lib.GEOS_finish_r(self.ctx)


def vrstvy(vertices, faces, geos):
    edges = np.sort(faces[:,((0,1),(1,2),(2,0))],axis=2)
    pairs, idx = np.unique(edges.reshape(-1,2),axis=0,return_inverse=True)
    index = idx.reshape(-1,3)
    z = vertices[faces,2]
    floor, ceiling = z.min(1), z.max(1)
    errors=[]
    planes=0
    for height in np.arange(.10000314159, ceiling.max(), .2):
        active = (floor < height) & (height < ceiling)
        side = z[active] > height
        which = index[active][side != np.roll(side,-1,axis=1)].reshape(-1,2)
        over(len(which)>0,f'Prázdný vodorovný řez ve výšce {height:.3f} mm.')
        uniq, inv, count = np.unique(which,return_inverse=True,return_counts=True)
        over(np.all(count==2),f'Otevřené konce ve výšce {height:.3f} mm.')
        a,b=vertices[pairs[uniq,0]],vertices[pairs[uniq,1]]
        p=a[:,:2]+(b[:,:2]-a[:,:2])*((height-a[:,2])/(b[:,2]-a[:,2]))[:,None]
        if not geos.simple(p[inv.reshape(-1,2)]):
            errors.append(round(float(height),4))
        planes+=1
    return planes,errors


def data_site(zip3):
    model=ET.fromstring(zip3.read(MODEL))
    over(model.get('unit','millimeter')=='millimeter','Jednotky 3MF nejsou mm.')
    items=model.findall('{*}build/{*}item')
    over(len(items)==1,'Očekáván jeden tiskový objekt.')
    objects={o.attrib['id']:o for o in model.findall('{*}resources/{*}object')}
    return objects,items[0]


def mesh(obj):
    v=np.asarray([[float(q.attrib[k]) for k in 'xyz'] for q in obj.findall('{*}mesh/{*}vertices/{*}vertex')])
    f=np.asarray([[int(q.attrib[k]) for k in ('v1','v2','v3')] for q in obj.findall('{*}mesh/{*}triangles/{*}triangle')])
    over(len(v)>3 and len(f)>=4 and np.isfinite(v).all() and 0 <= f.min() and f.max()<len(v),'Neplatná trojúhelníková síť.')
    return v,f


def native(path):
    import lib3mf
    wrapper=lib3mf.get_wrapper();model=wrapper.CreateModel();reader=model.QueryReader('3mf')
    reader.SetStrictModeActive(True)
    reader.ReadFromFile(str(path))
    over(reader.GetWarningCount()==0,'lib3mf ohlásila varování při importu.')
    over(model.GetBuildItems().Count()==1,'lib3mf zjistila jiný počet sestav.')
    it=model.GetMeshObjects()
    while it.MoveNext():
        obj=it.GetCurrentMeshObject()
        over(obj.IsManifoldAndOriented(),'lib3mf zjistila neuzavřenou nebo chybně orientovanou síť.')


def metad(node):
    return {x.get('key'):x.get('value') for x in node.findall('metadata') if 'key' in x.attrib}


def projekt(path, corev, coref, part, config, expected, run_native, cgal=None):
    with ZipFile(path) as z:
        over(z.testzip() is None,'Vadný ZIP projektu.')
        objects,item=data_site(z)
        group=objects[item.attrib['objectid']]
        cs=[x.attrib['objectid'] for x in group.findall('{*}components/{*}component')]
        sets=ET.fromstring(z.read('Metadata/model_settings.config'))
        models=sets.findall('object')
        over(len(models)==1 and models[0].get('id')==item.attrib['objectid'],'Nejednoznačné nastavení sestavy.')
        m=models[0];normal=[n for n in m.findall('part') if n.get('subtype')=='normal_part']
        mods=[n for n in m.findall('part') if n.get('subtype')=='modifier_part']
        over(len(normal)==1 and len(mods)==len(expected) and len(cs)==len(expected)+1,'Počet tiskových a pomocných komponent neodpovídá katalogu.')
        over(set(cs)=={n.get('id') for n in m.findall('part')},'Chybná vazba ID modifikátoru.')
        v,f=mesh(objects[normal[0].attrib['id']])
        over(np.array_equal(f,coref) and np.allclose(v,corev,rtol=0,atol=1e-8),'Zesílení změnilo tvar normální části.')
        if cgal:
            over(not len(cgal(v,f,detect_only=True)[2]),'Prostorový průnik normální části v projektu X1C.')
        t=np.array([float(x) for x in item.get('transform','1 0 0 0 1 0 0 0 1 0 0 0').split()])
        over(t.size==12 and np.array_equal(t[:9].reshape(3,3),np.eye(3)), 'Projekt změnil orientaci nebo měřítko.')
        placed=v+t[9:];over(placed.min()>=-0.0001 and placed.max()<256.0001 and abs(placed[:,2].min())<0.0001, 'Projekt nesedí na podložce X1C.')
        for comp in group.findall('{*}components/{*}component'):
            over(comp.get('transform','1 0 0 0 1 0 0 0 1 0 0 0')=='1 0 0 0 1 0 0 0 1 0 0 0','Neočekávaný přesun dílu/modifikátoru v projektu.')
        params=metad(m)
        over(int(params['wall_loops'])==config['wall_loops'] and params['sparse_infill_density']==f"{config['infill_pct']}%" and params['sparse_infill_pattern']==config['infill_pattern'] and int(params['top_shell_layers'])==config['top_layers'] and int(params['bottom_shell_layers'])==config['bottom_layers'],'Proces neodpovídá třídě dílu.')
        for node,region in zip(mods,expected):
            data=metad(node);rv,rf=mesh(objects[node.attrib['id']])
            over(len(rv)==8 and len(rf)==12 and np.allclose(rv.min(0),region['min']) and np.allclose(rv.max(0),region['max']),'Zóna má jiné umístění než návrh.')
            over(data.get('sparse_infill_density')=='50%' and data.get('wall_loops')=='6','Chybné zesílení oblasti.')
            over(region.get('sampled_material_mm3',0)>0,'Chybí ověření průniku zóny s materiálem.')
        meta=json.loads(z.read('Metadata/project_settings.config'))
        over(meta['printer_settings_id']==config['machine'] and meta['print_settings_id']==config['base'],'Nesprávná tiskárna nebo profil.')
        over(not any(n.lower().endswith(('.gcode','.bgcode')) for n in z.namelist()),'V neslicovaném projektu jsou pohyby tiskárny.')
    if run_native:
        native(path)


def kontrola(base, run_native, geos, cgal=None):
    catalog=json.loads((base/'catalog.json').read_bytes())
    parts=catalog['parts']; profiles=catalog['profiles'];errors=[]
    over(len({p['id'] for p in parts})==len(parts),'Duplicitní identifikátory.')
    over(len(parts)==catalog['summary']['catalog_entries'] and sum(len(p['source_objects']) for p in parts)==catalog['summary']['source_instances'],'Nesouhlasí počet zdrojových instancí.')
    confirmed=set(); counts={'parts':0,'projects':0,'modifiers':0,'planes':0,'intersecting_planes':0}
    thin=[]; issues={}; prostor={}
    for key,prof in profiles.items():
        rel=prof['preset_file']; confirmed.add(rel);preset=json.loads((base/rel).read_bytes())
        over(preset['inherits']==prof['base'] and preset['compatible_printers']==[prof['machine']] and preset['sparse_infill_density']==f"{prof['infill_pct']}%" and int(preset['wall_loops'])==prof['wall_loops'],f'Chyba profilu {key}.')
    for p in parts:
        ident=p['id'];files=p['files']
        try:
            if not p['printable']:
                over(not files,'U netiskové položky jsou tiskové soubory.')
                continue
            counts['parts']+=1
            for role,rel in files.items():
                q=(base/rel).resolve();over(q.is_relative_to(base.resolve()) and q.is_file(),f'Chybějící nebo neplatný odkaz {rel}.')
                over(rel not in confirmed,f'Duplicitní soubor {rel}.');confirmed.add(rel)
            core,stl=base/files['model3mf'],base/files['stl']
            with ZipFile(core) as z:
                over(z.testzip() is None,'Vadný ZIP 3MF.')
                objects,item=data_site(z);over(len(objects)==1,'Čisté 3MF má další netisknutelná tělesa.')
                v,f=mesh(objects[item.attrib['objectid']])
            if run_native:
                native(core)
            data=stl.read_bytes();nf=struct.unpack_from('<I',data,80)[0]
            over(len(data)==84+nf*50 and nf==len(f),'STL má nesprávnou délku nebo počet stěn.')
            records=np.frombuffer(data,offset=84,dtype=STL)
            tris=v[f];over(np.allclose(tris,records['p'],atol=1.6e-5,rtol=0),'Geometrie STL se liší od 3MF.')
            edges=np.stack((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]),axis=1).reshape(-1,2)
            ue,cnt=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
            over(np.all(cnt==2) and len(np.unique(edges,axis=0))==2*len(ue),'Chybějící nebo chybně obrácená sousední stěna.')
            if cgal:
                # STL nemá indexy. Přebíráme jejich ověřenou korespondenci z 3MF,
                # ale testujeme skutečné souřadnice uložené jako float32 v STL.
                vertices_stl=np.empty_like(v)
                vertices_stl[f.reshape(-1)]=records['p'].reshape(-1,3)
                over(np.array_equal(vertices_stl[f],records['p']), 'STL nedrží souřadnice sdílených vrcholů.')
                pair_counts = {}
                for kind,vertices in [('3mf',v),('stl',vertices_stl)]:
                    pairs = cgal(vertices,f,detect_only=True)[2]
                    if len(pairs):
                        pair_counts[kind] = len(pairs)
                if pair_counts:
                    prostor[ident]=pair_counts
            normals=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]); lengths=np.linalg.norm(normals,axis=1)
            over(np.all(lengths>0),'Nulový trojúhelník.')
            over(np.all(np.einsum('ij,ij->i',records['normal'],normals)/lengths>.99),'Normály STL jsou obrácené.')
            vol=np.einsum('ij,ij->',tris[:,0],normals)/6000
            over(vol>0 and abs(vol-p['volume_cm3'])<.00011,'Objem nezávislého výpočtu nesouhlasí.')
            over(np.allclose(np.ptp(v,axis=0),p['print_dimensions_mm'],atol=.00011,rtol=0),'Jiný rozměr v katalogu.')
            over(np.min(v)>-0.0001 and abs(v[:,2].min())<.0001 and np.max(v)<256.0001,'Díl přesahuje desku, nebo leží nad první vrstvou.')
            over(v[:,0].min()>=18 or v[:,1].min()>=28,'Obrys může přesahovat do výřezu desky.')
            if np.ptp(v[:,2])<.5:
                thin.append(ident)
            if geos:
                n,bad=vrstvy(v,f,geos);counts['planes']+=n
                if bad:
                    counts['intersecting_planes']+=len(bad)
                    issues[ident]={'count':len(bad),'first_heights_mm':bad[:8]}
            for role,rel in files.items():
                if role in ('stl','model3mf') or not rel.endswith('.3mf'):
                    continue
                zones=p.get('reinforcement') or []
                projekt(base/rel,v,f,p,profiles[p['process_id']],zones,run_native,cgal)
                counts['projects']+=1;counts['modifiers']+=len(zones)
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            errors.append(f'{ident}: {exc}')
    over(counts['parts']==catalog['summary']['printable_count'],'Počet součástí v katalogu.')
    published={str(path.relative_to(base)) for folder in ('parts','process') for path in (base/folder).rglob('*') if path.is_file()}
    if published!=confirmed:
        errors.append('Chybějící/přebývající soubory: '+', '.join(sorted(published^confirmed)))
    if issues:
        errors.append('Nejednoduché průřezy: '+', '.join(issues))
    if prostor:
        errors.append('Průniky trojúhelníků v prostoru: '+', '.join(prostor))
    return {**counts,'thin_under_0_5mm':thin,'layer_issues':issues,'spatial_issues':prostor,'errors':errors}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,default=ROOT/'web/app/tisk/R16')
    ap.add_argument('--lib3mf',action='store_true',help='Přísný import každého 3MF pomocí SDK.')
    ap.add_argument('--rezy',action='store_true',help='Řezy po 0,2 mm a jejich průsečíky (vyžaduje GEOS).')
    ap.add_argument('--cgal',action='store_true',help='Přesné průniky trojúhelníků v celém objemu obou formátů (libigl 2.6.3).')
    ap.add_argument('--report',type=Path)
    args=ap.parse_args()
    checker=KontrolaUsecek() if args.rezy else None
    cgal=None
    if args.cgal:
        from igl.copyleft.cgal import remesh_self_intersections as cgal
    try:
        report=kontrola(args.base,args.lib3mf,checker,cgal)
    finally:
        if checker:
            checker.close()
    out=json.dumps(report,ensure_ascii=False,indent=2)
    print(out)
    if args.report:
        args.report.write_text(out+'\n',encoding='utf-8')
    sys.exit(1 if report['errors'] else 0)
