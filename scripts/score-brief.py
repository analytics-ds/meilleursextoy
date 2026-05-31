#!/usr/bin/env python3
"""
Score un article Hugo contre son brief Datafer.
Usage: python3 scripts/score-brief.py <chemin_md> <brief_id>
Lit le .md, retire le frontmatter, convertit en HTML simple, POST a Datafer, affiche score vs best.
"""
import sys, json, re, urllib.request

API = "https://datafer.analytics-e0d.workers.dev"
KEY = "dfk_HFyaak33DxoUGiXd0PV0ehonsX_VK-QFxSEX6oS-6xE"

def md_to_html(md):
    # retire frontmatter
    if md.startswith('---'):
        md = md.split('---', 2)[2]
    out = []
    in_ul = False
    in_table = False
    for raw in md.split('\n'):
        line = raw.rstrip()
        # garde le HTML brut (encart, etc.)
        if re.match(r'\s*<', line):
            if in_ul: out.append('</ul>'); in_ul=False
            out.append(line); continue
        # tableaux markdown -> texte dans <p> (Datafer compte le texte)
        if '|' in line and line.strip().startswith('|'):
            if re.match(r'^\s*\|[\s:|-]+\|\s*$', line):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            out.append('<p>' + ' '.join(cells) + '</p>')
            continue
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            if in_ul: out.append('</ul>'); in_ul=False
            lvl = len(m.group(1)); txt = inline(m.group(2))
            out.append(f'<h{lvl}>{txt}</h{lvl}>'); continue
        if re.match(r'^\s*[-*]\s+', line):
            if not in_ul: out.append('<ul>'); in_ul=True
            out.append('<li>'+inline(re.sub(r'^\s*[-*]\s+','',line))+'</li>'); continue
        if in_ul: out.append('</ul>'); in_ul=False
        if line.strip()=='':
            continue
        out.append('<p>'+inline(line)+'</p>')
    if in_ul: out.append('</ul>')
    return '\n'.join(out)

def inline(t):
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', t)
    return t

def main():
    path, bid = sys.argv[1], sys.argv[2]
    md = open(path, encoding='utf-8').read()
    html = md_to_html(md)
    body = json.dumps({"editorHtml": html}).encode()
    req = urllib.request.Request(f"{API}/api/v1/briefs/{bid}/content", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type":"application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.loads(r.read())
    except Exception as e:
        print("ERREUR API:", e); sys.exit(1)
    score = d.get('score'); comp = d.get('competitors') or {}
    best = comp.get('best')
    verdict = "BAT LE CONCURRENT" if (score is not None and best is not None and score >= best) else "INSUFFISANT"
    print(f"score={score} best={best} -> {verdict}")
    bd = d.get('breakdown')
    if bd: print("breakdown:", json.dumps(bd, ensure_ascii=False)[:600])

if __name__ == "__main__":
    main()
