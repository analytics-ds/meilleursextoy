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

## Etape 1 — Analyse semantique via Datafer (repli CrazySERP puis WebSearch)

L'analyse du paysage concurrentiel passe par l'**API Datafer**, l'outil semantique interne de datashake. Un brief Datafer donne ce que l'appel SERP seul ne donnait pas : les **structures Hn completes du top 10**, le **contenu redige** de chaque concurrent, les **termes NLP ponderes** avec leur taux de presence, les **clusters semantiques**, les **sections recurrentes de la SERP**, les **entites nommees**, le **nombre de mots cible** calcule sur les concurrents reels, les **PAA**, et un **score /100** qui permet de mesurer l'article produit avant de le publier.

**Datafer est la source nominale depuis le 2026-09-01.** CrazySERP reste branche pour deux usages precis : le **check AI Overview** (Datafer ne l'expose pas) et le **repli** si Datafer echoue.

Les deux cles sont fournies dans le prompt de la routine (`DATAFER_API_KEY` et `CRAZYSERP_API_KEY`) et **ne doivent jamais etre ecrites dans le repo** : les repos du reseau sont publics. Si le prompt n'en fournit qu'une, la cascade de repli (1.5) s'adapte toute seule et l'article sort quand meme.

### 1.1 Verifier la cle, puis creer le brief Datafer

**Premier reflexe : la cle est-elle la ?**

```bash
if [ -z "$DATAFER_API_KEY" ]; then
  echo "DATAFER_API_KEY absente, mode crazyserp"   # voir 1.5, cas 0
fi
```

Si elle est absente ou vide, **ne pas tenter Datafer du tout** : passer directement au mode `crazyserp` (1.5, cas 0). Ce n'est jamais un motif d'echec. **Au 2026-09-07, les 14 routines du parc portent toutes la cle** : si un run tombe malgre tout dans ce cas 0, ce n'est plus une situation normale mais le signe que son prompt a ete modifie ou restaure depuis, a signaler.

```bash
export BASE="https://datafer.analytics-e0d.workers.dev"
curl -s -w '\nHTTP=%{http_code}\n' --max-time 120 -X POST "$BASE/api/v1/briefs" \
  -H "Authorization: Bearer $DATAFER_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"<kw>","country":"fr"}'
```

Recuperer le champ `.id` de la reponse. `jq` n'est pas toujours present dans le sandbox : faire l'extraction en `python3` en cas d'absence.

**Ne JAMAIS appeler Datafer avec `urllib` de Python.** Cloudflare rejette la signature `Python-urllib` en **403 `error code: 1010`**, et ce n'est ni la cle ni l'egress. Tout passe par `curl` (mesure du 2026-09-01 : le meme appel echoue en urllib et repond 200 en curl).

### 1.2 Poller jusqu'a `ready`

```bash
for i in $(seq 1 48); do
  STATUS=$(curl -s --max-time 30 "$BASE/api/v1/briefs/$ID" \
    -H "Authorization: Bearer $DATAFER_API_KEY" \
    | python3 -c 'import json,sys;print(json.load(sys.stdin).get("status",""))')
  [ "$STATUS" = "ready" ] && break
  [ "$STATUS" = "failed" ] && break
  sleep 5
done
```

- **Timeout 240 s, pas 90 s.** Mesures du 2026-09-01 : 31 s depuis le sandbox cloud, 89 s depuis un Mac sur un mot-cle jamais analyse. La doc annonce 20 a 60 s, c'est optimiste.
- Les endpoints v2 renvoient **409** tant que le brief est `pending` : ne jamais les appeler avant `ready`.
- `status: failed` cote Datafer signifie que son analyse SERP initiale a echoue : basculer sur le repli (1.5) sans insister.

### 1.3 Rapatrier les 4 endpoints v2

Une fois `ready`, quatre appels, tous sous la seconde (mesure du 2026-09-01) :

```bash
for EP in "" "/competitors" "/nlp" "/paa"; do
  curl -s --max-time 60 "$BASE/api/v2/briefs/$ID$EP" \
    -H "Authorization: Bearer $DATAFER_API_KEY" \
    -o "/tmp/datafer$(echo "$EP" | tr -d '/' | sed 's/^$/brief/').json"
done
```

Ce qu'on garde de chacun :

| Endpoint | Ce qu'on en tire | Sert a |
|---|---|---|
| `/api/v2/briefs/{id}` | `intent`, `targetWordCount`, `minWordCount`, `maxWordCount`, `avgHeadings`, `avgParagraphs`, `competitors.avg`, `competitors.best` | longueur cible (etape 7), nombre de Hn (etape 3), barre a battre (etape 8bis) |
| `/competitors` | par concurrent : `position`, `title`, `link`, `wordCount`, `headings`, `h1`, `h2`, `h3`, `outline`, `score`, `hasContent` | structure Hn (etape 3), angles reellement traites |
| `/nlp` | `nlpTerms`, `semanticClusters`, `sections`, `entities`, `opportunities`, `stats` | couverture semantique (etape 7), regroupement des H2, differenciation |
| `/paa` | `paa` (question, snippet) | FAQ (etape 3 et 7) |

**Formes reelles a connaitre, la doc `doc-datafer-api` etait fausse sur deux champs** (verifie le 2026-09-01) :

- `sections` : `{label, hits, total, sampleHeadings, keyTerms}` et **pas** `{title, frequency}`. `hits` sur `total` est le nombre de concurrents qui traitent ce sujet, c'est le signal le plus utile de tout le brief.
- `entities` : `{label, hits, total, totalOccurrences}` et **pas** `{name, type, frequency}`.
- `opportunities` peut etre une **liste vide**, c'est frequent. Ne jamais faire dependre une etape de sa presence.
- `sections` et `entities` varient enormement d'un mot-cle a l'autre (mesure : 12 sections et 10 entites sur un mot-cle SIRH, 1 section et 2 entites sur un mot-cle mode). Un compteur bas n'est pas une panne, c'est une SERP pauvre : continuer avec ce qu'il y a.
- `volume` (issu de Haloscan) est souvent absent ou absurde (9 sur un mot-cle a fort trafic). **Purement informatif, il ne conditionne rien.**

### 1.4 Check AI Overview via CrazySERP (1 credit, non bloquant)

Datafer n'expose pas l'AI Overview. Un appel CrazySERP la donne, et c'est une regle transverse datashake sur tout brief et toute redaction.

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

- Lire `stats.has_ai_overview` **en priorite**, avec repli sur `parsed_data.has_ai_overview` : le champ existe aux deux endroits, et le lire seulement dans `parsed_data` a deja renvoye `None` a tort.
- Si `true`, lire `parsed_data.ai_overview.content` : les sous-questions traitees indiquent ce que Google considere comme le noyau du sujet, les couvrir explicitement dans la structure Hn. **Ne jamais recopier le texte de l'AIO.**
- Noter dans le log `AIO : Declenchee` ou `AIO : Non declenchee`.
- **Cet appel n'est jamais bloquant.** S'il echoue, noter `AIO : non verifiee` et continuer. La reponse sert aussi de repli SERP gratuit si Datafer est tombe (1.5).
- `--max-time 240` est obligatoire, `location=France` et rien d'autre (`Paris,France` resout silencieusement vers `Paris,Ontario,Canada`), pas de `tbm` (0 resultat et 1 credit debite quand meme).

### 1.5 Repli en cascade (ne jamais echouer sur cette etape)

**Datafer et CrazySERP sont tous les deux verifies fonctionnels depuis l'environnement cloud du reseau** (mesure du 2026-09-01 depuis `env_01WaB3uJJef85yE35Ha5rLdN` : Datafer creation 200 en 2,7 s, `ready` en 31 s, les 4 endpoints v2 en 200 ; CrazySERP 200 en 2,7 s, AIO detectee, 1 credit).

Bascule **des le premier echec, sans insister ni retenter** :

0. **`DATAFER_API_KEY` absente ou vide** : ne pas appeler Datafer, passer directement en mode `crazyserp` et loguer `DATAFER_API_KEY absente, mode crazyserp`. **Cas a connaitre** : les routines du parc mises en pause portent encore un prompt CrazySERP seul, donc une routine simplement reactivee par `{"enabled": true}` tourne sans cle Datafer. Le run publie quand meme, proprement, en mode degrade d'un cran. Pour recuperer le mode `datafer`, il faut patcher son prompt, ce que fait la skill `geo-pbn-routine-setup`.
1. **Datafer repond** : cas nominal, mode `datafer`.
2. **Datafer en erreur** (creation non-200, `status: failed`, timeout de polling, 409 persistant) : passer en mode `crazyserp` et travailler sur l'appel de 1.4, qui est deja fait. On perd les structures Hn concurrentes, les termes NLP et le nombre de mots cible ; on garde organiques, PAA, recherches associees et AIO. Loguer `DATAFER indisponible, repli crazyserp` et le signaler dans le message de commit.
3. **Datafer et CrazySERP tous les deux injoignables** : mode `websearch`, 3 recherches maximum sur le `kw`, titres et snippets uniquement.
4. **WebSearch aussi indisponible** : mode `degrade`, analyse a partir du seul `kw`, de la `category` et du contexte editorial du `CLAUDE.md`. **Publier quand meme.**

Cas particuliers a loguer explicitement, sans changer de mode :
- CrazySERP **402** (credits epuises) : loguer `CRAZYSERP 402 credits epuises`, l'AIO passe en `non verifiee`, Datafer continue normalement.
- Datafer **401** : cle revoquee, loguer `DATAFER 401 cle invalide` et passer en repli.
- Datafer **403 `error code: 1010`** : c'est un appel parti en urllib, pas une panne. Refaire en curl.

**L'indisponibilite des sources n'est JAMAIS un motif d'echec de la skill.** Noter dans le log et dans la ligne ajoutee a `MEMORY.md` le mode reellement utilise : `datafer`, `crazyserp`, `websearch` ou `degrade`.

### 1.6 Ne pas ouvrir les pages concurrentes

Ne **PAS** utiliser `WebFetch` sur les URLs concurrentes : dans le sandbox cloud les domaines commerciaux sont bloques par la politique reseau (403/503). **C'est desormais inutile** : Datafer a deja crawle le top 10 et rend le contenu par `/competitors/{n}` (champs `text` et `structuredHtml`) pour les concurrents dont `hasContent` est `true`. Appeler cet endpoint sur les 2 ou 3 meilleurs scores quand la structure demande a etre precisee, jamais sur les 10.

En repli `crazyserp`, `websearch` ou `degrade`, l'analyse se fait uniquement sur les titres, descriptions, PAA et AI Overview.

### 1.7 Synthese auto (aucun output humain, juste des variables internes)

L'agent determine :

- **Intention de recherche** : `intent` du brief Datafer (`informational`, `commercial`, `transactional`, `navigational`). En repli, inferee du pattern recurrent des titres du top 10.
- **Sujets a couvrir obligatoirement** : les `sections` dont `hits / total >= 0,5`, c'est-a-dire les sujets traites par au moins la moitie du top 10. `sampleHeadings` donne la formulation reelle des concurrents, a reformuler et jamais a recopier.
- **Angles de differenciation** : les `opportunities` (questions PAA peu couvertes) si la liste n'est pas vide, plus les `sections` a `hits` faible qui restent pertinentes pour le sujet, plus l'angle editorial propre au blog.
- **Champ semantique** : les `nlpTerms` tries par `score` decroissant. Retenir ceux dont `presence >= 50` (present chez au moins la moitie des concurrents). **Nettoyer la liste** : les `nlpTerms` remontent regulierement des noms de marques concurrentes et du bruit de listing (mesure du 2026-09-01 : `jouroff` en 8e position sur un mot-cle SIRH). Ne jamais placer une marque concurrente dans un Hn.
- **Termes a placer dans les Hn** : ceux dont `inHeadings` est `true`, ce sont ceux que les concurrents mettent eux-memes en titre.
- **Regroupement des H2** : les `semanticClusters` (`label` + `terms`) donnent des familles de sujets pretes a devenir des H2.
- **Entites a mentionner** : les `entities` a `hits` eleve, en excluant les marques concurrentes directes du blog.
- **FAQ pertinente ?** : construire 4 a 6 questions a partir des `paa`, **toujours reformulees**, jamais copiees mot pour mot. Completer avec les `opportunities` si besoin. S'il y a moins de 4 PAA, completer avec les `related` de l'appel CrazySERP transformees en questions. En repli `websearch` ou `degrade`, juger selon la nature du sujet.
- **Longueur cible** : `targetWordCount` du brief, borne par `minWordCount` et `maxWordCount`. Detail et garde-fous a l'etape 7.
- **Nombre de Hn cible** : `avgHeadings` du brief, borne entre 6 et 14.
- **Tableau pertinent ?** : vrai si le `kw` ou les titres du top contiennent "meilleur", "top", "vs", "ou", "comparatif", "prix", "tarif", ou si `intent` vaut `commercial`. Faux sinon.
- **Barre de score a battre** : `competitors.avg` et `competitors.best` du brief. Sert a l'etape 8bis.
- **Volume de recherche** : informatif, ne change pas la decision de publier.
- **AI Overview** : voir 1.4.

## Etape 2 — Title et meta description (regles pixel inline)

Pas d'appel aux skills `/tech-title` ni `/tech-meta-description`. Regles appliquees directement :

### Title

**NE JAMAIS ecrire le nom du site dans le `title` du frontmatter.** Le theme l'ajoute deja tout seul : `themes/lusty/layouts/_default/baseof.html` rend `{{ .Title }} | {{ .Site.Title }}`. Mettre le suffixe dans le frontmatter le fait sortir **deux fois** dans la balise, et comme le H1 est construit sur `.Title` a defaut de `.Params.h1`, le nom du site se retrouve aussi **dans le H1**. Defaut constate et corrige sur `meilleur-logiciel-sirh.com` le 2026-08-11 (16 articles) et sur `magazine-como` le 2026-09-01 (4 pages).

- Format du frontmatter : `[Kw] : [angle]`, **sans nom de site, sans separateur final**
- Contient le `kw` en debut de title
- **Le budget de 60 caracteres porte sur le title RENDU**, donc frontmatter + suffixe ajoute par le theme. `hugo.toml` declare un `title` par langue :

| Langue | `Site.Title` | Suffixe ajoute | Max pour le frontmatter |
|---|---|---|---|
| fr | Meilleur Sextoy | ` \| Meilleur Sextoy` (18) | **42** |
| en | Best Sextoy | ` \| Best Sextoy` (14) | **46** |

- Controle avant de continuer : `python3 -c "print(len('<title frontmatter>') + <longueur du suffixe>)"` doit donner 60 au maximum. Si ca depasse, raccourcir l'angle, jamais le `kw`.
- **Une seule option, choix direct** (pas de 3 options comme en interactif)
- Meme regle pour la traduction EN et pour toute autre langue produite.

### Meta description
- Max 155 caracteres (proxy safe pour 920px en Arial SERP)
- Contient le `kw`
- Formule : phrase descriptive factuelle, pas de call-to-action agressif
- 1 phrase, pas de liste, pas de suspense

## Etape 3 — Structure Hn auto

### Regles
- 1 H1 contenant `kw`. Le H1 est genere par Hugo a partir du `title` frontmatter, **pas dans le body**.
- 4 a 7 H2 construits a partir des patterns recurrents identifies a l'etape 1.7. Privilegier les sujets presents chez 3+ concurrents en priorite, puis les 2+, puis combler avec des sujets uniques a fort potentiel.
- 1 a 2 H2 "valeur ajoutee" basee sur l'angle editorial du blog (lu dans `CLAUDE.md` section "Contexte du site" ou section editoriale).
- Si FAQ pertinente : dernier H2 = "Questions frequentes" avec les questions selectionnees a l'etape 1.7, en accordeon `<details><summary>`.
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

> **Cascade des sources d'image, revue le 2026-09-04.** Le script `.claude/scripts/fetch-image.sh`
> essaie dans cet ordre : **Pexels**, puis **Unsplash**, puis **Openverse**, puis un visuel de
> charte genere en local par `.claude/scripts/make-placeholder.py`. Il ne rend jamais la main
> sans visuel. **Openverse n'est plus la source nominale, il est le dernier recours** : mesure
> sur les 45 heros de journal-marketing, il n'avait produit que 15 photos pertinentes, contre
> 10 franchement hors sujet, 15 generiques et 5 degrades de secours, et il sert aussi des URLs
> mortes. Les cles `PEXELS_API_KEY` et `UNSPLASH_ACCESS_KEY` viennent du **prompt de la routine**
> ou du `.env` local, **jamais du repo** : les repos du reseau sont publics. Sans cle, la cascade
> demarre a Openverse et l'article sort quand meme. Le script tient un registre
> `.claude/hero-sources.json` qui **empeche deux articles de porter la meme photo**.
> **Le controle visuel de l'image reste obligatoire avant publication, quelle que soit la banque.**



Appeler le script existant :
```bash
bash .claude/scripts/fetch-image.sh "<kw traduit en anglais>" "<slug-fr>" "static/images/blog"
```

- La query image est le `kw` traduit en anglais (les trois banques sont majoritairement indexees en anglais).
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
faq:  # UNIQUEMENT si FAQ pertinente (voir etape 1.7)
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
- Au moins 1 tableau si l'etape 1.7 a note "tableau pertinent".
- Liens internes inseres contextuellement (etape 6).
- Ton impersonnel (pas de je/tu/nous/vous) sauf indication contraire dans le CLAUDE.md du blog.
- Paragraphes aeres, 3-5 phrases max.
- Pas de separateur horizontal (`---`). Pas de tiret cadratin (—) ni demi-cadratin (–).
- Si FAQ pertinente : dernier H2 "Questions frequentes" avec `<details><summary>` accordeon. Les Q/R du body correspondent strictement a celles du frontmatter.

## Etape 7bis — Controle de score Datafer (non bloquant, une seule passe)

Uniquement si le mode retenu a l'etape 1.5 est `datafer`. Dans les autres modes, sauter cette etape.

Le brief cree a l'etape 1 sait scorer un contenu sur les memes criteres que les concurrents. On mesure l'article **avant** de le traduire et de le publier, pour corriger une fois si besoin.

### 7bis.1 Soumettre le contenu

`POST /api/v1/briefs/{id}/content` n'accepte que `<h1>`, `<h2>`, `<h3>` et `<p>`. Convertir le body FR : le `title` du frontmatter devient le `<h1>`, les `##` et `###` deviennent `<h2>` et `<h3>`, chaque paragraphe devient un `<p>`. Les tableaux, les listes et les accordeons `<details>` sont aplatis en `<p>`, les questions de FAQ en `<h3>` suivies de leur reponse en `<p>`. Les liens sont conserves en texte.

```bash
python3 - <<'PY' > /tmp/editor.json
# construire {"editorHtml": "..."} depuis content/fr/blog/<slug>.md
PY
curl -s --max-time 120 -X POST "$BASE/api/v1/briefs/$ID/content" \
  -H "Authorization: Bearer $DATAFER_API_KEY" \
  -H 'Content-Type: application/json' \
  --data @/tmp/editor.json
```

### 7bis.2 Lire le verdict

De la reponse, retenir `total`, `seoTotal`, `geoTotal`, le `breakdown` par critere (`keyword`, `nlpCoverage`, `contentLength`, `headings`, `placement`, `structure`, `quality`, `geo`) et `competitors.avg` / `competitors.best`.

**La barre est `competitors.avg`.** Un article du reseau qui sort en dessous de la moyenne du top 10 n'a pas de raison de passer devant.

### 7bis.3 Une passe d'enrichissement, jamais deux

Si `total >= competitors.avg` : ne rien changer, loguer le score, passer a l'etape 8.

Si `total < competitors.avg` : prendre les **deux criteres du `breakdown` les plus loin de leur `max`** et corriger uniquement ceux-la, dans le contenu existant, sans casser la structure validee a l'etape 3 :

- `nlpCoverage` faible : placer naturellement les `nlpTerms` a `presence >= 50` encore absents, en priorite ceux dont `inHeadings` est `true`. Jamais de bourrage, jamais une marque concurrente.
- `contentLength` faible : etoffer les sections les plus courtes jusqu'a atteindre `minWordCount` au minimum, en apportant du fond, pas du remplissage.
- `headings` faible : ajouter un H2 ou un H3 sur une `section` a fort `hits` non encore couverte.
- `structure` ou `placement` faible : replacer le `kw` dans le premier paragraphe et dans un H2, aerer les paragraphes trop longs.
- `quality` faible : casser les phrases trop longues, retirer les formulations creuses.

Puis **rescorer une seule fois** et loguer les deux scores. **On s'arrete la, quel que soit le second score.** Pas de troisieme passe : la routine a un creneau de publication a tenir, et un article legerement sous la moyenne publie vaut mieux qu'une boucle d'optimisation qui mange le run.

### 7bis.4 Ne jamais echouer sur cette etape

Un `409`, un `400 editorHtml required`, un timeout ou une reponse illisible se loguent en `SCORE : non mesure` et n'empechent ni la traduction ni la publication. Cette etape est un controle qualite, pas une condition de publication.

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
- YYYY-MM-DD | [Titre FR] (FR+EN) | [Categorie] | auto | mode: [datafer|crazyserp|websearch|degrade] | score: [total]/[competitors.avg]
```

Le suffixe `auto` distingue les articles generes par cette skill des articles produits a la main via `/create-article-geo`.

## Etape 11 — Commit et push

```bash
git add -A
git commit -m "Auto: publication evergreen - [Titre FR] (mode: [datafer|crazyserp|websearch|degrade], score: [total]/[avg])"
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
