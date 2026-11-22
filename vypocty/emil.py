"""Emil H22 kinematics + mass model, ported from the page script (fk/rot/pos/dir)."""
import json, re, math
import numpy as np
W='/home/claude/work/'
data=json.load(open(W+'data.json'))
neck=json.load(open(W+'r9NeckData.json'))
P=np.array([neck['P'].get(str(i),p) for i,p in enumerate(data['P'])],float)
AX=np.array(data['axes'],float)
PAR=list(data['par'])
JN=data['joints']
sk=open(W+'skeleton.html').read()
m=re.search(r'const r10MassModels = (\{.*?\});\n',sk,re.S)
MM=json.loads(m.group(1))
LINKS=np.array(MM['r9']['links'])       # mass, com xyz (rest pose)
LIM=np.array(MM['r9']['limits'])
SOLE=MM['sole']
G=9.80665
def rot(axis,ang,pt):
    x,y,z=axis; a=math.radians(ang); s,c=math.sin(a),math.cos(a); v=1-c
    R=np.array([[c+x*x*v, x*y*v-z*s, x*z*v+y*s],[y*x*v+z*s, c+y*y*v, y*z*v-x*s],[z*x*v-y*s, z*y*v+x*s, c+z*z*v]])
    return R, np.asarray(pt)-R@np.asarray(pt)
def rt2T(rt):
    rt=np.asarray(rt,float); R=rt[:9].reshape(3,3).T; return R, rt[9:]
def fk(q,rt):
    w=[None]*23; w[22]=rt2T(rt)
    for i in range(22):
        Rp,tp=w[PAR[i]]; R,t=rot(AX[i],q[i],P[i]); w[i]=(Rp@R, Rp@t+tp)
    return w
def pt(w,link,p): R,t=w[link]; return R@np.asarray(p,float)+t
def com(w,links=LINKS):
    c=np.zeros(3)
    for i in range(23): c+=links[i,0]*pt(w,i,links[i,1:])
    return c/links[:,0].sum()
