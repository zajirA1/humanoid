# zkouška znaménka: drží polohu f, po 2 s přidá Δq = -Jᵀ Δf / kp pro Δf = +5 N svisle na pravou dlaň; změří změnu síly
import sys,json,subprocess,numpy as np,mujoco
KD='/home/claude/humanoid/kontrola'; sys.path.insert(0,KD)
import prepocet as P, vyvazovani as V, qp_sily as Q
fi=int(sys.argv[1]); k=sys.argv[2] if len(sys.argv)>2 else 'rightPalm'
A=json.load(open('/tmp/plan/_A.json')); F=A['frames']; G,_=P.nacti_geometrii({})
m=mujoco.MjModel.from_xml_string(P.mj_xml(A['P'],A['E'],A['links'],G=G)); d=mujoco.MjData(m)
kp=np.array([m.actuator_gainprm[j,0] for j in range(22)]); f=F[fi]
R0,t0=P.rt2T(f['rt']); qu=np.zeros(4); mujoco.mju_mat2Quat(qu,np.ascontiguousarray(R0).reshape(-1))
d.qpos[:3]=t0*1e-3+[0,0,0.002]; d.qpos[3:7]=qu; d.qpos[7:29]=np.radians(f['q']); q0=np.radians(f['q'])+np.array(f['ff'])/kp; q0[[11,21]]=np.radians(f['q'])[[11,21]]
d.ctrl[:]=q0; mujoco.mj_forward(m,d)
cile,nez=V.cile_sil(F,P.M,A['P'],A['E'],A['links'],P.fk); cile=cile[fi:fi+1]; nez=nez[fi:fi+1]
c=Q.SilyQP(m,[cile[0]],[nez[0]])
def sily():
    meas=c.zmer(d,list(cile[0])); return {kk:round(sum((fw[2] for _,fw in v),0.0),2) for kk,v in meas.items()}
for _ in range(2000): mujoco.mj_step(m,d)
print('před',sily())
bid=c.bid[k]; R=d.xmat[bid].reshape(3,3); ref=d.xpos[bid]+R@(np.array(V.OPORY[k][1])*1e-3)
Jp=np.zeros((3,m.nv)); mujoco.mj_jac(m,d,Jp,None,ref,bid); tau=-Jp.T@np.array([0,0,5.0])
d.ctrl[:]=q0+tau[6:]/kp
for _ in range(1500): mujoco.mj_step(m,d)
print('po  ',sily())
