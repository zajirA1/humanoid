import sys,json,os,glob; sys.path.insert(0,'/home/claude/humanoid/kontrola'); sys.argv=['x']
import numpy as np, prepocet as P, mujoco
A=json.load(open(sorted(glob.glob('/tmp/plan/va*.json'),key=os.path.getmtime)[-1])); F=A['frames']
G,_=P.nacti_geometrii({})
m=mujoco.MjModel.from_xml_string(P.mj_xml(A['P'],A['E'],A['links'],0.5,210.0,G=G))
def run(target):
    d=mujoco.MjData(m); i=0; R,t=P.rt2T(F[i]['rt']); qu=np.zeros(4); mujoco.mju_mat2Quat(qu,np.ascontiguousarray(R).reshape(-1))
    d.qpos[:3]=t*1e-3+np.array([0,0,0.0003]); d.qpos[3:7]=qu; d.qpos[7:29]=np.radians(F[i]['q']); q0=np.radians(F[i]['q']); d.ctrl[:]=q0; mujoco.mj_forward(m,d)
    for k in range(1500): mujoco.mj_step(m,d)
    c0=d.subtree_com[1].copy()
    nv=m.nv; Jc=np.zeros((3,nv)); mujoco.mj_jacSubtreeCom(m,d,Jc,1)
    rows=[Jc[:2]]; rhs=[np.array(target)*1e-3]
    for b,pl in (('b7',(57,-10,0)),('b17',(-57,-10,0))):
        bid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,b); p=d.xpos[bid]+d.xmat[bid].reshape(3,3)@(np.array(pl)*1e-3); Jp=np.zeros((3,nv)); Jw=np.zeros((3,nv)); mujoco.mj_jac(m,d,Jp,Jw,p,bid); rows.append(1000*Jp); rhs.append(np.zeros(3)); rows.append(1000*Jw); rhs.append(np.zeros(3))
    A_=np.vstack(rows); b=np.concatenate(rhs); v=np.linalg.solve(A_.T@A_+np.diag([1e-9]*6+[1e-4]*(nv-6)),A_.T@b)
    d.ctrl[:]=q0+v[6:]
    for k in range(2000): mujoco.mj_step(m,d)
    print('cíl',target,'skutečný posun těžiště mm',np.round((d.subtree_com[1]-c0)[:2]*1e3,2),'max dq°',round(float(np.degrees(np.abs(v[6:]).max())),2))
run([0,5]); run([5,0])
