"""Neslicovaný projekt X1C. Jediným tištěným dílem je původní uzavřená síť."""

import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np

from process import process_for

CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
BBL = "http://schemas.bambulab.com/package/2021"
MODEL = "3D/3dmodel.model"
IDENTITY = (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0)
MATRIX = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
# Stejná orientace vrcholů na všech šesti stěnách uzavřeného kvádru.
BOX_FACES = ((0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
             (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7))


def metadata(node, values):
    for k, v in values.items():
        ET.SubElement(node, "metadata", key=k, value=str(v))


def write_entry(archive, name, payload):
    info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    archive.writestr(info, payload, compress_type=ZIP_DEFLATED, compresslevel=6)


def xyz(pt):
    return dict(zip("xyz", (format(x, ".12g") for x in pt)))


def add_mesh(resources, id_, name, points, faces):
    obj = ET.SubElement(resources, "object", id=str(id_), type="model", name=name)
    mesh = ET.SubElement(obj, "mesh")
    vertices = ET.SubElement(mesh, "vertices")
    for point in points:
        ET.SubElement(vertices, "vertex", xyz(point))
    triangles = ET.SubElement(mesh, "triangles")
    for a, b, c in faces:
        ET.SubElement(triangles, "triangle", v1=str(a), v2=str(b), v3=str(c))


def parse_core(source):
    with ZipFile(source) as package:
        model = ET.fromstring(package.read(MODEL))
    if model.get("unit", "millimeter") != "millimeter":
        raise ValueError("Zesílení očekává milimetrové měřítko.")
    items = model.findall("{*}build/{*}item")
    if len(items) != 1:
        raise ValueError("Zesílení vyžaduje jednotlivou sestavenou součást.")
    item = items[0]
    obj = model.find("{*}resources/{*}object[@id='" + item.attrib["objectid"] + "']")
    if obj is None or obj.find("{*}mesh") is None:
        raise ValueError("Výchozí díl musí být jediná síť.")
    mat = [float(x) for x in item.get("transform", " ".join(map(str, IDENTITY))).split()]
    if len(mat) != 12 or not all(map(math.isfinite, mat)):
        raise ValueError("Neplatná transformace tiskového dílu.")
    points = []
    for v in obj.findall("{*}mesh/{*}vertices/{*}vertex"):
        x, y, z = (float(v.attrib[k]) for k in "xyz")
        points.append(tuple(x*mat[k]+y*mat[3+k]+z*mat[6+k]+mat[9+k] for k in range(3)))
    faces = [tuple(int(t.attrib[k]) for k in ("v1","v2","v3"))
             for t in obj.findall("{*}mesh/{*}triangles/{*}triangle")]
    det = (mat[0]*(mat[4]*mat[8]-mat[5]*mat[7]) - mat[1]*(mat[3]*mat[8]-mat[5]*mat[6])
           + mat[2]*(mat[3]*mat[7]-mat[4]*mat[6]))
    if not points or not faces or abs(det) < 1e-10 or not all(math.isfinite(n) for p in points for n in p):
        raise ValueError("Geometrie výchozího tělesa není platná.")
    if det < 0:
        faces = [(a,c,b) for a,b,c in faces]
    return obj.get("name", Path(source).stem), points, faces


def clip_zones(zones, lower, upper):
    clipped = []
    for i, zone in enumerate(zones):
        lo, hi = zone["min"], zone["max"]
        if len(lo) != 3 or len(hi) != 3 or not all(math.isfinite(float(x)) for x in (*lo,*hi)):
            raise ValueError("Modifikátor musí mít tři platné meze v každém směru.")
        if any(float(b) <= float(a) for a, b in zip(lo, hi)):
            raise ValueError("Prázdný modifikátor.")
        lo = [max(float(a), b) for a, b in zip(lo, lower)]
        hi = [min(float(a), b) for a, b in zip(hi, upper)]
        if any(b-a <= 0.01 for a, b in zip(lo, hi)):
            continue
        clipped.append({"name": str(zone.get("name", f"Zóna {i+1}")), "min":lo, "max":hi})
    return clipped


def material_inside(points, faces, regions):
    """Délky tětiv uvnitř sítě odhadnou kolik plastového objemu zóna skutečně protíná."""
    tri = np.asarray(points)[np.asarray(faces)]
    found = []
    for region in regions:
        lo = np.array(region["min"]); hi = np.array(region["max"])
        # Všechny trojúhelníky promítáme do roviny YZ. Vzdálenost X při
        # průsečíku dopočítají barycentrické souřadnice. Svislé tečny přeskočíme.
        spans = ((tri[:,:,1:].max(axis=1) >= lo[1:]) & (tri[:,:,1:].min(axis=1) <= hi[1:])).all(axis=1)
        a = tri[spans,0]; edge1 = tri[spans,1]-a; edge2 = tri[spans,2]-a
        determinant = edge1[:,1]*edge2[:,2] - edge1[:,2]*edge2[:,1]
        keep = np.abs(determinant) > 1e-12
        if not np.any(keep):
            continue
        a, edge1, edge2, determinant = a[keep], edge1[keep], edge2[keep], determinant[keep]
        widths = hi-lo
        for resolution in (7, 19):
            occupied = 0.0
            ok = 0
            for iy in range(resolution):
                dy = lo[1]+widths[1]*(iy+0.504871)/resolution-a[:,1]
                for iz in range(resolution):
                    dz = lo[2]+widths[2]*(iz+0.499213)/resolution-a[:,2]
                    u = (dy*edge2[:,2]-dz*edge2[:,1])/determinant
                    v = (edge1[:,1]*dz-edge1[:,2]*dy)/determinant
                    hit = (u>=0) & (v>=0) & (u+v<=1)
                    hits = np.sort(a[hit,0] + u[hit]*edge1[hit,0] + v[hit]*edge2[hit,0])
                    if hits.size:
                        hits = hits[np.r_[True, np.diff(hits) > 1e-7]]
                    if hits.size % 2:
                        continue
                    ok += 1
                    occupied += np.maximum(0, np.minimum(hits[1::2],hi[0])-np.maximum(hits[::2],lo[0])).sum()
            if ok and occupied>1e-7:
                found.append({**region,"sampled_material_mm3":round(occupied*widths[1]*widths[2]/ok,3),
                              "sampled_rays":ok})
                break
    return found


def write_reinforced_project(solid_3mf, output_3mf, zones, process_id="rigid-structure", name=None):
    """Krabičky v tiskových souřadnicích přidají lokální výplň pouze uvnitř sítě."""
    if not zones:
        raise ValueError("Projekt zesílení vyžaduje alespoň jednu zónu.")
    return _write_project(solid_3mf, output_3mf, zones, process_id, name)


def write_process_project(solid_3mf, output_3mf, process_id, name=None):
    """Projekt s nastavením samotného objektu bez objemů modifikujících výplň."""
    return _write_project(solid_3mf, output_3mf, [], process_id, name)


def _write_project(solid_3mf, output_3mf, zones, process_id, name):
    process = process_for(process_id)
    source_name, points, faces = parse_core(solid_3mf)
    name = name or source_name
    lo = [min(c) for c in zip(*points)]
    hi = [max(c) for c in zip(*points)]
    regions = material_inside(points, faces, clip_zones(zones, lo, hi)) if zones else []
    if zones and not regions:
        raise ValueError("Ve zvolených zónách se průsečíky s materiálem dílu nepotvrdily.")
    size = [b-a for a,b in zip(lo,hi)]
    if max(size) > 256.0001:
        raise ValueError("Díl přesahuje prostor tiskárny X1C v navržené orientaci.")
    # Doprostřed desky. Při velkém půdorysu se přední levý roh může překrývat
    # s vyloučeným prostorem řezačky X1C, v takovém případě nepřipravujeme projekt.
    origin = [(256-size[0])/2, (256-size[1])/2, 0]
    if origin[0] < 18 and origin[1] < 28:
        raise ValueError("Půdorys může zasahovat do výřezu řezačky X1C.")
    build_t = "1 0 0 0 1 0 0 0 1 " + " ".join(format(o-v, ".12g") for o,v in zip(origin,lo))

    model = ET.Element("model", xmlns=CORE, unit="millimeter",
                       attrib={"xml:lang":"cs-CZ", "xmlns:BambuStudio":BBL})
    # Toto označení verze je referenční formát. Importér podle prefixu Application
    # aktivuje rozpoznávání podtypů součástí; vlastní generátor dokládáme zvlášť.
    for key, txt in (("Application","BambuStudio-01.09.00.06"),("BambuStudio:3mfVersion","1"),
                     ("Designer","Humanoid H22"),("Title",name),
                     ("Description","Projekt sestavený nástrojem Humanoid H22. " + ("Zóny mění pouze parametry výplně v základním tělese." if regions else "Jeden objekt s procesním nastavením pro X1C.")),
                     ("BambuStudio:Generator","Humanoid H22 R16")):
        ET.SubElement(model, "metadata", name=key).text = txt
    resources = ET.SubElement(model, "resources")
    add_mesh(resources, 1, name, points, faces)
    for i, region in enumerate(regions, 2):
        x,y,z = region["min"]; X,Y,Z = region["max"]
        corners = ((x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z))
        add_mesh(resources, i, region["name"], corners, BOX_FACES)
    group_id = len(regions)+2
    group = ET.SubElement(resources, "object", id=str(group_id), type="model", name=name)
    comps = ET.SubElement(group, "components")
    for mesh_id in range(1,group_id):
        ET.SubElement(comps, "component", objectid=str(mesh_id))
    ET.SubElement(ET.SubElement(model,"build"), "item", objectid=str(group_id), transform=build_t)

    settings = ET.Element("config")
    obj = ET.SubElement(settings,"object",id=str(group_id))
    metadata(obj, {"name":name,"extruder":1, "wall_loops":process["wall_loops"],
                   "sparse_infill_density":f"{process['infill_pct']}%", "sparse_infill_pattern":"gyroid",
                   "top_shell_layers":process["top_layers"],"bottom_shell_layers":process["bottom_layers"],
                   "top_shell_thickness":f"{process['top_layers']*0.2:.1f}",
                   "bottom_shell_thickness":f"{process['bottom_layers']*0.2:.1f}"})
    ET.SubElement(obj,"metadata", face_count=str(len(faces) + 12*len(regions)))
    solid = ET.SubElement(obj,"part",id="1", subtype="normal_part")
    metadata(solid, {"name":name,"matrix":MATRIX,"extruder":1})
    for i, region in enumerate(regions, 2):
        part = ET.SubElement(obj,"part",id=str(i),subtype="modifier_part")
        metadata(part,{"name":region["name"],"matrix":MATRIX,"sparse_infill_density":"50%",
                       "sparse_infill_pattern":"gyroid","wall_loops":6})
    plate = ET.SubElement(settings,"plate")
    metadata(plate,{"plater_id":1,"plater_name":name,"locked":"false"})
    metadata(ET.SubElement(plate,"model_instance"),{"object_id":group_id,"instance_id":0,"identify_id":1})
    ET.SubElement(ET.SubElement(settings,"assemble"),"assemble_item",object_id=str(group_id),instance_id="0",
                  transform=build_t,offset="0 0 0")
    # Zachováme tovární proces a obálku tiskárny, místní nastavení patří objektu.
    # Přesný typ podložky a profil skutečné cívky se vybírají před plátkováním.
    filament = "TPU" if process_id=="flexible-contact" else "PETG"
    project = {"version":"01.09.00.06", "printer_technology":"FFF", "printer_settings_id":process["machine"],
               "printer_model":"Bambu Lab X1 Carbon", "printer_variant":"0.4", "nozzle_diameter":["0.4"],
               "print_settings_id":process["base"], "filament_settings_id":[f"Generic {filament}"],
               "filament_type":[filament], "filament_diameter":["1.75"], "filament_colour":["#87969C"],
               "printable_area":["0x0","256x0","256x256","0x256"], "printable_height":"256",
               "bed_exclude_area":["0x0","18x0","18x28","0x28"], "enable_prime_tower":"0"}
    types = ET.Element("Types",xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    for ext,val in (("rels","application/vnd.openxmlformats-package.relationships+xml"),
                    ("model","application/vnd.ms-package.3dmanufacturing-3dmodel+xml"),("config","application/octet-stream")):
        ET.SubElement(types,"Default",Extension=ext,ContentType=val)
    rels=ET.Element("Relationships",xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
    ET.SubElement(rels,"Relationship",Target="/"+MODEL,Id="rel0",Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
    out = Path(output_3mf)
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,"w") as archive:
        for path, xml in (("[Content_Types].xml",types),("_rels/.rels",rels),(MODEL,model),
                          ("Metadata/model_settings.config",settings)):
            write_entry(archive,path,ET.tostring(xml,encoding="utf-8",xml_declaration=True))
        write_entry(archive,"Metadata/project_settings.config",json.dumps(project,indent=2,ensure_ascii=False).encode())
    return {"file":out.name,"normal_parts":1,"modifier_count":len(regions),"zones":regions,
            "infill_pct":50 if regions else process["infill_pct"],
            "wall_loops":6 if regions else process["wall_loops"],"native_slice_verified":False,
            "note":"Otevři v Bambu Studiu jako projekt. " + ("Ve stromu součástí jsou zóny modifikátory. " if regions else "") + "V náhledu po rozřezání zkontroluj výplň, podpěry a volné otvory. Pro jiné slicery použij samostatnou čistou geometrii."}
