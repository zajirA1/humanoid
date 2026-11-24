"""Emil ETA: kalibrace a rektifikace uložených snímků z levé a pravé USB kamery."""
import argparse
import json
from pathlib import Path
import sys

import cv2 as cv
import numpy as np


def obraz(cesta, priznak):
    raw = np.fromfile(cesta, np.uint8)
    img = cv.imdecode(raw, priznak) if raw.size else None
    if img is None:
        raise ValueError(f'Nelze načíst snímek {cesta}.')
    return img


def obrazky(slozka):
    vysledek = {}
    for p in sorted(slozka.iterdir()):
        if p.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.bmp'):
            continue
        if p.stem in vysledek:
            raise ValueError(f'Duplicitní název záběru {p.stem} ve složce {slozka}.')
        vysledek[p.stem] = p
    return vysledek


def deska(sloupce, radky, policko):
    if sloupce < 3 or radky < 3 or sloupce == radky or not 0 < policko < 1000:
        raise ValueError('Použij obdélníkový vzor s odlišným počtem vnitřních rohů a šířkou políčka v mm.')
    body = np.zeros((sloupce*radky, 3), np.float32)
    body[:,:2] = np.mgrid[:sloupce,:radky].T.reshape(-1,2)*policko
    return body


def kalibrace(opt):
    model = deska(opt.sloupce,opt.radky,opt.policko)
    leve,prave = obrazky(opt.leve),obrazky(opt.prave)
    if leve.keys() != prave.keys():
        raise ValueError('Vstupní složky musí obsahovat stejné dvojice podle názvu bez přípony.')
    body,leva,prava = [],[],[]
    rozmer = None
    for jmeno in leve:
        nalezy=[]
        for p in (leve[jmeno],prave[jmeno]):
            img=obraz(p,cv.IMREAD_GRAYSCALE)
            velikost=tuple(img.shape[::-1])
            if rozmer is not None and velikost!=rozmer:
                raise ValueError(f'Rozměr snímku {p} se liší od ostatních.')
            rozmer=velikost
            ok,rohy=cv.findChessboardCornersSB(img,(opt.sloupce,opt.radky),flags=cv.CALIB_CB_NORMALIZE_IMAGE)
            if ok:
                nalezy.append(rohy)
        if len(nalezy)!=2:
            print(f'Přeskočeno: {jmeno}. Celá šachovnice musí být viditelná v obou obrazech.')
            continue
        l,r=nalezy
        # U dvojice téměř rovnoběžných kamer může detektor vzor seřadit opačně.
        if np.dot((l[-1]-l[0]).ravel(),(r[-1]-r[0]).ravel())<0:
            r=r[::-1].copy()
        body.append(model); leva.append(l); prava.append(r)
    if len(body)<10:
        raise ValueError(f'Použitelných dvojic je {len(body)}. Připrav alespoň deset různých náklonů a poloh.')
    _,k1,d1,_,_=cv.calibrateCamera(body,leva,rozmer,None,None)
    _,k2,d2,_,_=cv.calibrateCamera(body,prava,rozmer,None,None)
    rms,k1,d1,k2,d2,r,t,_,_=cv.stereoCalibrate(
        body,leva,prava,k1,d1,k2,d2,rozmer,flags=cv.CALIB_FIX_INTRINSIC)
    r1,r2,p1,p2,q,_,_=cv.stereoRectify(k1,d1,k2,d2,rozmer,r,t,flags=cv.CALIB_ZERO_DISPARITY,alpha=0)
    fx=float(p1[0,0]); b=float(-p2[0,3]/p2[0,0])
    if not np.isfinite([rms,fx,b]).all() or fx<=0 or b<=0 or abs(p2[1,3])>1e-5:
        raise ValueError('Ověř levou a pravou kameru a jejich vodorovnou montáž. Kalibrace nemá kladnou vodorovnou základnu.')
    chyby=[]
    for l,rp in zip(leva,prava):
        l=cv.undistortPoints(l,k1,d1,R=r1,P=p1).reshape(-1,2)
        rp=cv.undistortPoints(rp,k2,d2,R=r2,P=p2).reshape(-1,2)
        chyby.extend(abs(l[:,1]-rp[:,1]))
    info=dict(fx_px=fx,baseline_mm=b,cx_px=float(p1[0,2]),cy_px=float(p1[1,2]),
              width=rozmer[0],height=rozmer[1],pairs=len(body),rms_px=float(rms),
              vertical_p95_px=float(np.percentile(chyby,95)))
    opt.cil.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(opt.cil/'kalibrace.npz',k1=k1,d1=d1,k2=k2,d2=d2,r1=r1,r2=r2,p1=p1,p2=p2,q=q,
                        size=np.array(rozmer))
    report=json.dumps(info,indent=2,allow_nan=False)
    (opt.cil/'parametry.json').write_text(report+'\n',encoding='utf8')
    print(report)


