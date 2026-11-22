"""MuJoCo model of Emil R12/R13 for dynamic verification of the climb (position servos with torque limits)."""
import sys; sys.path.insert(0,'/home/claude/sim')
import numpy as np, mujoco, math
from emil import *
from geom import ITEMS
MM=1e-3
def link_box(l):
    v=np.vstack([it['v'] for it in ITEMS if it['link']==l]); return v.min(0),v.max(0)
def build_xml(mu=0.5,step_h=210.0,mass_scale=1.0,kp_scale=1.0,lim_scale=1.0,second_step=False):
    children={i:[] for i in range(23)}
    for j in range(22): children[PAR[j]].append(j)
    def inertial(l):
        m=LINKS[l,0]*mass_scale; c=LINKS[l,1:]*MM; lo,hi=link_box(l); d=(hi-lo)*MM*0.75
        I=m/12*np.array([d[1]**2+d[2]**2,d[0]**2+d[2]**2,d[0]**2+d[1]**2]); I=np.maximum(I,1e-7)
        return f'<inertial pos="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" mass="{m:.6f}" diaginertia="{I[0]:.3e} {I[1]:.3e} {I[2]:.3e}"/>'
    def geoms(l):
        g=''
        if l in (7,17):
            s=1 if l==7 else -1; cx=s*57.0
            # sole: plate + 4 corner spheres for well-conditioned contact
            g+=f'<geom name="sole{l}" type="box" pos="{cx*MM:.4f} {-10*MM:.4f} {4*MM:.4f}" size="{38.5*MM:.4f} {60*MM:.4f} {4*MM:.4f}" class="foot"/>'
        if l in (5,15):
            s=1 if l==5 else -1
            g+=f'<geom name="sleeve{l}" type="capsule" fromto="{s*54*MM:.4f} {-24*MM:.4f} {85*MM:.4f} {s*54*MM:.4f} {-24*MM:.4f} {122*MM:.4f}" size="{8*MM:.4f}" class="pad"/>'
        if l in (10,20):
            s=1 if l==10 else -1
            g+=f'<geom name="palm{l}" type="sphere" pos="{s*146*MM:.4f} {-12*MM:.4f} {205*MM:.4f}" size="{12*MM:.4f}" class="pad"/>'
        return g
    def body(j):
        s=f'<body name="b{j}" pos="0 0 0">{inertial(j)}<joint name="j{j}" type="hinge" pos="{P[j][0]*MM:.5f} {P[j][1]*MM:.5f} {P[j][2]*MM:.5f}" axis="{AX[j][0]:g} {AX[j][1]:g} {AX[j][2]:g}" damping="0.03" armature="0.004" frictionloss="0.01"/>{geoms(j)}'
        for c in children[j]: s+=body(c)
        return s+'</body>'
    kp={j:(45.0 if LIM[j]>1.2 else 28.0 if LIM[j]>0.5 else 3.0)*kp_scale for j in range(22)}
    act=''.join(f'<position name="a{j}" joint="j{j}" kp="{kp[j]}" kv="{0.02*kp[j]+0.05:.3f}" forcerange="{-LIM[j]*lim_scale:.4f} {LIM[j]*lim_scale:.4f}"/>' for j in range(22))
    step2=f'<geom name="step2" type="box" pos="0 {-0.42:.3f} {step_h*MM:.4f}" size="0.33 0.14 {step_h*MM:.4f}" class="env"/>' if second_step else ''
    xml=f'''<mujoco model="emil">
<compiler angle="degree" inertiafromgeom="false"/>
<option timestep="0.001" integrator="implicitfast" cone="elliptic" impratio="10" noslip_iterations="4"/>
<default>
 <geom condim="4" friction="{mu} 0.005 0.0001" solref="0.004 1" solimp="0.95 0.99 0.0005" contype="1" conaffinity="1"/>
 <default class="env"><geom contype="1" conaffinity="2" rgba=".7 .65 .6 1"/></default>
 <default class="foot"><geom contype="2" conaffinity="1" rgba=".2 .4 .4 1"/></default>
 <default class="pad"><geom contype="2" conaffinity="1" rgba=".8 .5 .2 1"/></default>
</default>
<worldbody>
 <geom name="floor" type="plane" size="2 2 .1" class="env"/>
 <geom name="step" type="box" pos="0 -0.14 {step_h*MM/2:.5f}" size="0.33 0.14 {step_h*MM/2:.5f}" class="env"/>{step2}
 <body name="b22" pos="0 0 0"><freejoint name="root"/>{inertial(22)}{''.join(body(c) for c in children[22])}</body>
</worldbody>
<actuator>{act}</actuator>
</mujoco>'''
    return xml
def set_pose(model,data,R,t,q):
    """root body frame coincides with rest world frame: world = R*x + t"""
    quat=np.zeros(4); mujoco.mju_mat2Quat(quat,np.ascontiguousarray(R).reshape(-1))
    data.qpos[:3]=np.asarray(t)*MM; data.qpos[3:7]=quat; data.qpos[7:29]=np.radians(q)
