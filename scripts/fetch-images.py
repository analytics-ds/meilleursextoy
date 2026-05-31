#!/usr/bin/env python3
"""
Telecharge les images (produits + en-tetes blog + auteur) via DuckDuckGo image search.
Valide que c'est une vraie image raster, convertit/recadre en JPG.
Usage: python3 scripts/fetch-images.py
"""
import os, sys, time, io, urllib.request, ssl

from ddgs import DDGS
try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROD = os.path.join(ROOT, 'static/images/products')
BLOG = os.path.join(ROOT, 'static/images/blog')
AUTH = os.path.join(ROOT, 'static/images/author')
for p in (PROD, BLOG, AUTH): os.makedirs(p, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE

# (fichier, requete, ratio cible w/h). ratio None = pas de recadrage strict (produit, garde tel quel en jpg)
PRODUCTS = [
    ("womanizer-premium-2.jpg", "Womanizer Premium 2 clitoral stimulator product"),
    ("satisfyer-pro-2.jpg", "Satisfyer Pro 2 product"),
    ("we-vibe-nova-2.jpg", "We-Vibe Nova 2 rabbit vibrator product"),
    ("lovense-lush-3.jpg", "Lovense Lush 3 wearable egg product"),
    ("magic-wand-rechargeable.jpg", "Magic Wand Rechargeable massager product"),
    ("lelo-ina-3.jpg", "LELO Ina 3 rabbit vibrator product"),
    ("satisfyer-penguin.jpg", "Satisfyer Penguin air pulse product"),
    ("arcwave-ion.jpg", "Arcwave Ion masturbator product"),
    ("fleshlight-launch.jpg", "Fleshlight Launch product"),
    ("lovense-max-2.jpg", "Lovense Max 2 masturbator product"),
    ("lovense-gush.jpg", "Lovense Gush product"),
    ("we-vibe-vector.jpg", "We-Vibe Vector prostate massager product"),
    ("tenga-flip-zero.jpg", "Tenga Flip Zero product"),
    ("lelo-f1s.jpg", "LELO F1S V2 product"),
    ("lovense-hush.jpg", "Lovense Hush 2 butt plug product"),
    ("lelo-hugo.jpg", "LELO Hugo prostate massager product"),
    ("we-vibe-pivot.jpg", "We-Vibe Pivot cock ring product"),
    ("we-vibe-sync.jpg", "We-Vibe Sync 2 couples product"),
    ("we-vibe-nova-2.jpg", "We-Vibe Nova 2 product"),
]
HEADERS = [
    ("meilleur-sextoy.jpg", "silk bed sheets sensual minimal aesthetic"),
    ("meilleur-sextoy-femme.jpg", "woman bedroom soft light intimate aesthetic"),
    ("meilleur-sextoy-homme.jpg", "man bedroom moody dark aesthetic"),
    ("choisir-sextoy.jpg", "gift box pink ribbon minimal aesthetic"),
    ("utiliser-sextoy.jpg", "couple holding hands bed intimate soft"),
    ("nettoyer-sextoy.jpg", "clean white bathroom soap water minimal"),
    ("fabriquer-sextoy-maison.jpg", "warning safety minimal pink background"),
    ("ou-acheter-sextoy.jpg", "discreet parcel delivery box minimal"),
]
AUTHOR = [("camille.jpg", "professional woman portrait headshot smiling brunette")]

def save_jpg(data, path, crop_ratio=None):
    if not HAVE_PIL:
        open(path, 'wb').write(data); return True
    try:
        im = Image.open(io.BytesIO(data)).convert('RGB')
    except Exception:
        return False
    w, h = im.size
    if w < 300 or h < 300:
        return False
    if crop_ratio:
        target = crop_ratio
        cur = w / h
        if cur > target:  # trop large -> crop largeur
            nw = int(h * target); x = (w - nw)//2; im = im.crop((x,0,x+nw,h))
        else:             # trop haut -> crop hauteur
            nh = int(w / target); y = (h - nh)//2; im = im.crop((0,y,w,y+nh))
    im.thumbnail((1600,1600))
    im.save(path, 'JPEG', quality=86)
    return True

def fetch(query, n=8):
    out = []
    try:
        with DDGS() as d:
            for r in d.images(query, max_results=n):
                u = r.get('image')
                if u: out.append(u)
    except Exception as e:
        print("  search err:", e)
    return out

def download(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=20, context=CTX).read()
    except Exception:
        return None

def process(jobs, folder, crop_ratio, only_missing=True):
    done, fail = [], []
    for fname, query in jobs:
        path = os.path.join(folder, fname)
        if only_missing and os.path.exists(path) and os.path.getsize(path) > 5000:
            print(f"SKIP {fname} (existe)"); done.append(fname); continue
        ok = False
        for url in fetch(query):
            data = download(url)
            if not data or len(data) < 5000: continue
            if save_jpg(data, path, crop_ratio):
                print(f"OK   {fname}  <- {url[:70]}"); ok = True; break
        if not ok:
            print(f"FAIL {fname}"); fail.append(fname)
        else:
            done.append(fname)
        time.sleep(1)
    return done, fail

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    allfail = []
    if which in ("all","products"):
        print("=== PRODUITS ===")
        _, f = process(PRODUCTS, PROD, None); allfail += f
    if which in ("all","headers"):
        print("=== EN-TETES ===")
        _, f = process(HEADERS, BLOG, 16/9); allfail += f
    if which in ("all","author"):
        print("=== AUTEUR ===")
        _, f = process(AUTHOR, AUTH, 1.0); allfail += f
    print("\nECHECS:", allfail if allfail else "aucun")
