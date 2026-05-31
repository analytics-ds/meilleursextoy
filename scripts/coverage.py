#!/usr/bin/env python3
"""
Score LOCAL de couverture semantique d'un article contre son brief Datafer.
Pas d'appel API (l'endpoint de scoring est rate-limite). Approxime le score Datafer
en mesurant la couverture des targetTerms ponderee par presence/avgCount + le respect du wordcount.

Usage: python3 scripts/coverage.py <chemin_md> <slug>
Le brief est lu dans datafer-briefs/<slug>.json
"""
import sys, json, re, unicodedata, os

def norm(s):
    s = s.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def main():
    path, slug = sys.argv[1], sys.argv[2]
    base = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    # remonter jusqu'au repo
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    brief = json.load(open(os.path.join(repo, 'datafer-briefs', slug + '.json'), encoding='utf-8'))
    md = open(path, encoding='utf-8').read()
    # retire frontmatter
    if md.startswith('---'):
        md = md.split('---', 2)[2]
    text = norm(md)
    words = re.findall(r"[a-z0-9']+", text)
    wc = len(words)
    target_wc = brief.get('targetWordCount') or 0
    terms = brief.get('targetTerms') or []
    best = (brief.get('competitors') or {}).get('best')

    covered = 0
    missing = []
    weight_total = 0.0
    weight_hit = 0.0
    for t in terms:
        term = norm(t['term'])
        presence = t.get('presence', 50) or 50
        w = presence / 100.0
        weight_total += w
        if term in text:
            covered += 1
            weight_hit += w
        else:
            missing.append(t['term'])
    cov_pct = round(100 * covered / max(1, len(terms)))
    weighted_pct = round(100 * weight_hit / max(0.0001, weight_total))
    wc_ratio = round(100 * wc / max(1, target_wc)) if target_wc else 0

    print(f"COUVERTURE termes: {covered}/{len(terms)} ({cov_pct}%) | ponderee: {weighted_pct}%")
    print(f"MOTS: {wc} / cible {target_wc} ({wc_ratio}%)")
    print(f"(score Datafer concurrent a battre: {best})")
    # objectif: couverture ponderee >= 80% ET wordcount entre 95% et 120% de la cible
    ok_cov = weighted_pct >= 80
    ok_wc = target_wc == 0 or (wc >= target_wc * 0.95)
    verdict = "OK" if (ok_cov and ok_wc) else "A ENRICHIR"
    print(f"VERDICT: {verdict}")
    if missing:
        print("TERMES MANQUANTS (" + str(len(missing)) + "): " + ", ".join(missing[:40]))

if __name__ == "__main__":
    main()