def simulate(states,hz=6,mu=0.5,step_h=210.0,mass_scale=1.0,kp_scale=1.0,lim_scale=1.0,y_offset=0.0,settle=1.0,tail=3.0,record_hz=6,tau_ff=None):
    """play a kinematic sequence (list of wbik.State) through position servos. returns dict of time series"""
    m=mujoco.MjModel.from_xml_string(build_xml(mu=mu,step_h=step_h,mass_scale=mass_scale,kp_scale=kp_scale,lim_scale=lim_scale)); d=mujoco.MjData(m)
    Q=np.radians(np.array([s.q for s in states])); n=len(states); T=(n-1)/hz
    if tau_ff is not None:      # torque feed-forward as a position offset: servo delivers the planned torque at the planned angle
        kpv=np.array([m.actuator_gainprm[j,0] for j in range(22)]); Q=Q+np.asarray(tau_ff)/kpv
    s0=states[0]; set_pose(m,d,s0.R,s0.t+np.array([0,y_offset,0.3]),s0.q); d.ctrl[:]=Q[0]; mujoco.mj_forward(m,d)
    dt=m.opt.timestep; rec=dict(t=[],root=[],quat=[],q=[],tau=[],taupk=[],sat=[],fz={})
    geoms={'leftFoot':'sole7','rightFoot':'sole17','leftKnee':'sleeve5','rightKnee':'sleeve15','leftPalm':'palm10','rightPalm':'palm20'}
    gid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,v) for k,v in geoms.items()}
    for k in gid: rec['fz'][k]=[]
    lim=LIM*lim_scale; nsteps=int(round((settle+T+tail)/dt)); every=int(round(1/(record_hz*dt))); pk=np.zeros(22); satc=np.zeros(22); f6=np.zeros(6)
    for k in range(nsteps):
        t=k*dt-settle; u=min(max(t,0),T)*hz; i=min(int(u),n-2); a=u-i
        d.ctrl[:]=Q[i]*(1-a)+Q[i+1]*a
        mujoco.mj_step(m,d)
        af=np.abs(d.actuator_force); pk=np.maximum(pk,af); satc+=(af>=lim*0.999)
        if (k+1)%every==0:
            rec['t'].append(t); rec['root'].append(d.qpos[:3]/MM); rec['quat'].append(d.qpos[3:7].copy()); rec['q'].append(np.degrees(d.qpos[7:29])); rec['tau'].append(d.actuator_force.copy()); rec['taupk'].append(pk.copy()); rec['sat'].append(satc/every); pk=np.zeros(22); satc=np.zeros(22)
            fz={k_:0.0 for k_ in gid}
            for c in range(d.ncon):
                con=d.contact[c]
                for k_,g in gid.items():
                    if con.geom1==g or con.geom2==g:
                        mujoco.mj_contactForce(m,d,c,f6); fz[k_]+=abs(f6[0])
            for k_ in gid: rec['fz'][k_].append(fz[k_])
        if not np.all(np.isfinite(d.qpos)): rec['diverged']=t; break
    for k_ in ('t','root','quat','q','tau','taupk','sat'): rec[k_]=np.array(rec[k_])
    for k_ in gid: rec['fz'][k_]=np.array(rec['fz'][k_])
    rec['T']=T; rec['settle']=settle; rec['lim']=lim
    return rec
def sim_states(rec):
    """convert recorded simulation samples back to wbik.State objects (for clearance checks)"""
    from wbik import State
    out=[]
    for r,qt,q in zip(rec['root'],rec['quat'],rec['q']):
        R=np.zeros(9); mujoco.mju_quat2Mat(R,qt); out.append(State(R.reshape(3,3),r,q))
    return out
def judge(rec,states,hz=6):
    """compare simulated root motion with the plan"""
    from wbik import State
    n=len(states); res={}
    tt=rec['t']; ok=tt>=0
    plan=np.array([states[min(n-1,max(0,int(round(t*hz))))].t for t in tt])
    err=np.linalg.norm(rec['root']-plan,axis=1)
    res['root_err_max']=float(err[ok].max()); res['root_err_end']=float(err[-1])
    up=[]
    for qt,t in zip(rec['quat'],tt):
        R=np.zeros(9); mujoco.mju_quat2Mat(R,qt); R=R.reshape(3,3); Rp=states[min(n-1,max(0,int(round(t*hz))))].R
        c=(np.trace(R@Rp.T)-1)/2; up.append(math.degrees(math.acos(max(-1,min(1,c)))))
    up=np.array(up); res['tilt_err_max']=float(up[ok].max()); res['tilt_err_end']=float(up[-1])
    ratio=rec['taupk']/rec['lim']; ratio[:,[11,21]]=0
    res['tau_ratio_max']=float(ratio[ok].max()); i=np.unravel_index(ratio[ok].argmax(),ratio[ok].shape); res['tau_ratio_joint']=JN[i[1]]; res['tau_ratio_t']=float(tt[ok][i[0]])
    res['sat_frac']=float((rec['sat'][ok].max(axis=1)>0.5).mean())
    res['end_height_err']=float(rec['root'][-1][2]-states[-1].t[2])
    res['success']=bool(res['root_err_end']<25 and res['tilt_err_end']<8 and 'diverged' not in rec)
    return res
if __name__=='__main__':
    xml=build_xml(); m=mujoco.MjModel.from_xml_string(xml); d=mujoco.MjData(m)
    print('nq',m.nq,'nu',m.nu,'mass',sum(m.body_mass))
    # stand still test
    set_pose(m,d,np.eye(3),[0,100,0.5],np.zeros(22)); d.ctrl[:]=0
    for k in range(3000): mujoco.mj_step(m,d)
    print('after 3 s standing: root z (mm)',d.qpos[2]/MM,'tilt quat',d.qpos[3:7].round(4),'max |act force|',np.abs(d.actuator_force).max().round(3))