def narovnat(opt):
    with np.load(opt.kalibrace,allow_pickle=False) as profil:
        rozmer=tuple(map(int,profil['size']))
        par=[obraz(p,cv.IMREAD_COLOR) for p in (opt.leva,opt.prava)]
        if any(tuple(img.shape[1::-1])!=rozmer for img in par):
            raise ValueError(f'Kalibrace očekává snímky {rozmer[0]} × {rozmer[1]} px.')
        opt.cil.mkdir(parents=True,exist_ok=True)
        for i,(img,jmeno) in enumerate(zip(par,('leva','prava')),1):
            mx,my=cv.initUndistortRectifyMap(profil[f'k{i}'],profil[f'd{i}'],profil[f'r{i}'],profil[f'p{i}'],rozmer,cv.CV_32FC1)
            out=cv.remap(img,mx,my,cv.INTER_LINEAR)
            ok,data=cv.imencode('.png',out)
            if not ok:
                raise ValueError('Zápis rektifikovaného obrazu selhal.')
            data.tofile(opt.cil/f'{jmeno}-rekt.png')


def vzdalenost(opt):
    with np.load(opt.kalibrace,allow_pickle=False) as profil:
        w,h=profil['size']
        if not (0<=opt.xl<w and 0<=opt.xr<w and 0<=opt.yl<h and 0<=opt.yr<h):
            raise ValueError('Bod je mimo rozměry kalibrovaného obrazu.')
        if abs(opt.yl-opt.yr)>2 or opt.xl<=opt.xr:
            raise ValueError('Vyber stejný bod v obou narovnaných obrazech. Je potřeba kladná disparita a rozdíl řádků do 2 px.')
        disparity=opt.xl-opt.xr
        z=float(-profil['p2'][0,3]/disparity)
        print(f'Optická hloubka: {z:.1f} mm; disparita: {disparity:.2f} px.')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    akce=ap.add_subparsers(dest='ukol',required=True)
    k=akce.add_parser('kalibrovat',help='Najde rohy ve dvojicích záběrů šachovnice.')
    for key in ('leve','prave','cil'): k.add_argument(key,type=Path)
    k.add_argument('--sloupce',type=int,default=9)
    k.add_argument('--radky',type=int,default=6)
    k.add_argument('--policko',type=float,required=True,help='Skutečná šířka políčka v milimetrech')
    k.set_defaults(func=kalibrace)
    n=akce.add_parser('narovnat',help='Uloží dva rektifikované PNG pro měření.')
    for key in ('kalibrace','leva','prava','cil'): n.add_argument(key,type=Path)
    n.set_defaults(func=narovnat)
    v=akce.add_parser('zmerit',help='Spočítá osovou hloubku ze souřadnic stejného bodu.')
    v.add_argument('kalibrace',type=Path)
    for key in ('xl','yl','xr','yr'): v.add_argument(key,type=float)
    v.set_defaults(func=vzdalenost)
    opt=ap.parse_args()
    try:
        opt.func(opt)
    except (ValueError,OSError,cv.error) as exc:
        sys.exit(str(exc))
