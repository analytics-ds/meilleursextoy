"""
Telecharge une image Bing par article et met a jour le frontmatter.

Usage:
    python3 bing_images.py [slug ...]   # cible specifique
    python3 bing_images.py --all        # tous les articles sans image

Strategy keyword Bing:
- comparatifs marques (womanizer, satisfyer, lelo, we-vibe) -> nom marque + neutre
- anatomie (clitoris, point g, squirting) -> illustration scientifique minimaliste
- couple (rapport, deux, partenaire) -> couple ambiance bedroom minimal
- sante (grossesse, menopause, accouchement, vaginisme, hysterectomie) -> wellness minimal
- pratique (nettoyer, ranger, discret, livraison) -> lifestyle minimal beige
- defaut -> sextoy lifestyle minimal pink
"""

import re
import sys
import time
import json
import shutil
from pathlib import Path
from urllib.parse import quote
import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "content" / "blog"
IMG_DIR = ROOT / "static" / "images" / "blog"
IMG_DIR.mkdir(parents=True, exist_ok=True)

ANATOMY_KW = ["clitoris", "point-g", "squirting", "orgasme", "anatomie"]
COUPLE_KW = ["couple", "rapport", "deux", "partenaire", "longue-distance", "introduire", "proposer"]
SANTE_KW = ["grossesse", "menopause", "accouchement", "vaginisme", "hysterectomie"]
PRATIQUE_KW = ["nettoyer", "ranger", "discret", "livraison", "facture", "pharmacie", "acheter", "francaise", "lubrifiant", "douche", "phtalates", "silicone", "duree", "charge", "ne-charge", "ipx7", "batterie", "desinfecter"]
PRODUITS = {"womanizer": "womanizer pleasure air stimulator", "satisfyer": "satisfyer air pulse stimulator", "lelo": "lelo sona cruise vibrator", "we-vibe": "we-vibe chorus couple toy"}


def detect_query(slug: str) -> str:
    s = slug.lower()
    for brand, q in PRODUITS.items():
        if brand in s:
            return q + " product photography"
    if any(k in s for k in ANATOMY_KW):
        return "feminine wellness minimal aesthetic"
    if any(k in s for k in COUPLE_KW):
        return "couple bedroom intimacy soft light"
    if any(k in s for k in SANTE_KW):
        return "feminine wellness selfcare beige minimal"
    if any(k in s for k in PRATIQUE_KW):
        return "minimal pink beige lifestyle aesthetic"
    if "sextoy" in s or "vibromasseur" in s or "stimulateur" in s or "meilleur" in s:
        return "minimal sex toy beige aesthetic product"
    return "minimal beige pink wellness aesthetic"


def parse_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def has_image_field(fm: str) -> bool:
    return any(line.startswith("image:") for line in fm.splitlines())


def update_image_field(fm: str, image_path: str) -> str:
    lines = fm.splitlines()
    new = []
    found = False
    for line in lines:
        if line.startswith("image:"):
            new.append(f'image: "{image_path}"')
            found = True
        else:
            new.append(line)
    if not found:
        new.append(f'image: "{image_path}"')
    return "\n".join(new)


def fetch_bing_image(page, query: str, retries: int = 2) -> str | None:
    for attempt in range(retries + 1):
        url = f"https://www.bing.com/images/search?q={quote(query)}&form=HDRSC2&first=1"
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        try:
            href = page.evaluate(
                """() => {
                    const tiles = document.querySelectorAll('a.iusc');
                    for (const t of tiles) {
                        const m = t.getAttribute('m');
                        if (!m) continue;
                        try {
                            const o = JSON.parse(m);
                            if (o.murl && /\\.(jpg|jpeg|png|webp)(\\?|$)/i.test(o.murl)) {
                                return o.murl;
                            }
                        } catch(e) {}
                    }
                    return null;
                }"""
            )
            if href:
                return href
        except Exception as e:
            print(f"  ! eval failed attempt {attempt}: {e}")
        time.sleep(2)
    return None


def download_image(url: str, dest: Path) -> bool:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Referer": "https://www.bing.com/",
        }
        r = requests.get(url, headers=headers, timeout=20, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        return dest.stat().st_size > 5000
    except Exception as e:
        print(f"  ! download failed: {e}")
        return False


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 bing_images.py --all  ou  python3 bing_images.py slug1 slug2 ...")
        sys.exit(1)

    if "--all" in args:
        files = sorted(BLOG_DIR.glob("*.md"))
        files = [f for f in files if f.name != "_index.md"]
    else:
        files = [BLOG_DIR / f"{slug}.md" for slug in args]
        files = [f for f in files if f.exists()]

    print(f"Articles a traiter: {len(files)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        for i, path in enumerate(files, 1):
            slug = path.stem
            dest = IMG_DIR / f"{slug}.jpg"

            text = path.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            if fm is None:
                print(f"[{i}/{len(files)}] {slug}: pas de frontmatter, skip")
                continue

            if dest.exists() and dest.stat().st_size > 5000 and has_image_field(fm):
                print(f"[{i}/{len(files)}] {slug}: deja OK, skip")
                continue

            query = detect_query(slug)
            print(f"[{i}/{len(files)}] {slug}: query='{query}'")

            url = fetch_bing_image(page, query)
            if not url:
                print(f"  ! pas d'url trouvee, skip")
                continue

            print(f"  url={url[:80]}...")
            if not download_image(url, dest):
                print(f"  ! download fail, skip")
                continue
            print(f"  -> {dest.relative_to(ROOT)} ({dest.stat().st_size} bytes)")

            new_fm = update_image_field(fm, f"/images/blog/{slug}.jpg")
            path.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
            time.sleep(1)

        browser.close()


if __name__ == "__main__":
    main()
