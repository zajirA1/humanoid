import sys; sys.path.insert(0,'/home/claude/sim')
from planner import *
TR=STEP_H; PZ=TR+PAD_R
def build(par=None):
    p=dict(y0=100.0, yp1=-60.0, ysh=-30.0, yp2=-165.0, yfoot=-80.0)
    if par: p.update(par)
    st=State(np.eye(3),[0,p['y0'],0],np.zeros(22))
    P=Plan(st); F={'leftFoot','rightFoot'}; LP='leftPalm'; RP='rightPalm'; LK='leftKnee'; RK='rightKnee'; LF='leftFoot'; RF='rightFoot'
    y0=p['y0']; yp1=p['yp1']; ysh=p['ysh']; yp2=p['yp2']; yf=p['yfoot']
    # 0 approach: lean, squat a little, hands above the tread
    P.seg(4,'Předklon a ruce nad nášlap',support=F, footL=[54,y0,0,0],footR=[-54,y0,0,0],
          com=[0,y0-15],pitch=48,pelz=262,wpelz=1.0,palmL=[146,yp1,PZ+30],palmR=[-146,yp1,PZ+30])
    # 1 palms down, load them
    P.seg(2.5,'Obě dlaně na nášlapu',support=F,palmL=[146,yp1,PZ],palmR=[-146,yp1,PZ])
    P.seg(3,support=F|{LP,RP},com=[-20,y0-45],pitch=50)
    # 2 left knee over the edge: unload left foot, lift, fold, cross
    P.seg(3,'Levé koleno přes hranu',support={RF,LP,RP},com=[-34,y0-55])
    P.seg(3,support={RF,LP,RP},legL='knee',kneeL=[54,y0-45,150,35],q6=20,wq6=0.5,pelz=272)
    P.seg(3.5,support={RF,LP,RP},kneeL=[54,25,238,80])
    P.seg(3,support={RF,LP,RP},kneeL=[54,ysh,TR+14,90])
    # 3 left shin down flat
    P.seg(2,'Dosednutí levé holeně',support={RF,LP,RP},kneeL=[54,ysh,TR,90])
    P.seg(3,support={RF,LP,RP,LK},com=[10,-10],pitch=52)
    # 4 re-grip forward under the shoulders, one palm at a time
    P.seg(2,'Přehmátnutí pod ramena',support={RF,LK,RP},palmL=[146,(yp1+yp2)/2,PZ+25])
    P.seg(2,support={RF,LK,RP},palmL=[146,yp2,PZ])
    P.seg(2,support={RF,LK,LP},palmR=[-146,(yp1+yp2)/2,PZ+25])
    P.seg(2,support={RF,LK,LP},palmR=[-146,yp2,PZ])
    # 5 weight onto the left shin, lift the rear leg
    P.seg(4,'Váha na levou holeň',support={LK,LP,RP},com=[30,-62],pitch=56)
    P.seg(3,'Zvednutí zadní nohy',support={LK,LP,RP},legR='knee',kneeR=[-54,y0-55,150,40],q16=-20,wq16=0.5)
    P.seg(3.5,support={LK,LP,RP},kneeR=[-54,25,238,80])
    P.seg(3,support={LK,LP,RP},kneeR=[-54,ysh,TR+14,90])
    P.seg(2,'Dosednutí pravé holeně',support={LK,LP,RP},kneeR=[-54,ysh,TR,90])
    P.seg(3,'Klek na obou holeních',support={LK,RK,LP,RP},com=[0,-55],pitch=55)
    return P
if __name__=='__main__':
    import time; t=time.time()
    P=build(); fr=P.run(verbose=True); print('frames',len(fr),time.time()-t)
    import pickle; pickle.dump((fr,P.phases),open('v1.pkl','wb'))
