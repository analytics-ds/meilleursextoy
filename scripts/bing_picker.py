"""
Picker web pour selectionner manuellement les images Bing par article.

Demarrage:
    python3 scripts/bing_picker.py

Puis ouvrir http://localhost:8888/
"""

import re
import json
import shutil
import threading
from pathlib import Path
from urllib.parse import quote
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests
from ddgs import DDGS

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "content" / "blog"
IMG_DIR = ROOT / "static" / "images" / "blog"
IMG_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

IMG_CACHE: dict[str, list[dict]] = {}
LOCK = threading.Lock()


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def has_image(slug):
    return (IMG_DIR / f"{slug}.jpg").exists()


def article_title(slug):
    p = BLOG_DIR / f"{slug}.md"
    if not p.exists():
        return slug
    fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
    if fm:
        for line in fm.splitlines():
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"')
    return slug


def article_query(slug):
    """Construit un query Bing court base sur le slug."""
    base = slug.replace("-", " ")
    # mots a filtrer pour avoir un query plus image-friendly
    drop = {"comment", "quel", "quels", "quelle", "ou", "pour", "le", "la", "les", "un", "une", "des", "du", "de", "vs", "a", "en", "son", "ses", "mon", "ma", "ne", "plus"}
    words = [w for w in base.split() if w not in drop]
    return " ".join(words)


def list_articles():
    files = sorted(BLOG_DIR.glob("*.md"))
    files = [f for f in files if f.name != "_index.md"]
    return [f.stem for f in files]


def fetch_images(slug, query, n=12):
    if slug in IMG_CACHE:
        return IMG_CACHE[slug]
    with LOCK:
        try:
            raw = list(DDGS().images(query, max_results=n, region="fr-fr", safesearch="moderate"))
        except Exception as e:
            print(f"ddgs error for '{query}': {e}")
            return []
    results = []
    for r in raw:
        results.append({
            "full": r.get("image", ""),
            "thumb": r.get("thumbnail") or r.get("image", ""),
            "title": (r.get("title") or "")[:80],
            "host": r.get("source") or r.get("url") or "",
        })
    IMG_CACHE[slug] = results
    return results


