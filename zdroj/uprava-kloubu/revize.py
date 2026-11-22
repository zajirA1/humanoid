"""Stránka revize: hotový simulátor + úprava, ze které revize vznikla (otevře se s ní).
python3 -I revize.py <simulátor.html> <vysledek.json> <název revize> <výstup.html>"""
import sys,json
src,res,name,out=sys.argv[1:5]
s=open(src,encoding='utf8').read(); R=json.load(open(res))
start=json.dumps(dict(revize=name,proslo=R['proslo'],upravy=R['upravy']),ensure_ascii=False)
assert '</' not in start
k='<script type="application/json" id="r14Data">'; assert s.count(k)==1
s=s.replace(k,'<script type="application/json" id="r14Start">'+start+'</script>'+k)
s=s.replace('<title>','<title>'+name+' · ',1)
open(out,'w',encoding='utf8').write(s); print('ok',len(s))
