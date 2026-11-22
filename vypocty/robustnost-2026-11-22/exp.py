"""Pokusy s přechody: python3 exp.py <název> <h1,h2,...> [volby json]"""
import sys,json,subprocess,os,math; name=sys.argv[1]; HS=[float(x) for x in sys.argv[2].split(',')]; OPT=json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
KD='/home/claude/humanoid/kontrola'; sys.path.insert(0,KD); sys.argv=['x']
import numpy as np, prepocet as P
from scipy.ndimage import gaussian_filter1d
G,_=P.nacti_geometrii({}); M=json.load(open(KD+'/data/model.json')); n=len(M['q'])
pid=str(os.getpid()); q=[list(x) for x in M['q']]; rt=[list(x) for x in M['rt']]; contacts=list(M['contacts']); sup=list(M['support'])
# 1) posun trupu ve fázi 3 (z předchozího pokusu)
if OPT.get('f3'):
    off=np.array(json.load(open('/tmp/plan/off.json'))); exec(open('/tmp/plan/podmnozina.py').read().split("if __name__=='__main__':")[0]); keep=okna(['f3'])
    idx=[i for i in range(n) if keep[i] and np.abs(off[i]).max()>1e-6]
    json.dump([{'i':i,'off':(off[i]*OPT['f3']).tolist()} for i in idx],open(f'/tmp/plan/x{pid}.rq','w'))
    subprocess.run(['node','/tmp/plan/posun.js',KD+'/data/model.json',f'/tmp/plan/x{pid}.rq',f'/tmp/plan/x{pid}.rs'],check=True)
    for r in json.load(open(f'/tmp/plan/x{pid}.rs')): q[r['i']]=r['q']; rt[r['i']]=r['rt']
# 2) zpomalení úseku [a,b] faktorem k (vložení mezisnímků, opory podle nejbližšího snímku)
if OPT.get('zpomal'):
    a,b,k=OPT['zpomal']; a=int(a*6); b=int(b*6)
    def lerp_rt(r0,r1,u):
        R0=np.array(r0[:9]).reshape(3,3); R1=np.array(r1[:9]).reshape(3,3)
        from scipy.spatial.transform import Rotation as Ro, Slerp
        s=Slerp([0,1],Ro.from_matrix([R0,R1]))(u).as_matrix().reshape(-1); t=(1-u)*np.array(r0[9:])+u*np.array(r1[9:]); return list(s)+list(t)
    nq,nrt,nc,ns=[],[],[],[]
    for i in range(n):
        if a<=i<b:
            m=int(round(k))
            for s_ in range(m):
                u=s_/m; nq.append(list((1-u)*np.array(q[i])+u*np.array(q[i+1]))); nrt.append(lerp_rt(rt[i],rt[i+1],u))
                j=i if u<0.5 else i+1; nc.append(contacts[j]); ns.append(sup[j])
        else: nq.append(q[i]); nrt.append(rt[i]); nc.append(contacts[i]); ns.append(sup[i])
    q,rt,contacts,sup=nq,nrt,nc,ns
if 'vyska' in OPT:
    # nejdřív případné úpravy výše (f3) zapsat do modelu, pak přizpůsobit výšce schodu
    Mv=dict(M); Mv['q']=q; Mv['rt']=rt; json.dump(Mv,open(f'/tmp/plan/mv{pid}.json','w'),separators=(',',':'))
    subprocess.run(['node','/tmp/plan/vyska.js',f'/tmp/plan/mv{pid}.json',str(OPT['vyska']),f'/tmp/plan/v{pid}.json'],check=True)
    V=json.load(open(f'/tmp/plan/v{pid}.json')); q=V['q']; rt=V['rt']; print('max posun opory při přizpůsobení výšce',round(max(V['drift']),2),'mm',flush=True)