def download_image(url, dest):
    try:
        headers = {"User-Agent": UA, "Referer": "https://www.bing.com/"}
        r = requests.get(url, headers=headers, timeout=20, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        return dest.stat().st_size > 5000
    except Exception as e:
        print(f"download failed: {e}")
        return False


def update_frontmatter(slug, image_path):
    p = BLOG_DIR / f"{slug}.md"
    text = p.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return False
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
    p.write_text(f"---\n{chr(10).join(new)}\n---\n{body}", encoding="utf-8")
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, body, status=200, ctype="text/html; charset=utf-8"):
        body_b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body_b)))
        self.end_headers()
        self.wfile.write(body_b)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/":
            self._send(self.page_index())
        elif parsed.path == "/article":
            slug = qs.get("slug", [None])[0]
            if not slug:
                self._send("missing slug", 400, "text/plain")
                return
            self._send(self.page_article(slug))
        elif parsed.path == "/pick":
            slug = qs.get("slug", [None])[0]
            url = qs.get("url", [None])[0]
            if not slug or not url:
                self._send("missing params", 400, "text/plain")
                return
            dest = IMG_DIR / f"{slug}.jpg"
            ok = download_image(url, dest)
            if not ok:
                self._send(f"<p>download fail. <a href='/article?slug={slug}'>retry</a></p>")
                return
            update_frontmatter(slug, f"/images/blog/{slug}.jpg")
            nxt = self.next_slug(slug)
            if nxt:
                self.send_response(302)
                self.send_header("Location", f"/article?slug={nxt}")
                self.end_headers()
            else:
                self._send("<h2>Tous les articles ont une image.</h2><p><a href='/'>Retour</a></p>")
        elif parsed.path == "/skip":
            slug = qs.get("slug", [None])[0]
            nxt = self.next_slug(slug)
            if nxt:
                self.send_response(302)
                self.send_header("Location", f"/article?slug={nxt}")
                self.end_headers()
            else:
                self._send("<h2>Termine.</h2><p><a href='/'>Retour</a></p>")
        elif parsed.path == "/edit-query":
            slug = qs.get("slug", [None])[0]
            new_q = qs.get("q", [""])[0]
            if slug and new_q:
                IMG_CACHE.pop(slug, None)
                QUERY_OVERRIDE[slug] = new_q
                self.send_response(302)
                self.send_header("Location", f"/article?slug={slug}")
                self.end_headers()
            else:
                self._send("missing", 400, "text/plain")
        else:
            self._send("not found", 404, "text/plain")

    def next_slug(self, current):
        slugs = list_articles()
        try:
            i = slugs.index(current)
        except ValueError:
            i = -1
        for s in slugs[i + 1 :]:
            if not has_image(s):
                return s
        for s in slugs[: max(0, i)]:
            if not has_image(s):
                return s
        return None

    def page_index(self):
        slugs = list_articles()
        rows = []
        for s in slugs:
            done = has_image(s)
            title = article_title(s)
            mark = "[OK]" if done else "[--]"
            rows.append(
                f'<li class="row {"done" if done else "todo"}">{mark} <a href="/article?slug={s}">{title}</a> <small>({s})</small></li>'
            )
        return f"""<!doctype html><html><head><meta charset=utf-8><title>Bing Picker</title>
<style>
body {{ font-family: ui-sans-serif, system-ui; max-width: 900px; margin: 30px auto; padding: 0 20px; color: #261108; background: #FFF8F5; }}
h1 {{ color: #FD2879; }}
ul {{ list-style: none; padding: 0; }}
.row {{ padding: 8px 12px; border-bottom: 1px solid #f0e4dc; }}
.done {{ color: #888; }}
.todo {{ color: #261108; }}
a {{ color: #FD2879; text-decoration: none; }}
</style></head><body>
<h1>Bing Picker - {sum(1 for s in slugs if has_image(s))}/{len(slugs)} done</h1>
<ul>{''.join(rows)}</ul>
</body></html>"""

    def page_article(self, slug):
        title = article_title(slug)
        query = QUERY_OVERRIDE.get(slug, article_query(slug))
        try:
            results = fetch_images(slug, query, n=16)
        except Exception as e:
            return f"<p>Search error: {e}</p><a href='/article?slug={slug}'>retry</a>"
        tiles = []
        for r in results:
            tiles.append(
                f"""
            <div class="tile">
              <a href="/pick?slug={slug}&url={quote(r['full'])}">
                <img src="{r['thumb']}" loading="lazy">
              </a>
              <div class="src"><a href="{r['host']}" target="_blank">{r['host'][:60]}</a></div>
            </div>"""
            )
        return f"""<!doctype html><html><head><meta charset=utf-8><title>{title}</title>
<style>
body {{ font-family: ui-sans-serif, system-ui; max-width: 1300px; margin: 20px auto; padding: 0 20px; color: #261108; background: #FFF8F5; }}
h1 {{ color: #261108; }}
h1 small {{ color: #999; font-weight: normal; font-size: 0.65em; }}
.actions {{ display: flex; gap: 12px; margin: 16px 0; align-items: center; flex-wrap: wrap; }}
.actions form {{ display: flex; gap: 8px; }}
.actions input[type=text] {{ padding: 6px 10px; border: 1px solid #ccc; border-radius: 6px; width: 360px; }}
.btn {{ padding: 8px 14px; background: #FD2879; color: white; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; font-size: 14px; }}
.btn.alt {{ background: #888; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 20px; }}
.tile {{ background: white; border-radius: 8px; overflow: hidden; border: 1px solid #eee; }}
.tile img {{ width: 100%; height: 180px; object-fit: cover; display: block; cursor: pointer; transition: transform 0.15s; }}
.tile:hover img {{ transform: scale(1.03); }}
.src {{ padding: 6px 10px; font-size: 11px; color: #999; }}
.src a {{ color: #999; }}
</style></head><body>
<h1>{title} <small>({slug})</small></h1>
<div class="actions">
  <a class="btn alt" href="/skip?slug={slug}">Skip ({slug})</a>
  <a class="btn alt" href="/">Index</a>
  <form action="/edit-query" method="get">
    <input type="hidden" name="slug" value="{slug}">
    <input type="text" name="q" placeholder="Nouveau query Bing" value="{query}">
    <button class="btn" type="submit">Re-chercher</button>
  </form>
</div>
<div class="grid">{''.join(tiles)}</div>
</body></html>"""


QUERY_OVERRIDE: dict[str, str] = {}


def main():
    print("Image picker ready on http://localhost:8888/")
    server = HTTPServer(("127.0.0.1", 8888), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
