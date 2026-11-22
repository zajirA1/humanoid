"""Turn the final records into the JSON blocks the viewer expects."""
import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
from final_build import PHASES_END
import json
ORIGJ=json.load(open(W+'r9ClimbData.json'))
PH=[dict(p) for p in ORIGJ['phases'][:13]]
PH[0]['description']='Emil se přiblíží k hraně, pokrčí nohy a obě dlaně vede vzhůru a dopředu nad nášlap.'
PH[1]['description']='Obě dlaně dosedají 40 mm za hranu (levá o 30 mm hlouběji než v R12). Paty zůstávají na podlaze. Přenos váhy čeká na potvrzení opory rukou.'
PH[4]['description']='Levou dlaň Emil posune ke středu těla a 139 mm za hranu, pravou položí do strany 9 mm za hranu. Trup se při tom posouvá a natáčí tak, aby ramena zůstávala co nejblíž nad dlaněmi.'
PH[5]['description']='Váha se přesune na levou holeň a obě dlaně dřív, než se pravá špička odlepí. Špička opouští zem z dřívější, výhodnější polohy odvalu než v R12.'
PH[7]['description']='Obě holeně spočívají na stupni. Emil přesune dlaně jednu po druhé na 234 mm za hranu (o 30 mm blíž k tělu než v R12, dál od zadní hrany nášlapu).'
PH[12]['description']='Obě dlaně spočívají na nášlapu. Emil postupně zvedne každé chodidlo o 12 mm a položí na stupeň i patu.'
PH+= [dict(name=a,description=b) for a,b in PHASES_END]
def export(recs,rows,sim=None):
    poses=[];loads=[]
    for i,(rec,row) in enumerate(zip(recs,rows)):
        st=rec['state']; poses.append(st.pose(phase=int(rec['phase']),contacts=contact_points(st,rec['contacts'])))
        r=row['r']; tau=[round(float(x),5) for x in r['tau']]; F=r['forces']
        lN=float(F.get('leftPalm',np.zeros(3))[2]); rN=float(F.get('rightPalm',np.zeros(3))[2]); j=int(r['jmax'])
        ld=dict(tau=tau,ratio=round(float(r['s']),5),cm=[round(float(x),3) for x in r['com']],joint=JN[j],palmN=round(max(lN,rN),3),rightN=round(rN,3),leftN=round(lN,3),margin=round(float(row['margin']),3),
                kneeN=[round(float(F.get('leftKnee',np.zeros(3))[2]),2),round(float(F.get('rightKnee',np.zeros(3))[2]),2)],footN=[round(float(F.get('leftFoot',np.zeros(3))[2]),2),round(float(F.get('rightFoot',np.zeros(3))[2]),2)])
        if sim is not None and i<len(sim['ratio']): ld['moving']=round(float(sim['ratio'][i]),4); ld['movingTau']=[round(float(x),4) for x in sim['tau'][i]]
        loads.append(ld)
    ratios=np.array([l['ratio'] for l in loads]); k=int(ratios.argmax())
    check=dict(peak=[round(float(ratios[k]),5),k,loads[k]['joint']],failed=[],over=int((ratios>1).sum()),evaluated=len(loads))
    by={}
    for p in sorted(set(r['phase'] for r in recs)):
        idx=[i for i,r in enumerate(recs) if r['phase']==p]; kk=idx[int(ratios[idx].argmax())]
        by[str(p)]=dict(peak=[round(float(ratios[kk]),5),kk,loads[kk]['joint']],failed=[],over=0,evaluated=len(idx))
    return dict(poses=poses,phases=PH,hz=HZ),dict(loads=loads,check=check,byPhase=by)
