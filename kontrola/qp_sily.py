"""EXPERIMENTÁLNÍ – regulace sil v oporách přes QP (22. 11. 2026). Automatická kontrola ho zatím nepoužívá.

Každých 10 ms:
  1. požadovaná výslednice na robota: tíha + PD na těžiště (plán z statiky) + PD na náklon trupu (IMU),
  2. QP rozdělí výslednici do bodů opor (chodidlo 4 rohy, holeň 2 body, dlaň 1 bod):
     min |A f − W|² + λ |f − f_plán|², f_z ≥ minimum (nezbytná opora ≥ F_MIN celkem), |f_x|,|f_y| ≤ μ f_z (jehlan),
  3. chyba sil v každé opoře (požadovaná − změřená, pro chodidlo i moment) → potřebná změna momentů kloubů Δτ = −Jᵀ Δf,
  4. polohová serva neumí řídit moment: Δτ se převede na posun povelu Δq = Δτ / kp (poddajnost serva), vyhlazený a omezený.
Potřebná čidla na skutečném robotu: IMU, síly v dlaních, holeních a chodidlech (chodidlo aspoň 4 body), úhly kloubů.
Skutečná serva STS mají jen polohovou smyčku a jejich tuhost není přesně známá – převod přes kp je proto odhad."""
import math, os, numpy as np, mujoco, quadprog
from vyvazovani import OPORY, GEOM
BODY={'leftFoot':[(57+s*36,-10+t*57,0) for s in (-1,1) for t in (-1,1)],'rightFoot':[(-57+s*36,-10+t*57,0) for s in (-1,1) for t in (-1,1)],
      'leftKnee':[(54,-24,85),(54,-24,122)],'rightKnee':[(-54,-24,85),(-54,-24,122)],'leftPalm':[(146,-12,193)],'rightPalm':[(-146,-12,193)]}
