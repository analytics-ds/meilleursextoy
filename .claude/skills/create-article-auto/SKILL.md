# Skill : Creer un article evergreen SEO (full auto)

Cette skill produit **automatiquement** un article evergreen SEO (pas GEO), bilingue FR + EN, a partir d'un mot-cle pris dans la roadmap editoriale du blog. Aucun input humain. Aucun point d'arret. Publication directe sur GitHub.

Elle est destinee a etre declenchee par une routine planifiee (ex: 2x/semaine a 3h du mat via `/schedule`). Elle peut aussi etre lancee manuellement pour tester.

## Quand l'utiliser

- Declenchement automatique via routine planifiee (cron distant).
- Declenchement manuel : `/create-article-auto` dans le contexte d'un blog du reseau PBN GEO datashake.

## Pre-requis dans le blog

- `roadmap.yaml` existe et contient au moins une entree `status: todo`.
- `hugo.toml` configure avec la langue principale + la langue EN.
- `data/authors.yaml` present (systeme d'auteurs partage).
- `content/blog/` existe (peut etre vide pour un premier article).
- Remote git `origin` configure, acces push.
- Cle `CRAZYSERP_API_KEY` exportee par le prompt de la routine (source SERP nominale). Outil `WebSearch` disponible en repli. Si les deux manquent, la skill degrade en mode "kw seul" sans echouer.

## Philosophie : full auto, pas de human in the loop

Aucune question a l'utilisateur. Toutes les decisions sont prises par l'agent a partir de :
- Le mot-cle de la roadmap
- L'analyse SERP via CrazySERP (ou WebSearch en repli, ou le kw seul en mode degrade)
- Le contexte du site (CLAUDE.md du blog, authors.yaml, hugo.toml)
- Les articles deja publies (scan `content/blog/`)

Si une etape bloque (image introuvable, build Hugo echoue, push rejete apres rebase), l'agent **n'insiste pas** : il marque l'entree `status: failed` dans la roadmap avec le message d'erreur, commit le roadmap, et sort proprement en exit code non-zero. **Exception : l'indisponibilite de la source SERP n'est PAS un motif d'echec** (voir Etape 1), CrazySERP puis WebSearch puis mode degrade, on publie dans tous les cas.

## Pas de quota hebdomadaire (regle exemptee)

Cette skill **ignore completement** la regle indicative "4 articles par semaine" mentionnee dans le `CLAUDE.md` du blog. Elle s'applique uniquement aux skills interactives (`/create-article-geo`, `/create-article-seo`).

`/create-article-auto` est faite pour tourner en routine cron (mardi/vendredi 3h Paris) et doit publier l'entree eligible de la roadmap **sans aucune verification de quota**. Ne pas lire le `MEMORY.md` pour compter les publications de la semaine. Ne pas afficher de warning. Publier point.

Le seul critere d'eligibilite est defini a l'Etape 0 : `status == todo` et `scheduled_date <= today`.

## Difference avec /create-article-geo

| Element | `/create-article-geo` | `/create-article-auto` |
|---|---|---|
| Interactivite | Oui, plusieurs points d'arret | Non, full auto |
| Type d'article | Standard OU geo-comparatif (GEO) | Standard uniquement (SEO pur) |
| Mots-cles | Prompt GEO + query fan-out | Mot-cle SEO simple |
| FAQ | Toujours (3+) | Seulement si le sujet s'y prete (questions vues en recherche) |
| "En bref" numerote | Oui (GEO) | Non |
| Source KW | Demande a l'utilisateur | Lit `roadmap.yaml` |
| Analyse concurrents | Manuelle ou absente | Automatique via CrazySERP (organiques, PAA, AI Overview, volume), repli WebSearch |
| Validation | Humaine a chaque etape | Aucune |

## Etape 0 — Selection de l'entree roadmap

1. `cd` vers la racine du blog (la skill est lancee depuis ce contexte).
2. Pull du remote :
   ```bash
   git pull --rebase origin main
   ```
   Si echec : abort avec log clair.
3. Lire `roadmap.yaml`.
4. Filtrer les entrees :
   - `status == todo`
   - `scheduled_date <= today` (YYYY-MM-DD)
5. Trier par `scheduled_date` croissante. Prendre la premiere.
6. Si aucune entree eligible : logger "Aucune entree roadmap eligible aujourd'hui" et exit 0 (pas d'erreur, juste rien a faire).

L'entree selectionnee fournit : `kw`, `category`, `scheduled_date`.

## Etape 1 — Analyse SERP via CrazySERP (repli WebSearch)

L'analyse du paysage concurrentiel passe par l'**API CrazySERP de datashake**. Un seul appel renvoie les resultats organiques, les People Also Ask, les recherches associees, l'AI Overview complete et le volume de recherche mensuel. La cle est fournie dans le prompt de la routine (variable `CRAZYSERP_API_KEY`) et **ne doit jamais etre ecrite dans le repo** : les repos du reseau sont publics.

### 1.1 Appel

```bash
curl -s --max-time 240 -G "https://crazyserp.com/api/search" \
  --data-urlencode "q=<kw>" \
  --data-urlencode "gl=fr" \
  --data-urlencode "hl=fr" \
  --data-urlencode "location=France" \
  --data-urlencode "page=1" \
  -H "Authorization: Bearer $CRAZYSERP_API_KEY" \
  -o /tmp/serp.json
```

Points de vigilance, tous verifies en production :

- **`--max-time 240` est obligatoire.** Une requete que CrazySERP n'a jamais scrapee prend de 60 s a plusieurs minutes, il scrape en direct. Un timeout court perd le credit sans rien recuperer.
- **`location=France` et rien d'autre** pour un ciblage national. Ne jamais ecrire `Paris,France` : ce format resout silencieusement vers `Paris,Ontario,Canada`.
- **Relire `params.location` et `credits_used`** dans la reponse. Ce sont les deux champs qui trahissent un appel parti de travers.
- **Ne pas utiliser `tbm`** (`nws`, `isch`, `vid`) : renvoie 0 resultat tout en debitant un credit.
- Un seul appel par article, `page=1`. Le top 10 suffit pour rediger.

### 1.2 Extraction

```bash
jq '{
  volume:   .volume.yearly_data[0].total_volume,
  aio:      .parsed_data.has_ai_overview,
  aio_txt:  .parsed_data.ai_overview.content,
  organic:  [.parsed_data.organic[]? | {position, title, description, url}],
  paa:      [.parsed_data.people_also_ask[]? | .question],
  related:  [.parsed_data.related[]? | .query],
  snippet:  .parsed_data.featured_snippet,
  stats:    .stats
}' /tmp/serp.json
```

`jq` n'est pas toujours present dans le sandbox : en cas d'absence, faire la meme extraction en `python3`.

### 1.3 Repli en cascade (ne jamais echouer sur cette etape)

**Etat connu au 2026-08-06 : dans l'environnement cloud du reseau, l'egress rejette `crazyserp.com` en 403 quasi immediat (mesure a 0,72 s).** Ce n'est ni un timeout ni un souci de cle, le meme appel passe en 6 s depuis un Mac. La cause est le niveau **"Acces reseau"** de l'environnement, positionne sur "De confiance", une liste blanche curatee qui ne contient pas ce domaine. Tant qu'il n'est pas passe en acces complet, **la routine tourne en repli WebSearch**. En local, CrazySERP fonctionne normalement.

Consequence pratique : tenter CrazySERP quand meme, puis **basculer des le premier echec, sans insister ni retenter**.

1. **CrazySERP repond** : cas nominal.
2. **CrazySERP renvoie 402 (credits insuffisants)** : ne pas basculer silencieusement. Loguer `CRAZYSERP 402 credits epuises`, continuer en repli WebSearch, et le signaler dans le message de commit pour que Damien le voie.
3. **CrazySERP injoignable** (403 de l'egress, timeout, DNS) : basculer sur `WebSearch`, execute cote serveur Anthropic donc non soumis a la politique reseau du sandbox. Maximum 3 recherches sur le `kw`, en exploitant uniquement titres et snippets.
4. **WebSearch aussi indisponible** : mode degrade, analyse a partir du seul `kw`, de la `category` et du contexte editorial du `CLAUDE.md`. **Publier quand meme.**

Noter dans le log et dans la ligne ajoutee a `MEMORY.md` le mode reellement utilise : `crazyserp`, `websearch` ou `degrade`.

### 1.4 Ne pas ouvrir les pages concurrentes

Ne **PAS** utiliser `WebFetch` sur les URLs concurrentes : dans le sandbox cloud les domaines commerciaux sont bloques par la politique reseau (403/503). L'analyse se fait uniquement sur les titres, descriptions, PAA et AI Overview renvoyes par l'API.

### 1.5 Synthese auto (aucun output humain, juste des variables internes)

L'agent determine :

- **Intention de recherche** : inferee du pattern recurrent des titres du top 10 (informationnelle, definitionnelle, comparative, transactionnelle).
- **Angles concurrents** : sous-themes qui reviennent dans les titres et les descriptions (prix, comparatif, avis, guide, duree de vie...).
- **Champ semantique** : termes recurrents, plus `parsed_data.highlights` si present, ce sont les termes que Google met en gras.
- **FAQ pertinente ?** : construire 4 a 6 questions a partir des `people_also_ask`, **toujours reformulees**, jamais copiees mot pour mot. S'il y a moins de 4 PAA, completer avec les `related` transformees en questions. En repli WebSearch ou en mode degrade, juger selon la nature du sujet.
- **Longueur cible** : 1500 a 2000 mots.
- **Tableau pertinent ?** : vrai si le `kw` ou les titres du top contiennent "meilleur", "top", "vs", "ou", "comparatif", "prix", "tarif". Faux sinon.
- **Volume de recherche** : `volume.yearly_data[0].total_volume` est offert dans le meme appel. Purement informatif, il ne change pas la decision de publier.
- **AI Overview** : si `has_ai_overview` est vrai, lire `ai_overview.content`. Les sous-questions qu'elle traite indiquent ce que Google considere comme le noyau du sujet, les couvrir explicitement dans la structure Hn. **Ne jamais recopier le texte de l'AIO.** Noter dans le log `AIO : Declenchee` ou `AIO : Non declenchee`.

## Etape 2 — Title et meta description (regles pixel inline)

Pas d'appel aux skills `/tech-title` ni `/tech-meta-description`. Regles appliquees directement :

### Title
- Contient le `kw` en premier tiers de la balise si possible
- Max 60 caracteres (proxy safe pour 580px en Arial SERP Google)
- Format cible : `[Kw] : [angle] | [Nom du site]`
- Le nom du site vient du `hugo.toml` (`title` global)
- **Une seule option, choix direct** (pas de 3 options comme en interactif)

### Meta description
- Max 155 caracteres (proxy safe pour 920px en Arial SERP)
- Contient le `kw`
- Formule : phrase descriptive factuelle, pas de call-to-action agressif
- 1 phrase, pas de liste, pas de suspense

## Etape 3 — Structure Hn auto

### Regles
- 1 H1 contenant `kw`. Le H1 est genere par Hugo a partir du `title` frontmatter, **pas dans le body**.
- 4 a 7 H2 construits a partir des patterns recurrents identifies a l'etape 1.3. Privilegier les sujets presents chez 3+ concurrents en priorite, puis les 2+, puis combler avec des sujets uniques a fort potentiel.
- 1 a 2 H2 "valeur ajoutee" basee sur l'angle editorial du blog (lu dans `CLAUDE.md` section "Contexte du site" ou section editoriale).
- Si FAQ pertinente : dernier H2 = "Questions frequentes" avec les questions selectionnees a l'etape 1.3, en accordeon `<details><summary>`.
- H3 : 1 a 3 par H2, optionnels, utilises pour les sous-aspects ou les tableaux.

### Contraintes
- Les H2 doivent etre **explicites et auto-suffisants** (lisibles hors contexte).
- Pas de H2 vague ("Introduction", "Conclusion" tels quels — les reformuler).
- Pas de caractere `&` dans les H2/H3.
- Pas de tiret cadratin (—) ni demi-cadratin (–).

## Etape 4 — Selection auto de l'auteur

Identique a la logique de `/create-article-geo` etape 1.3 :

1. Lire `data/authors.yaml`.
2. Pour chaque auteur, compter les matches entre ses `topics`/`expertise` et le `kw` + la `category` de la roadmap.
3. Selectionner l'auteur au score le plus haut.
4. En cas d'egalite ou de score nul : auteur principal du site defini dans CLAUDE.md.

Injecter l'ID-slug dans le frontmatter (`author: [id]`). Meme ID pour FR et EN.

## Etape 5 — Image hero auto

Appeler le script existant :
```bash
bash .claude/scripts/fetch-image.sh "<kw traduit en anglais>" "<slug-fr>" "static/images/blog"
```

- La query image est le `kw` traduit en anglais (Openverse est majoritairement indexe en anglais).
- Si le script renvoie un code non-zero, retenter **une seule fois** avec une query plus generique (la `category` traduite en anglais).
- Si 2e echec : **ne pas marquer `failed`**. Continuer la publication sans image hero (champs `image`, `imageAlt`, `imageCredit` omis du frontmatter ou laisses vides). L'absence d'image n'est pas une raison d'avorter : l'article est publie, le site fonctionne sans hero.
- Recuperer les 3 sorties du script (chemin, alt, credit) pour le frontmatter **uniquement si le script a reussi**.

## Etape 6 — Maillage interne auto

1. Lister tous les `.md` dans `content/blog/` (articles FR uniquement pour cette passe).
2. Lire le frontmatter de chacun : `title`, `kw` (via slug), `categories`, `tags`.
3. Scorer chaque article par proximite avec le nouveau (categorie identique = +3, tags partages = +1 par tag, mots communs entre kw = +2).
4. Garder les 3 a 5 meilleurs scores.
5. Preparer les ancres : chaque ancre contient le mot-cle principal de l'article cible (extrait du slug, reformule en langue naturelle).
6. Positionner les liens de maniere contextuelle dans le body (etape 7) : un par section, pas de bloc "Voir aussi" en fin d'article.

**Maillage intra-langue uniquement** : version FR mail vers `/blog/*`, version EN mail vers `/en/blog/*`.

Si le blog a moins de 3 articles FR publies : faire au mieux avec ce qui existe (2 liens, 1 lien, ou aucun pour le tout premier article). Ne pas bloquer.

## Etape 7 — Redaction FR complete

Produire le fichier `content/blog/[slug-fr].md`.

### Frontmatter
```yaml
---
title: "[Title]"
translationKey: "[slug-generique-identique-FR-et-EN]"
date: "[YYYY-MM-DD]"
lastmod: "[YYYY-MM-DD]"
description: "[Meta description <= 155 car]"
categories: ["[Categorie FR]"]
tags: ["tag1", "tag2", "tag3", "tag4", "tag5"]
author: "[id-slug]"
image: "/images/blog/[slug].webp"
imageAlt: "[Description FR, max 125 car]"
imageCredit: "[Credit retourne par fetch-image.sh]"
faq:  # UNIQUEMENT si FAQ pertinente (voir etape 1.3)
  - question: "[Q1]"
    answer: "[R1, 3-5 phrases]"
  - question: "[Q2]"
    answer: "[R2, 2-4 phrases]"
readingTime: true
---
```

### Body
- Premier paragraphe : contient le `kw` naturellement, pose le contexte.
- Respecter la structure Hn de l'etape 3. Aucune section ajoutee, aucune supprimee.
- Longueur cible : moyenne des concurrents +/- 10% (ex: si moyenne = 1600 mots, viser 1440-1760).
- Densite `kw` naturelle : 1-2%.
- Variations et synonymes du `kw` dans les H2.
- Mots-cles en **gras** quand pertinent.
- Au moins 1 tableau si l'etape 1.3 a note "tableau pertinent".
- Liens internes inseres contextuellement (etape 6).
- Ton impersonnel (pas de je/tu/nous/vous) sauf indication contraire dans le CLAUDE.md du blog.
- Paragraphes aeres, 3-5 phrases max.
- Pas de separateur horizontal (`---`). Pas de tiret cadratin (—) ni demi-cadratin (–).
- Si FAQ pertinente : dernier H2 "Questions frequentes" avec `<details><summary>` accordeon. Les Q/R du body correspondent strictement a celles du frontmatter.

## Etape 8 — Redaction EN (traduction directe)

Produire le fichier `content/en/blog/[slug-en].md`.

- Meme `translationKey` que la version FR (obligatoire pour le hreflang et le language switcher Hugo).
- Traduction **directe** du contenu FR (pas de recherche KW EN extensive, c'est une trad fidele du contenu + du title/meta).
- Adaptation legere : slug EN traduit (pas translitteration), `categories` et `tags` en EN (mapping defini dans CLAUDE.md du blog), `imageAlt` traduit.
- `image` et `imageCredit` identiques au FR.
- Meme `author` que FR (les libelles jobTitle/role/bio sont bilingues dans authors.yaml).
- FAQ frontmatter et body traduits en EN aussi.

## Etape 9 — Build Hugo et verification

### 9.0 Installer Hugo extended (meme version que la prod)

Le sandbox cloud n'a PAS Hugo pre-installe, et `apt` fournit une version trop ancienne (0.123.x) qui fait echouer le build de certains sites du reseau (ex: sites multilingues avec `locale` par langue). Avant de builder, installer la MEME version que le deploiement GitHub Actions du reseau, **Hugo extended v0.161.1** :

```bash
wget -q -O /tmp/hugo.deb https://github.com/gohugoio/hugo/releases/download/v0.161.1/hugo_extended_0.161.1_linux-amd64.deb \
  && (sudo dpkg -i /tmp/hugo.deb 2>/dev/null || { dpkg-deb -x /tmp/hugo.deb /tmp/hugobin && export PATH="/tmp/hugobin/usr/local/bin:$PATH"; })
hugo version   # doit afficher v0.161.1 extended
```

**Repli si le telechargement GitHub echoue (403 proxy / repo hors scope de la session)** : dans le sandbox cloud, l'egress proxy peut bloquer les telechargements directs depuis `github.com/gohugoio/hugo/releases` (repo hors du scope GitHub de la session, non debloquable via `add_repo` car cross-owner). Se rabattre sur le wrapper npm `hugo-extended`, qui recupere le meme binaire a l'installation et passe generalement le proxy (registry npm autorise) :

```bash
mkdir -p /tmp/hugobin-npm && cd /tmp/hugobin-npm && npm init -y >/dev/null 2>&1 && npm install hugo-extended@0.161.1
export PATH="/tmp/hugobin-npm/node_modules/.bin:$PATH"
hugo version   # doit afficher v0.161.1 extended
```

Si les deux methodes echouent, utiliser le `hugo` deja present, mais NE PAS se rabattre sur `apt install hugo` (version cassante). La version prod exacte est dans `.github/workflows/hugo.yml` de chaque blog (champ `hugo_extended_..._linux-amd64.deb`) : s'y referer si elle a change.

### 9.1 Build

```bash
hugo
```

- Si exit code non-zero : marquer `failed` avec log de l'erreur, abort.
- Si OK : noter le nombre de pages generees.

## Etape 10 — Update roadmap et MEMORY.md

### Roadmap
Mettre a jour l'entree traitee dans `roadmap.yaml` :
```yaml
  status: done
  published_date: "[YYYY-MM-DD]"
  published_url_fr: "[baseURL]/blog/[slug-fr]/"
  published_url_en: "[baseURL]/en/blog/[slug-en]/"
  error: null
```

### MEMORY.md
Ajouter une ligne dans la section de la semaine en cours :
```
- YYYY-MM-DD | [Titre FR] (FR+EN) | [Categorie] | auto
```

Le suffixe `auto` distingue les articles generes par cette skill des articles produits a la main via `/create-article-geo`.

## Etape 11 — Commit et push

```bash
git add -A
git commit -m "Auto: publication evergreen - [Titre FR]"
git pull --rebase origin main
git push origin main
```

En cas de rejet du push apres rebase : retenter jusqu'a 3 fois (pull --rebase + push). Si toujours KO au bout de 3 tentatives : marquer failed avec erreur "push rejected 3x", commit du roadmap local, exit non-zero.

## Gestion des echecs (transversal)

A **n'importe quelle etape**, si un blocage survient :
1. Loger le message d'erreur precis (etape + cause).
2. Mettre a jour l'entree de roadmap :
   ```yaml
     status: failed
     error: "[etape] [message d'erreur]"
   ```
3. Si des fichiers article ont ete partiellement ecrits : les supprimer (revenir a l'etat pre-skill) pour ne pas laisser de brouillon dans `content/`.
4. Commit uniquement le `roadmap.yaml` mis a jour, avec message `Auto: roadmap update (failed)`.
5. Push.
6. Exit non-zero.

L'entree `failed` n'est **pas retentee automatiquement** par les lancements suivants de la skill (elle reste en status `failed`). Damien passe manuellement la corriger et la repasser en `todo`.

## Format de `roadmap.yaml`

Voir le fichier `.claude/templates/roadmap-template.yaml` pour le squelette commente.

Structure attendue :
```yaml
articles:
  - kw: "mot cle principal"
    category: "Categorie du blog"
    volume: 1200        # informatif, ignore par l'agent
    kd: 35              # informatif, ignore par l'agent
    scheduled_date: "2026-04-28"
    status: todo
    published_date: null
    published_url_fr: null
    published_url_en: null
    error: null
```

Les champs editables par l'humain :
- `kw`, `category`, `scheduled_date` (obligatoires)
- `volume`, `kd` (informatifs, aident l'humain a prioriser, **ignores par l'agent** — il ne s'en sert pas pour decider quoi que ce soit)
- `status` (pour repasser un `failed` en `todo` apres correction)

Les champs remplis par l'agent : `published_date`, `published_url_fr`, `published_url_en`, `error`, et bascule `status` vers `done` ou `failed`.

## Logs

Tout le deroulement de la skill est ecrit dans `/tmp/create-article-auto-[YYYY-MM-DD-HHMM].log` :
- Mot-cle traite
- URLs concurrents, nombre de mots moyen
- Auteur selectionne et raison
- Image recuperee (chemin, credit)
- Nombre de liens internes places
- Temps total
- Exit code

Creer le dossier `/tmp/` si absent. Conserver les 30 derniers logs (rotation).
