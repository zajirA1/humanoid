"""EXPERIMENTÁLNÍ – zatím NEFUNKČNÍ (22. 11. 2026, výsledky v vypocty/robustnost-2026-11-22/README.md).
Automatická kontrola ho nepoužívá (simuluj(..., vyvazovani=None)).

Vyvažování v dynamické simulaci – jen z veličin, které má skutečný robot: náklon a úhlová rychlost trupu (IMU),
svislé síly v dlaních, holeních a chodidlech, úhly kloubů. Každých 20 ms:
  1. chyba sil: nezbytná opora nese méně, než má (plán, nejméně F_MIN) → požadovaný posun těžiště k ní,
  2. náklon trupu oproti plánu → požadované pootočení trupu zpět,
  3. nejmenší čtverce přes Jacobiány MuJoCo: posun těžiště a natočení trupu, opory na zemi se nesmí pohnout,
  4. výsledek = oprava povelů kloubů (omezená, vyhlazená), přičte se k plánovaným povelům."""
import math, numpy as np, mujoco
OPORY={'leftFoot':('b7',(57,-10,0)),'rightFoot':('b17',(-57,-10,0)),'leftKnee':('b5',(54,-24,103.5)),'rightKnee':('b15',(-54,-24,103.5)),
       'leftPalm':('b10',(146,-12,193)),'rightPalm':('b20',(-146,-12,193))}
GEOM={'leftFoot':'sole7','rightFoot':'sole17','leftKnee':'sleeve5','rightKnee':'sleeve15','leftPalm':'palm10','rightPalm':'palm20'}
LINK={'leftFoot':7,'rightFoot':17,'leftKnee':5,'rightKnee':15,'leftPalm':10,'rightPalm':20}
class Vyvazovani:
    def __init__(s,m,cil_sil,nez=None,F_MIN=4.0,K_SILA=1.0,K_NAKLON=1.0,K_TLUM=0.1,MAX_DQ=6.0,MAX_DC=15.0):
        s.m=m; s.cil=cil_sil; s.nez=nez; s.F_MIN=F_MIN; s.Ks=K_SILA; s.Kt=K_NAKLON; s.Kd=K_TLUM; s.maxdq=math.radians(MAX_DQ); s.maxdc=MAX_DC*1e-3
        s.bid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,b) for k,(b,_) in OPORY.items()}
        s.gid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,g) for k,g in GEOM.items()}
        s.root=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,'b22'); s.dq=np.zeros(22); s.dc=np.zeros(2); s.f6=np.zeros(6)
        s.log=[]
    def sily(s,d):
        F={k:0.0 for k in s.gid}; inv={g:k for k,g in s.gid.items()}
        for c in range(d.ncon):
            con=d.contact[c]
            for g in (con.geom1,con.geom2):
                if g in inv: mujoco.mj_contactForce(s.m,d,c,s.f6); F[inv[g]]+=abs(s.f6[0])
        return F
    def krok(s,d,i,R_plan,dt,com_plan=None):
        m=s.m; F=s.sily(d); plan=s.cil[i]; sup=[k for k in plan]
        if len(sup)<1 or com_plan is None: s.dq*=0.99; return s.dq
        com=d.subtree_com[s.root].copy()
        pos={k:d.xpos[s.bid[k]]+d.xmat[s.bid[k]].reshape(3,3)@(np.array(OPORY[k][1])*1e-3) for k in sup}
        # 1) střed tlaku: skutečný vs. požadovaný (plán; nezbytná opora aspoň F_MIN) → požadovaný posun těžiště dc (pomalu, s únikem)
        nez=s.nez[i] if s.nez else set()
        cil={k:(max(plan[k],s.F_MIN) if k in nez else plan[k]) for k in sup}
        Wm=sum(F[k] for k in sup); Wc=sum(cil.values())
        e=np.zeros(2)
        if len(sup)>=2 and Wm>5 and Wc>5:
            e=sum(cil[k]*pos[k][:2] for k in sup)/Wc-sum(F[k]*pos[k][:2] for k in sup)/Wm
        s.dc=np.clip(s.dc*(1-0.3*dt)+s.Ks*e*dt,-s.maxdc,s.maxdc)
        # chyba těžiště vůči plánu + požadovaný posun
        ec=(np.asarray(com_plan)[:2]*1e-3+s.dc)-com[:2]
        # 2) náklon trupu vůči plánu (IMU)
        Rm=d.xmat[s.root].reshape(3,3); Rerr=R_plan@Rm.T; er=np.array([Rerr[2,1]-Rerr[1,2],Rerr[0,2]-Rerr[2,0],Rerr[1,0]-Rerr[0,1]])*0.5
        # 3) nejmenší čtverce: změna q, která opraví těžiště a náklon, opory na místě
        nv=m.nv; Jc=np.zeros((3,nv)); mujoco.mj_jacSubtreeCom(m,d,Jc,s.root)
        Jr=np.zeros((3,nv)); mujoco.mj_jacBodyCom(m,d,None,Jr,s.root)
        rows=[Jc[:2]*1.0,Jr*0.3*s.Kt]; rhs=[ec*1.0,er*0.3*s.Kt]
        for k in sup:
            Jp=np.zeros((3,nv)); Jw=np.zeros((3,nv)); mujoco.mj_jac(m,d,Jp,Jw,pos[k],s.bid[k]); rows.append(1000*Jp); rhs.append(np.zeros(3))
            if 'Foot' in k: rows.append(1000*Jw); rhs.append(np.zeros(3))          # chodidlo celou plochou: ani natočení
            if 'Knee' in k:                                                        # holeň v linii: druhý bod návleku
                sx=1 if k=='leftKnee' else -1; p2=d.xpos[s.bid[k]]+d.xmat[s.bid[k]].reshape(3,3)@(np.array((sx*54,-24,85))*1e-3)
                J2=np.zeros((3,nv)); mujoco.mj_jac(m,d,J2,None,p2,s.bid[k]); rows.append(1000*J2); rhs.append(np.zeros(3))
        A=np.vstack(rows); b=np.concatenate(rhs)
        v=np.linalg.solve(A.T@A+np.diag([1e-9]*6+[1e-4]*(nv-6)),A.T@b)
        # 4) integrace opravy (pomalu), únik k nule, omezení
        s.dq=np.clip(s.dq*(1-0.2*dt)+s.Kd*v[6:],-s.maxdq,s.maxdq)
        if getattr(s,'ladit',False) and i%6==0 and False: print(f'f{i} ec {np.round(ec*1e3,1)} er {np.round(np.degrees(er),2)} |v| {np.abs(v[6:]).max():.4f} |dq| {np.degrees(np.abs(s.dq).max()):.2f}° opory {sup} sily { {k:round(F[k],1) for k in sup} }',flush=True)
        return s.dq
