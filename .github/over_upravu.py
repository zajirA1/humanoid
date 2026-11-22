"""Načte úpravu z proměnné UPRAVA (JSON nebo cesta k souboru v repozitáři), ověří ji a uloží. Vytvoří id přepočtu."""
import os,sys,json,re,hashlib,datetime
src=os.environ.get('UPRAVA','').strip()
if src.startswith('{'): U=json.loads(src)
else:
    p=os.path.normpath(src)
    if p.startswith('..') or os.path.isabs(p) or not p.startswith('upravy/') or not p.endswith('.json'): sys.exit('Cesta musí vést do složky upravy/ a končit .json')
    U=json.load(open(p))
up=U.get('upravy')
if not isinstance(up,dict) or not up: sys.exit('Úprava neobsahuje žádný posunutý kloub')
cist={}
for k,e in up.items():
    if not re.fullmatch(r'\d{1,2}',str(k)) or not 0<=int(k)<22 or int(k) in (0,1,11,21): sys.exit(f'Kloub {k} nelze upravit')
    d=e.get('posun_mm')
    if not (isinstance(d,list) and len(d)==3 and all(isinstance(v,(int,float)) and abs(v)<=40 for v in d)): sys.exit(f'Kloub {k}: posun musí být tři čísla v rozsahu ±40 mm')
    rt=e.get('natoceni_serva_deg',0)
    if not isinstance(rt,(int,float)) or abs(rt)>180: sys.exit(f'Kloub {k}: neplatné natočení')
    cist[str(int(k))]=dict(kloub=str(e.get('kloub',''))[:80],posun_mm=[float(v) for v in d],nese_dalsi_dily=bool(e.get('nese_dalsi_dily',False)),natoceni_serva_deg=float(rt))
out=dict(model='Emil H22 R13',upravy=cist)
json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False,indent=1)
i=os.environ.get('VSTUP_ID','').strip()
if not re.fullmatch(r'[A-Za-z0-9-]{4,40}',i): i=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+hashlib.sha256(json.dumps(cist,sort_keys=True).encode()).hexdigest()[:6]
open(os.path.join(os.path.dirname(sys.argv[1]),'id.txt'),'w').write(i); print('id',i,'kloubů',len(cist))
