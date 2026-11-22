"""Dynamické hledání: posun pravé dlaně (položení 43,5–77,2 s) a trupu ve fázi 6; simulace do 62 s."""
import sys,json,subprocess,math,os; args=sys.argv[1:]; sys.argv=['x']
KD='/home/claude/humanoid/kontrola'; sys.path.insert(0,KD)
import numpy as np, prepocet as P, mujoco
from scipy.ndimage import gaussian_filter1d
M=P.M; n=len(M['q']); NT=62*6; pid=str(os.getpid()); G,_=P.nacti_geometrii({})
RAMP=12
def vaha(i,a,b):
    if a<=i<=b: return 1.0
    if a-RAMP<=i<a: return 0.5-0.5*math.cos(math.pi*(i-(a-RAMP))/RAMP)
    if b<i<=b+RAMP: return 0.5-0.5*math.cos(math.pi*((b+RAMP)-i)/RAMP)
    return 0.0
def pohyb(pp, lp=(0,0), tor=(0,0), f3=0.0, dh=0.0, od=34.0, nabeh=2.0, NT=NT):
    off=np.array(json.load(open('/tmp/plan/off.json'))) if f3 else None
    reqs=[]
    for i in range(NT):
        sh={'10':[lp[0]*vaha(i,53,211),lp[1]*vaha(i,53,211),0],'20':[pp[0]*vaha(i,261,463),pp[1]*vaha(i,261,463),0]}
        o=[tor[0]*vaha(i,288,330),tor[1]*vaha(i,288,330),0]
        if f3 and 74<=i<=192: o=[o[0]+f3*off[i][0],o[1]+f3*off[i][1],0]
        lw=0.0 if i<od*6 else min(1.0,(i-od*6)/(nabeh*6))
        if dh and lw>0:
            # podíl opor na schodu → zvednutí pánve
            on=sum(1 for s_ in M['support'][i] if s_ in ('leftPalm','rightPalm','leftKnee','rightKnee') or (s_ in('leftFoot','rightFoot') and i>=700)); tot=max(1,len(M['support'][i]))
            o[2]+=dh*lw*on/tot
        reqs.append({'i':i,'shift':sh,'off':o,'plne':True,'lift':dh*lw})
    json.dump(reqs,open(f'/tmp/plan/d{pid}.rq','w')); subprocess.run(['node','/tmp/plan/posun2.js',KD+'/data/model.json',f'/tmp/plan/d{pid}.rq',f'/tmp/plan/d{pid}.rs'],check=True)
    return json.load(open(f'/tmp/plan/d{pid}.rs'))
def sim(F,ff,sh,t_end=61.0):
    MM=1e-3; m=mujoco.MjModel.from_xml_string(P.mj_xml(M['P'],[[0,0,0]]*22,M['LINKS'],0.5,sh,G=G)); d=mujoco.MjData(m)
    Q=np.radians(np.array([f['q'] for f in F])); kpv=np.array([m.actuator_gainprm[j,0] for j in range(22)]); Q=Q+ff/kpv; nn=len(F)
    R0,t0=P.rt2T(F[0]['rt']); qu=np.zeros(4); mujoco.mju_mat2Quat(qu,np.ascontiguousarray(R0).reshape(-1))
    d.qpos[:3]=(t0+np.array([0,0,0.3]))*MM; d.qpos[3:7]=qu; d.qpos[7:29]=np.radians(F[0]['q']); d.ctrl[:]=Q[0]; mujoco.mj_forward(m,d); worst=0
    for k in range(int((1+t_end)/0.001)):
        t=k*0.001-1; u=min(max(t,0),(nn-1)/6)*6; i=min(int(u),nn-2); a=u-i; d.ctrl[:]=Q[i]*(1-a)+Q[i+1]*a; mujoco.mj_step(m,d)
        if k%100==0 and t>=0:
            e=np.linalg.norm(d.qpos[:3]/MM-P.rt2T(F[min(nn-1,int(round(t*6)))]['rt'])[1])
            if e>60: return t,worst
            if t>=40: worst=max(worst,e)
    return None,worst
for spec in args:
    c=json.loads(spec); R=pohyb(tuple(c.get('pp',(0,0))),tuple(c.get('lp',(0,0))),tuple(c.get('tor',(0,0))),c.get('f3',0),c.get('dh',0),c.get('od',34.0),c.get('nabeh',2.0),int(c.get('tend',62)*6))
    F=[{'q':r['q'],'rt':r['rt']} for r in R]; ff=np.array([r['ff'] if r['ff'] else [0]*22 for r in R]); ff[:,[11,21]]=0; ff=gaussian_filter1d(ff,1.5,axis=0,mode='nearest')
    out=[]
    for sh in c.get('h',[210,218]):
        if c.get('plna'):
            r,_=P.simuluj(F,M['P'],[[0,0,0]]*22,M['LINKS'],G,ff,step_h=float(sh)); out.append(f'{sh}:'+('OK' if r['uspech'] else 'PÁD'+('@'+str(round(r['pad_s'],1)) if r['pad_s'] else ''))+f"(konec {r['odchylka_konec_mm']:.0f} mm, max {r['odchylka_max_mm']:.0f}, náklon {r['naklon_konec_deg']:.1f}°)"); continue
        pad,wst=sim(F,ff,float(sh),t_end=c.get('tend',62)-1); out.append(f'{sh}:'+('OK(max '+str(round(wst))+')' if pad is None else 'PÁD@'+str(round(pad,1))))
    print(json.dumps(c),'statika',round(max(r['s50'] or 9 for r in R),3),' '.join(out),flush=True)