def cile_sil(frames,M,P_,E_,links,fk):
    """plánované síly opor (stejná tuhost) a množina nezbytných opor pro každou polohu"""
    import robustnost
    names={v:k for k,v in LINK.items()}; cile=[]; nez=[]
    for i,f in enumerate(frames):
        r=robustnost.poloha(fk(f['q'],f['rt'],P_,E_),M['contacts'][i],links)
        cile.append({names[l]:F for l,F in r['F'].items() if l in names}); nez.append({names[l] for l in r['nez'] if l in names})
    return cile,nez

class ReflexDlani:
    """Reflex dlaní: opora-dlaň, která má podle plánu nést (nebo je nezbytná), a nese méně → ruka se natáhne svisle dolů
    (klouby ramene a lokte, nejvýš MAX_MM); nese-li víc než dvojnásobek → povolí. Jen síla v dlani a úhly kloubů."""
    RUKA={'leftPalm':[8,9,10],'rightPalm':[18,19,20]}
    def __init__(s,m,cil_sil,nez=None,F_MIN=4.0,RYCHLOST=20.0,MAX_MM=15.0,**_):
        s.m=m; s.cil=cil_sil; s.nez=nez; s.F_MIN=F_MIN; s.v=RYCHLOST*1e-3; s.max=MAX_MM*1e-3
        s.bid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,OPORY[k][0]) for k in s.RUKA}
        s.gid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,GEOM[k]) for k in s.RUKA}
        s.z={k:0.0 for k in s.RUKA}; s.dq=np.zeros(22); s.f6=np.zeros(6)
    def krok(s,d,i,R_plan,dt,com_plan=None):
        m=s.m; plan=s.cil[i]; nez=s.nez[i] if s.nez else set(); dq=np.zeros(22)
        for k,J in s.RUKA.items():
            F=0.0
            for c in range(d.ncon):
                con=d.contact[c]
                if s.gid[k] in (con.geom1,con.geom2): mujoco.mj_contactForce(m,d,c,s.f6); F+=abs(s.f6[0])
            if k in plan:
                cil=max(plan[k],s.F_MIN) if k in nez else max(plan[k],1.0)
                if F<cil: s.z[k]=min(s.max,s.z[k]+s.v*dt)
                elif F>2*cil+2: s.z[k]=max(-s.max,s.z[k]-s.v*dt)
            else: s.z[k]*=(1-1.0*dt)                     # mimo oporu se reflex pomalu vrací
            if abs(s.z[k])>1e-6:
                p=d.xpos[s.bid[k]]+d.xmat[s.bid[k]].reshape(3,3)@(np.array(OPORY[k][1])*1e-3)
                Jp=np.zeros((3,m.nv)); mujoco.mj_jac(m,d,Jp,None,p,s.bid[k]); A=Jp[:,[6+j for j in J]]
                # posun dlaně o -z (dolů) jen klouby ruky; tlumené nejmenší čtverce
                x=np.linalg.solve(A.T@A+1e-5*np.eye(len(J)),A.T@np.array([0,0,-s.z[k]]))
                dq[J]=np.clip(x,-0.2,0.2)
        s.dq=0.8*s.dq+0.2*dq
        return s.dq

# regulace sil přes QP (experimentální) – dostupná jako trida="SilyQP"
try:
    from qp_sily import SilyQP  # noqa: E402  (potřebuje balík quadprog)
except ImportError:
    pass
