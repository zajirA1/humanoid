# smyčka QP ve statické poloze f: plán držen, regulátor běží; sleduje se, zda změřené síly dojdou k požadovaným
import sys,json,numpy as np,mujoco
KD='/home/claude/humanoid/kontrola'; sys.path.insert(0,KD)
import prepocet as P, vyvazovani as V, qp_sily as Q
fi=int(sys.argv[1]); Z=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
A=json.load(open('/tmp/plan/_A.json')); F=A['frames']; G,_=P.nacti_geometrii({})
m=mujoco.MjModel.from_xml_string(P.mj_xml(A['P'],A['E'],A['links'],G=G)); d=mujoco.MjData(m)
kp=np.array([m.actuator_gainprm[j,0] for j in range(22)]); f=F[fi]
R0,t0=P.rt2T(f['rt']); qu=np.zeros(4); mujoco.mju_mat2Quat(qu,np.ascontiguousarray(R0).reshape(-1))
d.qpos[:3]=t0*1e-3+[0,0,0.002]; d.qpos[3:7]=qu; d.qpos[7:29]=np.radians(f['q']); q0=np.radians(f['q'])+np.array(f['ff'])/kp; q0[[11,21]]=np.radians(f['q'])[[11,21]]
d.ctrl[:]=q0; mujoco.mj_forward(m,d)
cile,nez=V.cile_sil(F,P.M,A['P'],A['E'],A['links'],P.fk)
cil=dict(cile[fi]); 
for k,v in Z.pop('posun',{}).items(): cil[k]=cil[k]+v
c=Q.SilyQP(m,[cil]*len(F),[nez[fi]]*len(F),**Z)
for _ in range(1000): mujoco.mj_step(m,d)
for st in range(4000):
    if st%20==0: dq=c.krok(d,fi,R0,0.02,f['com'])
    d.ctrl[:]=q0+dq; mujoco.mj_step(m,d)
    if st%800==0: print(st/1000,'s',{k:round(sum((fw[2] for _,fw in v),0.0),1) for k,v in c.zmer(d,list(cil)).items()},'|dq|',round(float(np.degrees(np.abs(dq).max())),2))
print('cíl',{k:round(v,1) for k,v in cil.items()})
