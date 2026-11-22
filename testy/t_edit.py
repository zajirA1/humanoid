import sys,json; sys.path.insert(0,'/home/claude/sim')
from contact import *
import emil
T=json.load(open('t_edit.json')); D=json.load(open('r14data.json'))
sub=lambda j:[k for k in range(22) if j in ANC[k]]
shift=np.zeros((23,3))
for k,e in T['ed'].items():
    j=int(k); d=np.array(e['d'],float); L=PAR[j]
    LINKS[L,1:]+=d*D['servoKg'][j]/LINKS[L,0]
    if e.get('carry'):
        for s_ in sub(j): P[s_]+=d; LINKS[s_,1:]+=d; shift[s_]+=d
    else: P[j]+=d
md=0;n=0
for i in range(0,1141,7):
    q,sj,rt=T['out'][i]; st=State(*rt2T(rt),q); fl=D['contacts'][i]
    pts=[(fl[k],st.pt(fl[k],np.array(fl[k+1:k+4])+shift[fl[k]]),'c') for k in range(0,len(fl),4)]
    r=statics(st,[],extra_pts=pts)
    if r is None or sj is None: print('none',i,r is None,sj); continue
    md=max(md,abs(r['s']-sj)); n+=1
print('compared',n,'max diff',md)
