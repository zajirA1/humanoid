"""Sestaví Emil V3.1 z modelu V2 (nebo původního archivu V1) a výrobních STL.

Usage: python build_scene.py Emil-V2.glb Emil-V3.1.glb
Design coordinates are millimetres, Y up. glTF translations and meshes are metres.
"""
import argparse
import copy
import json
import math
import struct
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
TISK = SRC.parents[1] / 'web' / 'app' / 'tisk' / 'emil'
DECK_BOTTOM = 98.5  # Horní víčko a návrhová vrstva lepidla 0,5 mm.
DECK_TOP = DECK_BOTTOM + 7
TABLET_CENTER = (-56, DECK_TOP + 77 + 181.85 / 2, 0)


def mm(values):
    return [v / 1000 for v in values]


def quaternion(axis, angle):
    half = math.radians(angle) / 2
    return [*(value * math.sin(half) for value in axis), math.cos(half)]


def read_reference(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("Emil-V1.glb")
    else:
        raw = path.read_bytes()
    if raw[:4] != b"glTF":
        raise ValueError("Expected a binary glTF model or the original V1 archive")
    length = struct.unpack_from("<I", raw, 12)[0]
    return json.loads(raw[20:20 + length]), raw[28 + length:]


class Scene:
    def __init__(self):
        self.doc = {
            "asset": {"version": "2.0", "generator": "Emil V3.1 • ETA 5229, Waveshare WAV083, Yahboom"},
            "scene": 0, "scenes": [{"name": "Emil V3.1", "nodes": [0]}],
            "nodes": [], "meshes": [], "materials": [], "buffers": [],
            "bufferViews": [], "accessors": [],
        }
        self.blob = bytearray()
        self.shapes = {}
        self.obstacles = []

    def append(self, array, item):
        items = self.doc[array]
        items.append(item)
        return len(items) - 1

    def view(self, data, target=34962):
        self.blob.extend(bytes(-len(self.blob) % 4))
        index = self.append("bufferViews", {
            "buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data),
            "target": target,
        })
        self.blob.extend(data)
        return index

    def import_emil(self, source, binary):
        # Zůstává podvozek, obličej tabletu, přepravní miska a zkušební koule.
        # Původní příruba, červený talíř, sloupek a kamera nad tabletem se vyřadí.
        if source["nodes"][73]["name"] == "WS_Payload":
            payload = 73
        elif source["nodes"][73]["name"] == "Patka manipulátoru" and "ponožky" in source["nodes"][99]["name"]:
            payload = 99
        else:
            raise ValueError("The reference must contain the original V1/V2 Emil body")
        retained = [*range(23), 39, 40, *range(42, 64), *range(68, 73), payload]
        nodes = {old: new for new, old in enumerate(retained)}
        meshes, materials, views, accessors = {}, {}, {}, {}

        def import_accessor(old):
            if old in accessors:
                return accessors[old]
            acc = copy.deepcopy(source["accessors"][old])
            view_id = acc["bufferView"]
            view = source["bufferViews"][view_id]
            if view_id not in views:
                start = view.get("byteOffset", 0)
                views[view_id] = self.view(binary[start:start + view["byteLength"]], view.get("target", 34962))
                if "byteStride" in view:
                    self.doc["bufferViews"][views[view_id]]["byteStride"] = view["byteStride"]
            acc["bufferView"] = views[view_id]
            accessors[old] = self.append("accessors", acc)
            return accessors[old]

        for old in retained:
            node = copy.deepcopy(source["nodes"][old])
            if 68 <= old <= 72:  # Dno a stěny misky byly ve V1/V2 na talíři ve výšce 115 mm.
                node['translation'][1] += (DECK_TOP - 115) / 1000
            if old == 42:
                node["name"] = "Redmi Pad Pro • svisle"
                node["translation"] = mm(TABLET_CENTER)
                node.pop("rotation", None)
                # Výchozí V1 měl zjednodušené tělo 9 × 177 × 282 mm.
                node["scale"] = [7.52 / 9, 181.85 / 177, 280 / 282]
            if node.get("children"):
                node["children"] = [nodes[i] for i in node["children"] if i in nodes]
            if old == payload:
                node["name"] = "WS_Payload"
                node["translation"] = mm((212, 16, 125))
            if "mesh" in node:
                key = node["mesh"]
                if key not in meshes:
                    mesh = copy.deepcopy(source["meshes"][key])
                    for prim in mesh["primitives"]:
                        material = prim["material"]
                        if material not in materials:
                            materials[material] = self.append("materials", source["materials"][material])
                        prim["material"] = materials[material]
                        prim["attributes"] = {k: import_accessor(v) for k, v in prim["attributes"].items()}
                        if "indices" in prim:
                            prim["indices"] = import_accessor(prim["indices"])
                    meshes[key] = self.append("meshes", mesh)
                node["mesh"] = meshes[key]
            self.append("nodes", node)

    def material(self, name, srgb, metallic=0, roughness=0.5):
        def linear(value):
            value /= 255
            return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        return self.append("materials", {"name": name, "pbrMetallicRoughness": {
            "baseColorFactor": [*(linear(v) for v in srgb), 1],
            "metallicFactor": metallic, "roughnessFactor": roughness,
        }})

    def node(self, parent, name, xyz=(0, 0, 0), rotation=None, mesh=None):
        node = {"name": name, "translation": mm(xyz)}
        if rotation is not None:
            node["rotation"] = rotation
        if mesh is not None:
            node["mesh"] = mesh
        index = self.append("nodes", node)
        self.doc["nodes"][parent].setdefault("children", []).append(index)
        return index

    def polygon(self, parent, name, outline, depth, material, xyz, rotation=None):
        # Simple convex/convex-star-shaped sections in XY, extruded along Z.
        # Use triangle lists with explicit flat normals, including caps.
        key = (tuple(map(tuple, outline)), depth, material)
        if key not in self.shapes:
            centroid = tuple(sum(p[a] for p in outline) / len(outline) for a in (0, 1))
            vertices, normals = [], []

            def tri(a, b, c):
                u = [b[i] - a[i] for i in range(3)]
                v = [c[i] - a[i] for i in range(3)]
                cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                length = math.sqrt(sum(q*q for q in cross))
                normal = [q / length for q in cross]
                vertices.extend(mm(p) for p in (a, b, c))
                normals.extend([normal] * 3)

            front, rear = depth / 2, -depth / 2
            for a, b in zip(outline, [*outline[1:], outline[0]]):
                af = (*a, front)
                ar = (*a, rear)
                bf = (*b, front)
                br = (*b, rear)
                tri((*centroid, front), af, bf)
                tri((*centroid, rear), br, ar)
                tri(ar, br, bf)
                tri(ar, bf, af)

            def accessor(rows, bounds=False):
                blob = b"".join(struct.pack("<3f", *row) for row in rows)
                acc = {"bufferView": self.view(blob), "componentType": 5126, "count": len(rows), "type": "VEC3"}
                if bounds:
                    packed = list(struct.iter_unpack("<3f", blob))
                    acc["min"] = list(map(min, zip(*packed)))
                    acc["max"] = list(map(max, zip(*packed)))
                return self.append("accessors", acc)
            prim = {"attributes": {"POSITION": accessor(vertices, True), "NORMAL": accessor(normals)}, "material": material}
            self.shapes[key] = self.append("meshes", {"name": name, "primitives": [prim]})
        return self.node(parent, name, xyz, rotation, self.shapes[key])

    def box(self, parent, name, size, material, xyz, rotation=None):
        a, b, depth = size[0] / 2, size[1] / 2, size[2]
        return self.polygon(parent, name, [(-a, -b), (a, -b), (a, b), (-a, b)], depth, material, xyz, rotation)

    def disc(self, parent, name, diameter, depth, material, xyz, rotation=None, sides=18):
        outline = [(diameter/2 * math.cos(2*math.pi*i/sides), diameter/2 * math.sin(2*math.pi*i/sides)) for i in range(sides)]
        return self.polygon(parent, name, outline, depth, material, xyz, rotation)

    def link(self, parent, name, length, width, thick, material, xyz, rotation=None):
        # Capsule between two revolute centres, local forward axis +X.
        outline = []
        for cx, start in ((length, -90), (0, 90)):
            for k in range(9):
                angle = math.radians(start + 180*k/8)
                outline.append((cx + width/2*math.cos(angle), width/2*math.sin(angle)))
        return self.polygon(parent, name, outline, thick, material, xyz, rotation)

    def stl(self, filename, name, material, transform):
        """Importuje stejný výrobní povrch jako soubor ke stažení. Matice je v mm."""
        mesh_file = TISK / filename
        raw = mesh_file.read_bytes()
        count = struct.unpack_from("<I", raw, 80)[0]
        if len(raw) == 84 + 50 * count:
            triangles = [[p[3:6], p[6:9], p[9:12]]
                         for p in struct.iter_unpack("<12fH", raw[84:])]
        else:
            vertices = [tuple(map(float, line.split()[1:])) for line in raw.decode("ascii").splitlines()
                        if line.lstrip().startswith("vertex ")]
            if not vertices or len(vertices) % 3:
                raise ValueError(f"Neplatné STL: {filename}")
            triangles = [vertices[i:i+3] for i in range(0, len(vertices), 3)]

        points, normals = bytearray(), bytearray()
        minimum, maximum = [math.inf] * 3, [-math.inf] * 3
        for tri in triangles:
            world = [tuple(sum(a*b for a,b in zip(row[:3], p)) + row[3] for row in transform)
                     for p in tri]
            u = [b-a for a,b in zip(world[0], world[1])]
            v = [b-a for a,b in zip(world[0], world[2])]
            normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            length = math.hypot(*normal)
            if length <= 1e-8:
                continue
            normals.extend(struct.pack("<3f", *(component/length for component in normal))*3)
            for vertex in world:
                points.extend(struct.pack("<3f", *mm(vertex)))
                for dim, pos in enumerate(vertex):
                    minimum[dim] = min(minimum[dim], pos)
                    maximum[dim] = max(maximum[dim], pos)
        if not points:
            raise ValueError(f"Prázdné STL: {filename}")
        size = len(points)//12
        # Použij skutečné meze uložených 32bitových souřadnic pro glTF.
        stored = list(zip(*struct.iter_unpack("<3f", points)))
        positions = self.append("accessors", {"bufferView": self.view(points), "componentType": 5126,
            "count": size, "type": "VEC3", "min": list(map(min,stored)), "max": list(map(max,stored))})
        directions = self.append("accessors", {"bufferView": self.view(normals), "componentType": 5126,
            "count": size, "type": "VEC3"})
        geom = self.append("meshes", {"name":name, "primitives":[{"material":material,
            "attributes":{"POSITION":positions,"NORMAL":directions}}]})
        node = self.node(1, name, mesh=geom)
        self.doc["nodes"][node]["extras"] = {"stl": filename, "print_to_world_mm": transform}
        return [[round(v,3) for v in minimum], [round(v,3) for v in maximum]]

    def write(self, file):
        self.doc["buffers"] = [{"byteLength": len(self.blob)}]
        meta = json.dumps(self.doc, ensure_ascii=False, separators=(",", ":")).encode()
        meta += b" " * (-len(meta) % 4)
        binary = bytes(self.blob) + bytes(-len(self.blob) % 4)
        data = struct.pack("<4sII", b"glTF", 2, 28 + len(meta) + len(binary))
        data += struct.pack("<I4s", len(meta), b"JSON") + meta
        data += struct.pack("<I4s", len(binary), b"BIN\0") + binary
        file.write_bytes(data)


def make_arm(s):
    # Published dimensions: Waveshare Robot-Arm-for-Pi-size.jpg. Pivot lengths
    # and local plate outlines are approximations for layout, not production CAD.
    blue = s.material("Modře eloxovaný hliník", (36, 94, 178), .32, .36)
    edge = s.material("Světle modré spojnice", (57, 125, 206), .29, .36)
    servo = s.material("Černá pouzdra serv", (43, 48, 53), .08, .49)
    steel = s.material("Ocelové čepy", (191, 199, 204), .55, .30)
    brass = s.material("Mosazné distanční sloupky", (179, 144, 83), .43, .38)
    green = s.material("Deska Raspberry Pi", (45, 111, 72), 0, .61)
    pcb = s.material("Modrá deska PCA9685 HAT", (44, 77, 121), .05, .54)
    signal = s.material("Signálové piny", (207, 164, 67), .25, .44)
    x_axis, z_axis = (1, 0, 0), (0, 0, 1)
    horizontal = quaternion(x_axis, -90)
    zrot = lambda degree: quaternion(z_axis, degree)

    mount = s.node(1, "Waveshare Robot Arm for Pi • WAV083", (91, DECK_TOP, 55))
    # Retain the complete supplied rectangular base and controller. Rotation axis
    # lies 40 mm from the front edge of the 149.6 mm long plate.
    plate = [(-36,-74.8),(36,-74.8),(40,-70.8),(40,70.8),(36,74.8),(-36,74.8),(-40,70.8),(-40,-70.8)]
    s.polygon(mount, "Základová deska Waveshare", plate, 2, blue, (0, 8.37, -34.8), horizontal)
    for x in (-34, 34):
        for z in (-102, 33):
            s.disc(mount, "Spodní distanční sloupek", 6, 7.37, brass, (x, 3.685, z), horizontal, 6)
            s.disc(mount, "Šroub základny", 4.3, 1.3, steel, (x, 10.0, z), horizontal, 12)
    s.box(mount, "Servo MG996R • otočení", (40.5, 35, 20), servo, (0, 21.6, -4))
    s.box(mount, "Upevňovací příruba MG996R", (51, 2.8, 21), servo, (0, 32, -4))
    for x in (-24.5, 24.5):
        for z in (-24.5, 24.5):
            s.disc(mount, "Sloupek horní desky", 5, 25, brass, (x, 21.87, z), horizontal, 6)
            s.disc(mount, "Hlava strojního šroubu", 4.3, 1.3, steel, (x, 36.8, z), horizontal)
    s.box(mount, "Deska pod otočí", (60, 2, 60), edge, (0, 35.2, 0))

    # The V2 model represents the Pi assembly as a layout envelope, not a PCB design.
    s.box(mount, "Raspberry Pi • nosná DPS", (54, 1.6, 68), green, (0, 17.3, -70))
    for x in (-23, 23):
        for z in (-94, -45):
            s.disc(mount, "Distanční sloupek HAT", 4.1, 12, brass, (x, 22.6, z), horizontal, 6)
    s.box(mount, "Servo Driver HAT", (51, 1.6, 50), pcb, (0, 29, -65))
    s.box(mount, "PCA9685", (8, 1.8, 6), servo, (2, 30.6, -61))
    for x in (-13, 5, 19):
        s.box(mount, "Konektor Raspberry Pi", (12, 12, 15), steel, (x, 23.3, -100))
        s.box(mount, "Otvor konektoru", (9, 8, 1), servo, (x, 23.3, -107.5))
    for row in (-5, 0, 5):
        s.box(mount, "Lišta servo konektorů", (3.2, 4.2, 39), servo, (row-13, 32, -64))
        for k in range(12):
            s.box(mount, "Pin PWM", (1, 3, 1), signal, (row-13, 35, -81 + k*3))

    parked = {"yaw": 10, "upper": 75, "fore": -25, "gap": 40}
    yaw = s.node(mount, "WS_Yaw", (0,80,0), quaternion((0,1,0), -parked["yaw"]))
    s.disc(yaw, "Unašeč otoče", 33, 3.2, steel, (0,-41,0), horizontal)
    s.box(yaw, "Dno U třmenu", (49, 3, 43), blue, (0,-37,0))
    cheeks = [(-25,-36),(23,-36),(23,3),(18,9),(-17,9),(-25,4)]
    for side in (-1, 1):
        s.polygon(yaw, "Bočnice otočné kolébky", cheeks, 2.1, blue, (0,0,side*20.3))
        s.box(yaw, "Servo MG90S • pákový převod", (23,12.5,22), servo, (-3,-7,side*15.3))
        s.box(yaw, "Montážní patky MG90S", (31,3,13), servo, (-2,-5,side*19.0))

    upper = s.node(yaw, "WS_Upper", rotation=zrot(parked["upper"]))
    upper_parallel = s.node(yaw, "WS_UpperParallel", (-13,6,0), zrot(parked["upper"]))
    elbow = s.node(upper, "WS_ElbowLevel", (86.2,0,0), zrot(-parked["upper"]))
    fore = s.node(upper, "WS_Fore", (86.2,0,0), zrot(parked["fore"] - parked["upper"]))
    fore_parallel = s.node(elbow, "WS_ForeParallel", (0,10,0), zrot(parked["fore"]))
    wrist = s.node(fore, "WS_Hand", (128,0,0), zrot(-parked["fore"]))

    for side in (-1, 1):
        s.link(upper, "Zdvihové rameno", 86.2, 8, 2.1, blue, (0,0,16*side))
        s.link(upper_parallel, "Paralelní táhlo zdvihu", 86.2, 4.9, 1.8, edge, (0,0,12.2*side))
        # Level triangular rocker ties the two pairs of parallelogram pivots.
        rocker = [(-16,2),(-2,-4),(4,-2),(4,12),(-2,14),(-16,9)]
        s.polygon(elbow, "Trojúhelník loketního převodu", rocker, 2.3, blue, (0,0,13*side))
        s.link(fore, "Předloktí • dolní páka", 128, 6.7, 2.1, blue, (0,0,10.2*side))
        s.link(fore_parallel, "Předloktí • horní táhlo", 128, 4.8, 1.8, edge, (0,0,7.9*side))
        s.link(wrist, "Čelní spojka", 10, 8, 2.2, blue, (0,0,9.6*side), zrot(90))
    for group, pivots in ((yaw, [(0,0),(-13,6)]), (elbow, [(0,0),(-13,6),(0,10)]), (wrist, [(0,0),(0,10)])):
        span = 49 if group == yaw else (37 if group == elbow else 26)
        for x,y in pivots:
            s.disc(group, "Čep čtyřčlenu", 2.9, span, steel, (x,y,0))
            for side in (-1, 1):
                s.disc(group, "Hlava čepu", 4.5, 1.5, brass, (x,y,side*span/2))

    s.box(wrist, "Nosník chapadla", (28,3,26), blue, (7,5,0))
    s.box(wrist, "Servo chapadla MG90S", (22.5,19.5,12), servo, (7,16,0))
    s.box(wrist, "Příruba serva chapadla", (31.5,2.1,13), servo, (6,7.5,0))
    for side, name in ((-1, "WS_Jaw_L"), (1, "WS_Jaw_R")):
        # Opposed gear sectors remain attached to the wrist; the usable contact
        # gap is the independent control in this approximation. Thin guide tabs
        # cover the represented cam movement at all supported openings.
        gear = []
        for i in range(48):
            angle = 2*math.pi*i/48
            radius = 7.5 if i % 4 in (1,2) else 6.8
            gear.append((radius*math.cos(angle), radius*math.sin(angle)))
        s.polygon(wrist, "Ozubený sektor úchopu", gear, 2.6, steel, (10,1.1,side*6.9), horizontal)
        s.disc(wrist, "Čep ozubeného sektoru", 3.5, 4, brass, (10,1.8,side*6.9), horizontal)
        s.box(wrist, "Vodicí část čelisti", (8,1.7,19), steel, (15,0.5,side*10))
        jaw = s.node(wrist, name, (0,0,side*parked["gap"]/2))
        blade = [(9,0),(40,0),(42,1),(41,3),(28,4),(14,7),(9,5)]
        # The inner contact surface lies precisely at +/- gap/2.
        outline = [(x, -side*z) for x,z in blade]
        if side > 0:
            outline.reverse()
        s.polygon(jaw, "Tvarovaná kovová čelist", outline, 2, steel, (0,0,0), horizontal)
        s.box(jaw, "Kontaktní plocha čelisti", (7,2.5,1.5), servo, (39,0,side*.75))
    dynamic_names = ["WS_Yaw","WS_Upper","WS_UpperParallel","WS_ElbowLevel","WS_Fore","WS_ForeParallel","WS_Hand","WS_Jaw_L","WS_Jaw_R","WS_Payload"]
    s.doc["extras"] = {
        "units": "metres", "hardware": "Waveshare Robot Arm for Pi (RPiShop WAV083)",
        "parked": parked,
        "controls": {n["name"]: i for i,n in enumerate(s.doc["nodes"]) if n["name"] in dynamic_names},
        "source": "https://www.waveshare.com/img/devkit/accBoard/Robot-Arm-for-Pi/Robot-Arm-for-Pi-size.jpg",
        "geometry": "Reference dimensions with estimated linkage pivots, jaw path and host mounting. No calibrated physical motion.",
    }


def make_optics(s):
    """Pouzdra a optické středy senzorů v robotovém rámci. Všechny délky jsou mm."""
    graphite = s.material("Pouzdro kamery", (39, 45, 48), .06)
    grey = s.material("Zadní kryt a závěs", (73, 83, 89), .12)
    black = s.material("Černý kroužek objektivu", (24, 31, 36))
    glass = s.material("Optické sklo", (61, 122, 139), .36, .23)
    lens_normal = quaternion((0, 1, 0), 90)  # původní osa válce je Z, optická osa je X
    for name, sign, y, z, diameter in (
        ("Tablet_front_optical", 1, TABLET_CENTER[1]+85.4, 0, 3.1),
        ("Tablet_rear_optical", -1, TABLET_CENTER[1]+69, 122, 13)
    ):
        surface = TABLET_CENTER[0] + sign * 7.52 / 2
        protrusion = .85 if sign > 0 else 1.6
        s.disc(1, "Vestavěná přední kamera" if sign>0 else "Vestavěná zadní kamera",
               diameter, protrusion, black, (surface+sign*protrusion/2, y, z), lens_normal, 24)
        optical = (surface+sign*(protrusion+.15), y, z)
        s.disc(1, "Sklo tabletu", diameter*.58, .3, glass, optical, lens_normal, 20)
        node = s.node(1, name, optical)
        s.doc["nodes"][node]["extras"] = {"forward":[sign,0,0],"estimated_lens_position":True}
    inclination = 20
    angle = math.radians(inclination)
    forward = (math.cos(angle),-math.sin(angle),0)
    up = (math.sin(angle),math.cos(angle),0)
    centres = []
    for suffix, lateral in (("L",-55), ("R",55)):
        origin=(-51,DECK_TOP+296,lateral)
        frame = s.node(1, "Yahboom USB • "+suffix, origin, quaternion((0,0,1),-inclination))
        # Silueta kamery v místním Z−Y. Zaoblené boky a prostřední předsazený objektiv.
        outline=[]
        for cx, start in ((32,-90),(-32,90)):
            for i in range(13):
                a=math.radians(start+i*180/12)
                outline.append((cx+14.5*math.cos(a),14.5*math.sin(a)))
        s.polygon(frame,"Tělo kamery USB",outline,22,graphite,(11,14.5,0),lens_normal)
        s.disc(frame,"Prstenec objektivu",16,4.0,black,(24,14.5,0),lens_normal,24)
        s.disc(frame,"Čočka Yahboom",9.5,.3,glass,(25.85,14.5,0),lens_normal,28)
        s.disc(frame,"Mikrofon",2.0,.3,black,(22.1,14.5,-14),lens_normal,12)
        s.box(frame,"Sklopený původní klip • odhad", (9,5.4,25), grey,(7,-2.2,0))
        for z in (-31,31):
            s.box(frame,"Pásek zadního sedla", (23.4,1.3,3),black,(11,29.35,z))
            s.box(frame,"Pásek čela kamery",(1.25,30,3),black,(22.55,14.5,z))
        centre=tuple(origin[i]+26*forward[i]+14.5*up[i] for i in range(3))
        centres.append([round(x,5) for x in centre])
        node=s.node(1,"Stereo_"+suffix+"_optical",centre)
        s.doc["nodes"][node]["extras"]={"forward":forward,"up":up,"estimated_lens_position":True}
        corners=[[origin[i]+d*forward[i]+h*up[i]+(z if i==2 else 0) for i in range(3)]
                 for d in (0,26) for h in (-5,29) for z in (-46.5,46.5)]
        axes=list(zip(*corners))
        s.obstacles.append({"label":"kamera Yahboom","bounds_mm":[list(map(min,axes)),list(map(max,axes))]})
    s.doc["extras"]["stereo"] = {"left_mm":centres[0],"right_mm":centres[1],
        "forward":forward,"up":up,"baseline_mm":110,"pitch_down_deg":inclination}
    s.doc["extras"]["tablet"]={"size_mm":[7.52,181.85,280],"center_mm":TABLET_CENTER,
        "front":[1,0,0],"rear":[-1,0,0],"source":"https://www.mi.com/global/product/redmi-pad-pro/specs/"}
    half=[7.52/2+2,181.85/2,140]
    s.obstacles.append({"label":"tablet","bounds_mm":[[v-r for v,r in zip(TABLET_CENTER,half)],
                                                     [v+r for v,r in zip(TABLET_CENTER,half)]]})


def make_lidar(s):
    steel=s.material("Původní podpěry víčka • poloha odhad", (95,101,109),.23)
    original=[]
    # Počet doložen majitelem. Poloha, rozteč i průměr jsou ilustrační.
    for degrees in (0,120,240):
        a=math.radians(degrees)
        x,z=44*math.cos(a),44*math.sin(a)
        s.disc(0,"Původní sloupek víčka • schematicky",3,7.6,steel,
               (x,91,z),quaternion((1,0,0),-90),12)
        original.append({"x":round(x,4),"z":round(z,4),"radius":1.5})
    s.disc(1,"Lepená plocha • návrhová vrstva",66,.5,s.material("Lepidlo",(204,174,125)),
           (0,98.25,0),quaternion((1,0,0),-90),60)
    s.doc["extras"]["lidar"]={"origin_mm":[0,91,0],"window_radius_mm":42,"window_y_mm":[87.5,94.5],
        "cap_top_mm":98,"adhesive_y_mm":[98,98.5],"deck_bottom_mm":DECK_BOTTOM,"deck_top_mm":DECK_TOP,
        "stock_posts_mm":original,"stock_posts_layout_estimated":True}


def make_mounts(s):
    deck=s.material("PETG • nosná deska", (175,62,52),0,.61)
    mast=s.material("PETG • držák tabletu", (191,202,198),0,.66)
    rail=s.material("PETG • stereolišta a příchytky",(82,104,111),0,.68)
    s.stl("talir.stl","Nosný talíř PETG",deck,((1,0,0,0),(0,0,-1,DECK_TOP),(0,1,0,0)))
    for file,label,material,matrix in [
        ("stojan.stl","Stojan tabletu",mast,((0,0,1,-86),(0,1,0,DECK_TOP),(-1,0,0,0))),
        ("pojistka-tabletu.stl","Horní pojistka tabletu",mast,((0,0,1,-70),(0,1,0,DECK_TOP+246),(-1,0,0,0))),
        ("stereo-lista.stl","Společná stereolišta",rail,((0,0,1,-61),(0,1,0,DECK_TOP+287),(-1,0,0,0)))
    ]:
        bounds=s.stl(file,label,material,matrix)
        s.obstacles.append({"label":label,"bounds_mm":bounds})
    for x,z,sign in ((44,-37,1),(44,33,1),(138,-37,-1),(138,69,-1)):
        bounds=s.stl("prichytka-ramene.stl","Příchytka tovární základny",rail,
                     ((sign,0,0,x),(0,0,-1,DECK_TOP+14.4),(0,sign,0,z)))
        s.obstacles.append({"label":"příchytka základny","bounds_mm":bounds})
    steel=s.material("Spojovací materiál M4",(174,183,187),.58,.35)
    vertical=quaternion((1,0,0),-90)
    for x,z in ((73,-58.6),(77,99)):
        s.disc(1,"Koncový doraz základny Ø8",8,10,steel,(x,DECK_TOP+5,z),vertical,18)
        s.obstacles.append({"label":"doraz základny","bounds_mm":[[x-4,DECK_TOP,z-4],[x+4,DECK_TOP+10,z+4]]})
    for x,z in ((44,-37),(44,33),(138,-37),(138,69),(-79,-32),(-79,32),(-48,-32),(-48,32)):
        y=DECK_TOP + (14.4 if x>0 else 8)
        s.disc(1,"Podložka M4",9,.8,steel,(x,y+.4,z),vertical,16)
        s.disc(1,"Hlava M4",7,3,steel,(x,y+2.3,z),vertical,12)
    for y,z,x in ((DECK_TOP+252,-32,-86),(DECK_TOP+252,32,-86),(DECK_TOP+287,-13,-86),(DECK_TOP+287,13,-86)):
        s.disc(1,"Zadní hlava šroubu příčníku",7,3,steel,(x-1.5,y,z),quaternion((0,1,0),90),12)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path, nargs="?", default=SRC / "Emil-V3.1.glb")
    args = parser.parse_args()
    scene = Scene()
    scene.import_emil(*read_reference(args.reference))
    make_arm(scene)
    make_optics(scene)
    make_lidar(scene)
    make_mounts(scene)
    scene.doc["extras"]["static_obstacles"]=scene.obstacles
    scene.write(args.output)


if __name__ == "__main__":
    main()
