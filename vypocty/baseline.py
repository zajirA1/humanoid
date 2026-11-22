import sys; sys.path.insert(0,'/home/claude/sim')
from fullpass import *
import time
# structural adjacent contacts: evaluate ADJ pair distances at home pose
st=REFS[0].st.copy(); st.q[:]=0; st.R=np.eye(3); st.t=np.array([0,0,0.]); st.update(); K.place(st)
import fcl
struct=[]
for ka,kb in K.ADJ:
    res=fcl.DistanceResult(); d=fcl.distance(K.G[ka].obj,K.G[kb].obj,K._req,res); 
    if d<0.5: struct.append((ka,kb))
    print(ka,kb,round(d,3))
pickle.dump(struct,open('adj_struct.pkl','wb'))
