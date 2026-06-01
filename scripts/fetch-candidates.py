#!/usr/bin/env python3
"""
Telecharge N candidats par slot d'image dans /tmp/candidates/<slot>/ pour verification visuelle.
Filtre les banques d'images a filigrane et les images trop petites.
Usage: python3 scripts/fetch-candidates.py <config.json>
config.json: [{"slot": "nom", "queries": ["q1","q2"], "ratio": 1.77 ou null, "n": 4}]
"""
import os, sys, io, json, time, ssl, urllib.request

from ddgs import DDGS
from PIL import Image

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

# domaines a filigrane ou hors sujet a bannir
BLACKLIST = ["dreamstime", "shutterstock", "istockphoto", "alamy", "123rf", "depositphotos",
             "gettyimages", "vecteezy", "freepik", "stock.adobe", "bigstock", "pond5",
             "craiyon", "pinimg", "pinterest", "tattoo", "anime", "fandom", "wikia",
             "instagram", "facebook", "tiktok", "store-images.s-microsoft"]

def dl(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=20, context=CTX).read()
    except Exception:
        return None

def save_candidate(data, path, ratio):
    try:
        im = Image.open(io.BytesIO(data)).convert('RGB')
    except Exception:
        return False
    w, h = im.size
    if w < 500 or h < 400:
        return False
    if ratio:
        cur = w / h
        if cur > ratio:
            nw = int(h * ratio); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
        else:
            nh = int(w / ratio); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
    im.thumbnail((1600, 1600))
    im.save(path, 'JPEG', quality=86)
    return True

def main():
    config = json.load(open(sys.argv[1]))
    base = "/tmp/candidates"
    for job in config:
        slot = job["slot"]; queries = job["queries"]; ratio = job.get("ratio"); n = job.get("n", 4)
        outdir = os.path.join(base, slot)
        os.makedirs(outdir, exist_ok=True)
        saved = 0
        seen_urls = set()
        for q in queries:
            if saved >= n: break
            try:
                with DDGS() as d:
                    results = list(d.images(q, max_results=12))
            except Exception as e:
                print(f"  search err {q}: {e}"); continue
            for r in results:
                if saved >= n: break
                u = r.get('image') or ""
                if not u or u in seen_urls: continue
                seen_urls.add(u)
                low = u.lower()
                if any(b in low for b in BLACKLIST): continue
                data = dl(u)
                if not data or len(data) < 10000: continue
                path = os.path.join(outdir, f"{saved+1}.jpg")
                if save_candidate(data, path, ratio):
                    # garder la source pour reference
                    open(os.path.join(outdir, f"{saved+1}.src.txt"), 'w').write(u)
                    saved += 1
            time.sleep(1)
        print(f"{slot}: {saved} candidats")

if __name__ == "__main__":
    main()
