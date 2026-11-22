import sys,json,subprocess,os; sys.path.insert(0,'/home/claude/humanoid/kontrola'); sys.argv=['x']
import numpy as np, prepocet as P, mujoco
A=json.load(open([f for f in sorted(__import__('glob').glob('/tmp/plan/va*.json'),key=os.path.getmtime)][-1])); F=A['frames']
G,_=P.nacti_geometrii({})
m=mujoco.MjModel.from_xml_string(P.mj_xml(A['P'],A['E'],A['links'],0.5,210.0,G=G)); d=mujoco.MjData(m)
for i in (0,60,300):
    R,t=P.rt2T(F[i]['rt']); qu=np.zeros(4); mujoco.mju_mat2Quat(qu,np.ascontiguousarray(R).reshape(-1))
    d.qpos[:3]=t*1e-3; d.qpos[3:7]=qu; d.qpos[7:29]=np.radians(F[i]['q']); mujoco.mj_forward(m,d)
    print(i,'plán com',np.round(F[i]['com'],1),'mujoco com',np.round(d.subtree_com[1]*1e3,1), 'body1',mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,1))
