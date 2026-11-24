"""Příprava uzavřené sítě pro FDM. Úpravy zachovávají tvar a vnitřní dutiny."""
from collections import Counter

import numpy as np


def objem(v, f):
    p = v[f] - v.mean(axis=0)
    return float(np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2])).sum()/6)


def rozmer(v):
    return np.ptp(v, axis=0).round(4).tolist()


def okraje(f):
    edges = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    edges, counts = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    return edges[counts != 2], counts[counts != 2]


def priprav(v, f):
    v, inverse = np.unique(np.round(v, 8), axis=0, return_inverse=True)
    f = inverse[f]
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 2] != f[:, 0])]
    p = v[f]
    deg = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1) <= 1e-11
    flat = list(f[deg])
    faces = list(map(tuple, f[~deg].tolist()))
    for tri in flat:
        ids = tri.tolist()
        i = max(range(3), key=lambda j: np.linalg.norm(v[ids[j]]-v[ids[(j+1)%3]]))
        a, b, mid = ids[i], ids[(i+1)%3], ids[(i+2)%3]
        for j, t in enumerate(faces):
            if a not in t or b not in t:
                continue
            k = t.index(b)
            if t[(k+1)%3] == a:
                third = t[(k+2)%3]
                faces[j] = (b, mid, third)
                faces.append((mid, a, third))
                break
    f = np.asarray(faces, dtype=int)
    # Zredukujeme izolované nulové vrcholy z původní triangulace.
    used, inv = np.unique(f, return_inverse=True)
    v, f = v[used], inv.reshape(-1, 3)
    volume = objem(v, f)
    if volume < 0:
        f = f[:, [0, 2, 1]]
    return v, f


def orientace(v, f, structural=False):
    """Bodovaná volba mezi podporujícími rovinami. Bez změny tvaru a měřítka."""
    tri = v[f]
    normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    areas = np.linalg.norm(normals, axis=1)/2
    normals = normals/np.maximum(2*areas[:, None], 1e-30)
    direction_area = Counter()
    for n, area in zip(normals.round(4), areas):
        direction_area[tuple(n)] += float(area)
    candidates = set(map(tuple, np.vstack([np.eye(3), -np.eye(3)])))
    candidates.update(n for n, area in direction_area.most_common(40) if area > 0.2)
    best = None
    max_span = np.max(np.ptp(v, axis=0))
    total = areas.sum()
    principal = np.linalg.eigh(np.cov(v.T))[1][:, -1] if structural else np.zeros(3)
    for d in sorted(candidates):
        n = np.asarray(d)
        n = n/np.linalg.norm(n)
        up = -n
        z = v@up
        zs = z[f]
        flat = np.max(zs-z.min(), axis=1) <= 0.024
        contact = float(areas[flat].sum())
        if contact < 0.05:
            continue
        ref = np.eye(3)[np.argmin(np.abs(up))]
        x = np.cross(ref, up)
        x /= np.linalg.norm(x)
        y = np.cross(up, x)
        m = np.asarray([x, y, up])
        placed = v@m.T
        dims = np.ptp(placed, axis=0)
        if max(dims) > 255.8:
            continue
        overhang = float(areas[((normals@up)<-0.7071)&(~flat)].sum())
        # Odměna za reálný kontakt a nízkou stavbu. U dlouhých rámů favorizujeme
        # dlouhou osu v rovině XY, aby se zatížení nepřenášelo jen přes spoje vrstev.
        score = contact/total - .27*overhang/total - .12*dims[2]/max_span
        if structural:
            score -= .12*abs(float(principal@up))
        if best is None or score > best[0]:
            offset = -placed.min(axis=0)
            best = (score, placed+offset, m, offset, contact, overhang)
    if best is None:
        raise ValueError("Součást nemá nalezenou vyhovující plochu pro X1C")
    return best[1:]


def sjednot(geometrie):
    """Přesný booleovský součet tištěných úseků jedné čelisti/nosníku (pokud se dotýkají)."""
    from tempfile import TemporaryDirectory
    from pathlib import Path
    import subprocess
    from soubory import stl, STL
    with TemporaryDirectory() as td:
        directory=Path(td)
        for i,(v,f) in enumerate(geometrie):
            stl(directory/f'{i}.stl',v,f)
        lines=[f'import("{i}.stl");' for i in range(len(geometrie))]
        (directory/'join.scad').write_text('union(){\n'+'\n'.join(lines)+'\n}')
        cmd=['openscad','--export-format','binstl','-o','union.stl','join.scad']
        result=subprocess.run(cmd,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if result.returncode or not (directory/'union.stl').exists():
            raise ValueError('Nedefinovaný objem spojovaných dílů')
        pts=np.frombuffer((directory/'union.stl').read_bytes(),offset=84,dtype=STL)['p'].astype(float).reshape(-1,3)
        return priprav(pts,np.arange(len(pts)).reshape(-1,3))


def kontrola(v, f):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    un, counts = np.unique(e,axis=0,return_counts=True)
    if np.any(counts!=1) or set(map(tuple,un)) != set(map(tuple,un[:,::-1])):
        raise ValueError('Neuzavřená nebo nekonzistentně orientovaná síť')
    p=v[f];areas=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
    if np.min(areas)<=1e-13:raise ValueError('Trojúhelník s nulovou plochou')
    _,labels=connected_components(coo_matrix((np.ones(len(e)),e.T),shape=(len(v),len(v))),directed=False)
    volumes=[objem(v,f[labels[f[:,0]]==k]) for k in np.unique(labels[f[:,0]])]
    positives=sum(x>1e-7 for x in volumes)
    if positives!=1:raise ValueError(f'Počet oddělených kladných těles: {positives}')
    return {'solid_shells':positives, 'internal_cavities':sum(x < -1e-8 for x in volumes),
            'manifold':True,'oriented':True,'vertices':len(v),'triangles':len(f)}


def regularizuj(v, f):
    """Přesný rozklad hranic tělesa: lokální překryvy nesmí přejít do plátkování."""
    from igl.copyleft import cgal
    v=v.astype(np.float32).astype(float)
    _,_,pairs,_,_=cgal.remesh_self_intersections(v,f,detect_only=True)
    count=len(pairs)
    if count:
        before=np.array([v.min(0),v.max(0)])
        v,f,_=cgal.mesh_boolean(v,f,np.empty((0,3)),np.empty((0,3),dtype=int),'union')
        # Obě výměnné geometrie dostanou stejné vrcholy v přesnosti STL. Zachováme
        # i správný směr uzavřených záporných skořepin (otvory a vnitřní dutiny).
        v,f=priprav(v.astype(np.float32).astype(float),f)
        v=v.astype(np.float32).astype(float)
        if np.max(np.abs(np.array([v.min(0),v.max(0)])-before))>.01:
            raise ValueError('Regularizace změnila obálku tiskového dílu')
        _,_,remaining,_,_=cgal.remesh_self_intersections(v,f,detect_only=True)
        if len(remaining):
            raise ValueError(f'Zbývající průniky v tiskové síti: {len(remaining)}')
    return v,f,count
