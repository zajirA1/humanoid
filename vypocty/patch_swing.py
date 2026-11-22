import sys; sys.path.insert(0,'/home/claude/sim')
from seqmetrics import *
recs=pickle.load(open('final9.pkl','rb')); rows,sp=pickle.load(open('final9_m.pkl','rb'))
LIMB={**{l:[12,13,14,15,16,17] for l in (12,13,14,15,16,17)},**{l:[2,3,4,5,6,7] for l in (2,3,4,5,6,7)}}
def in_contact(rec,js):
    names={'leftFoot','leftKnee'} if js[0]==2 else {'rightFoot','rightKnee'}
    return bool(names&rec['contacts'])
def selfd(st): K.place(st); return K.min_dist(st,cutoff=14,placed=True)[0]
for (a,b) in ((306,310),(698,703)):
    pair=rows[(a+b)//2]['selfpair']; links=[pair[0][0],pair[1][0]]
    js=None
    for l in links:
        if l in LIMB and not in_contact(recs[(a+b)//2],LIMB[l]): js=LIMB[l]
    print(a,b,pair,'swing joints',js)
    if js is None: continue
    qa=recs[a]['state'].q[js].copy(); qb=recs[b]['state'].q[js].copy()
    for i in range(a+1,b):
        st=recs[i]['state']; before=selfd(st); q0=st.q.copy()
        st.q[js]=qa+(qb-qa)*(i-a)/(b-a); st.update(); after=selfd(st)
        if after<before: st.q=q0; st.update(); after=before
        print('  frame',i,round(before,1),'->',round(after,1))
pickle.dump(recs,open('final10.pkl','wb'))