G0=9.81
class SilyQP:
    def __init__(s,m,cil_sil,nez=None,F_MIN=5.0,KP_COM=40.0,KD_COM=8.0,KP_ROT=3.0,KD_ROT=0.3,LAMBDA=0.02,MU=0.35,K_SILA=0.6,FILTR=0.3,MAX_DQ=8.0,ROVNOMERNE=0.0,K_INT=0.0,UNIK=0.3,**_):
        s.m=m; s.cil=cil_sil; s.nez=nez; s.Fmin=F_MIN; s.kpc=KP_COM; s.kdc=KD_COM; s.kpr=KP_ROT; s.kdr=KD_ROT; s.lam=LAMBDA; s.mu=MU
        s.ks=K_SILA; s.filtr=FILTR; s.maxdq=math.radians(MAX_DQ); s.rovn=ROVNOMERNE; s.ki=K_INT; s.unik=UNIK; s.qi=np.zeros(22)
        s.bid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,b) for k,(b,_) in OPORY.items()}
        s.gid={k:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,g) for k,g in GEOM.items()}
        s.root=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,'b22'); s.mtot=float(m.body_subtreemass[s.root])
        s.kp=np.array([m.actuator_gainprm[j,0] for j in range(22)]); s.dq=np.zeros(22); s.f6=np.zeros(6); s.com_prev=None; s.log=[]
    def zmer(s,d,sup):
        """změřené síly na robota (svět) a jejich působiště, po oporách"""
        inv={s.gid[k]:k for k in sup}; out={k:[] for k in sup}
        for c in range(d.ncon):
            con=d.contact[c]; k=inv.get(con.geom1) or inv.get(con.geom2)
            if k is None: continue
            mujoco.mj_contactForce(s.m,d,c,s.f6); fw=con.frame.reshape(3,3).T@s.f6[:3]
            if con.geom1==s.gid[k]: fw=-fw
            out[k].append((con.pos.copy(),fw))
        return out
    def krok(s,d,i,R_plan,dt,com_plan=None):
        m=s.m; plan=s.cil[i]; sup=[k for k in plan if k in s.gid]
        if not sup or com_plan is None: s.dq*=0.98; return s.dq
        nez=s.nez[i] if s.nez else set()
        com=d.subtree_com[s.root].copy(); vc=np.zeros(3) if s.com_prev is None else (com-s.com_prev)/dt; s.com_prev=com
        # 1) požadovaná výslednice
        ec=np.asarray(com_plan)*1e-3-com; ec[2]=0; vc[2]=0
        Fw=s.mtot*(np.array([0,0,G0])+s.kpc*ec-s.kdc*vc)
        Rm=d.xmat[s.root].reshape(3,3); Re=R_plan@Rm.T; er=0.5*np.array([Re[2,1]-Re[1,2],Re[0,2]-Re[2,0],Re[1,0]-Re[0,1]])
        om=d.cvel[s.root][:3]; Mw=s.mtot*(s.kpr*er-s.kdr*om)
        # 2) body opor ve světě
        pts=[];own=[]
        for k in sup:
            R=d.xmat[s.bid[k]].reshape(3,3); x=d.xpos[s.bid[k]]
            for p in BODY[k]: pts.append(x+R@(np.array(p)*1e-3)); own.append(k)
        n=len(pts); A=np.zeros((6,3*n))
        for j,p in enumerate(pts):
            A[:3,3*j:3*j+3]=np.eye(3); r=p-com; A[3:,3*j:3*j+3]=np.array([[0,-r[2],r[1]],[r[2],0,-r[0]],[-r[1],r[0],0]])
        W=np.r_[Fw,Mw]; wt=np.r_[1,1,1,30,30,30]
        cnt={k:own.count(k) for k in sup}; Wp=sum(plan[k] for k in sup) or 1.0
        fref=np.zeros(3*n)
        for j,k in enumerate(own):
            fz=(plan[k]/Wp*(1-s.rovn)+s.rovn/len(sup))*s.mtot*G0/cnt[k]; fref[3*j+2]=fz
        H=A.T@np.diag(wt)@A+s.lam*np.eye(3*n)+1e-9*np.eye(3*n); g=A.T@(wt*W)+s.lam*fref
        C=[];b=[]
        for j,k in enumerate(own):
            fmin=(s.Fmin if k in nez else 0.5)/cnt[k]; e=np.zeros(3*n); e[3*j+2]=1; C.append(e); b.append(fmin)
            for a in (0,1):
                for sg in (1,-1):
                    e=np.zeros(3*n); e[3*j+2]=s.mu; e[3*j+a]=-sg; C.append(e); b.append(0.0)
        try: f=quadprog.solve_qp(H,g,np.array(C).T,np.array(b))[0]
        except ValueError: s.dq*=0.98; return s.dq
        # 3) chyba sil po oporách → Δτ = −Jᵀ Δf
        meas=s.zmer(d,sup); tau=np.zeros(m.nv)
        for k in sup:
            js=[j for j,o in enumerate(own) if o==k]; R=d.xmat[s.bid[k]].reshape(3,3); ref=d.xpos[s.bid[k]]+R@(np.array(OPORY[k][1])*1e-3)
            fd=sum(f[3*j:3*j+3] for j in js); md=sum(np.cross(pts[j]-ref,f[3*j:3*j+3]) for j in js)
            fm=sum((fw for _,fw in meas[k]),np.zeros(3)); mm=sum((np.cross(p-ref,fw) for p,fw in meas[k]),np.zeros(3))
            Jp=np.zeros((3,m.nv)); Jr=np.zeros((3,m.nv)); mujoco.mj_jac(m,d,Jp,Jr,ref,s.bid[k])
            tau-=Jp.T@(fd-fm)
            if 'Foot' in k or 'Knee' in k: tau-=Jr.T@(md-mm)
        # 4) poddajnost polohového serva: Δq = Δτ / kp
        # integrační složka (poddajnost/admitance): dokud opora nenese, končetina se k ní dál přisouvá; pomalý únik k nule
        s.qi=np.clip(s.qi*(1-s.unik*dt)+s.ki*dt*tau[6:]/s.kp,-s.maxdq,s.maxdq)
        dq=np.clip(s.ks*tau[6:]/s.kp+s.qi,-s.maxdq,s.maxdq); dq[[11,21]]=0
        s.dq=(1-s.filtr)*s.dq+s.filtr*dq
        if getattr(s,'ladit',False) and i%int(os.environ.get("KAZDY","30"))==0:
            print(f'f{i} ec {np.round(ec[:2]*1e3,1)} er {np.round(np.degrees(er),1)} plán { {k:round(plan[k],1) for k in sup} } QP { {k:round(sum(f[3*j+2] for j,o in enumerate(own) if o==k),1) for k in sup} } změř { {k:round(sum((fw[2] for _,fw in meas[k]),0.0),1) for k in sup} } |dq| {np.degrees(np.abs(s.dq).max()):.1f}°',flush=True)
        return s.dq