n=len(q); M2=dict(M); M2['q']=q; M2['rt']=rt; M2['contacts']=contacts; M2['support']=sup; M2['ex']=[0]*n
json.dump(M2,open(f'/tmp/plan/m{pid}.json','w'),separators=(',',':')); json.dump({'upravy':{}},open(f'/tmp/plan/u{pid}.json','w'))
json.dump(dict(q=q,rt=rt,drift=[0]*n,shift=[0]*n),open(f'/tmp/plan/f{pid}.json','w'))
subprocess.run(['node',KD+'/prizpusob.js',f'/tmp/plan/m{pid}.json',f'/tmp/plan/u{pid}.json',f'/tmp/plan/a{pid}.json',f'/tmp/plan/f{pid}.json'],check=True,capture_output=True)
A=json.load(open(f'/tmp/plan/a{pid}.json')); F=A['frames']
ff=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); ff[:,[11,21]]=0
# 3) plynulost předkorekce: sigma (snímky) – globálně, nebo jen kolem změn opor
sg=OPT.get('sigma',1.5); ff=gaussian_filter1d(ff,sg,axis=0,mode='nearest')
if OPT.get('nabeh'):
    # při změně množiny opor rozložit změnu předkorekce lineárně na OPT['nabeh'] snímků před změnou
    L=OPT['nabeh']; raw=np.array([f['ff'] if f['ff'] else [0]*22 for f in F]); raw[:,[11,21]]=0; out=raw.copy()
    ch=[i for i in range(1,n) if set(sup[i])!=set(sup[i-1])]
    for c in ch:
        lo=max(0,c-L)
        for i in range(lo,c): u=(i-lo)/(c-lo); out[i]=(1-u)*raw[lo]+u*raw[c]
    ff=gaussian_filter1d(out,sg,axis=0,mode='nearest')
res=[]
for sh in HS:
    r,_=P.simuluj(F,A['P'],A['E'],A['links'],G,ff,step_h=sh); res.append(f'{sh:.0f}:{"OK" if r["uspech"] else "PÁD@"+str(round(r["pad_s"] or -1,1))}')
print(f'{name:28s} statika {max(f["s50"] for f in F if f["s50"]):.3f} délka {n/6:.0f} s  '+' '.join(res),flush=True)
for f in ('rq','rs'): 
    try: os.remove(f'/tmp/plan/x{pid}.{f}')
    except: pass
if OPT.get('trace'):
    import mujoco
    t0,t1,sh=OPT['trace']; MM=1e-3
    m=mujoco.MjModel.from_xml_string(P.mj_xml(A['P'],A['E'],A['links'],0.5,sh,G=G)); d=mujoco.MjData(m)
    Q=np.radians(np.array([f['q'] for f in F])); T=(n-1)/6; kpv=np.array([m.actuator_gainprm[j,0] for j in range(22)]); Q=Q+ff/kpv
    R0,tt0=P.rt2T(F[0]['rt']); qu=np.zeros(4); mujoco.mju_mat2Quat(qu,np.ascontiguousarray(R0).reshape(-1))
    d.qpos[:3]=(tt0+np.array([0,0,0.3]))*MM; d.qpos[3:7]=qu; d.qpos[7:29]=np.radians(F[0]['q']); d.ctrl[:]=Q[0]; mujoco.mj_forward(m,d)
    gn={mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,g):g for g in ['sole7','sole17','sleeve5','sleeve15','palm10','palm20']}
    f6=np.zeros(6)
    for k in range(int((1+t1)/0.001)):
        t=k*0.001-1; u=min(max(t,0),T)*6; i=min(int(u),n-2); a_=u-i; d.ctrl[:]=Q[i]*(1-a_)+Q[i+1]*a_; mujoco.mj_step(m,d)
        if t>=t0 and k%250==0:
            fz={}
            for c in range(d.ncon):
                con=d.contact[c]
                for g in (con.geom1,con.geom2):
                    if g in gn: mujoco.mj_contactForce(m,d,c,f6); fz[gn[g]]=fz.get(gn[g],0)+abs(f6[0])
            fi=min(n-1,int(round(t*6))); err=np.linalg.norm(d.qpos[:3]/MM-P.rt2T(F[fi]['rt'])[1])
            # natočení trupu oproti plánu
            Rm=np.zeros(9); mujoco.mju_quat2Mat(Rm,d.qpos[3:7]); Rm=Rm.reshape(3,3); Rp=P.rt2T(F[fi]['rt'])[0]; ang=math.degrees(math.acos(max(-1,min(1,(np.trace(Rm@Rp.T)-1)/2))))
            sat=[P.JN[j][:22] for j in range(22) if j not in(11,21) and abs(d.actuator_force[j])>=P.LIM[j]*0.999]
            print(f'{t:5.2f}s f{fi} {",".join(s.replace("left","L").replace("right","P") for s in sup[fi]):28s} odch {err:5.1f} mm nákl {ang:4.1f}° síly { {k_:round(v,1) for k_,v in fz.items()} } mez {sat[:2]}',flush=True)
