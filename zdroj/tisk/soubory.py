"""Deterministické 3MF a binární STL v milimetrech. Kontrolujeme i znovu načtené STL."""
from pathlib import Path
from xml.sax.saxutils import quoteattr
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import struct
import numpy as np


MODEL = '3D/3dmodel.model'
TYPES = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
RELS = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="r0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
STL = np.dtype([('n','<f4',3),('p','<f4',(3,3)),('a','<u2')])


def stl(path, v, f):
    p = v[f]
    normal = np.cross(p[:, 1]-p[:, 0],p[:, 2]-p[:, 0])
    buf = np.zeros(len(f),dtype=STL)
    buf['n'] = normal/np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-30)
    buf['p'] = p
    Path(path).write_bytes(b'Emil H22 | millimeter'.ljust(80,b' ') + struct.pack('<I',len(f)) + buf.tobytes())


def zapis3mf(path, name, v, f):
    vertices=''.join('<vertex x="%.17g" y="%.17g" z="%.17g"/>'%tuple(pt) for pt in v)
    triangles=''.join('<triangle v1="%d" v2="%d" v3="%d"/>'%tuple(t) for t in f)
    model=('<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter">'
           '<resources><object type="model" id="1" name='+quoteattr(name)+'><mesh><vertices>'+vertices+
           '</vertices><triangles>'+triangles+'</triangles></mesh></object></resources>'
           '<build><item objectid="1"/></build></model>')
    with ZipFile(path,'w') as z:
        for key,s in [('[Content_Types].xml',TYPES),('_rels/.rels',RELS),(MODEL,model)]:
            info=ZipInfo(key,(1980,1,1,0,0,0))
            z.writestr(info,s.encode(),compress_type=ZIP_DEFLATED,compresslevel=6)
