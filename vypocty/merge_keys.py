import sys; sys.path.insert(0,'/home/claude/sim')
from fullpass import *
src,sup=timeline(); n=len(src)
vk={}
for tag in ('A3','B3'):
    K_=pickle.load(open(f'key_{tag}.pkl','rb')); vk.update(K_['v'])
keys=sorted(vk); print(len(keys),keys[0],keys[-1],n)
V=np.zeros((n,6))
for f in keys: V[f]=vk[f]
# start from the neutral stance: fade in over the first 4 keyframes
for f in keys:
    if f<=12: V[f]*=smooth(max(0,(f-3)/12.0)) if f>3 else 0
np.save('V0.npy',V)
