"""Per-link geometry (R12 assembly incl. covers and climbing sleeves) in link rest coordinates."""
import json, numpy as np
from emil import rt2T
_g=json.load(open('/home/claude/sim/geom.json'))
ITEMS=[]
for n,it in enumerate(_g['items']):
    v=np.array(_g['meshes'][it['key']][0],float).reshape(-1,3); f=np.array(_g['meshes'][it['key']][1],int).reshape(-1,3)
    if it['t'] is not None:
        R,t=rt2T(it['t']); v=v@R.T+t
    ITEMS.append(dict(key=it['key'],link=it['link'],kind=it['kind'],v=v,f=f,idx=n))
# palm pads: sphere r=12 at (+-146,-12,205) on links 10/20
PAD={10:np.array([146,-12,205.]),20:np.array([-146,-12,205.])}; PAD_R=12.0
