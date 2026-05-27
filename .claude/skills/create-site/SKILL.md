# Skill : Creer un site

Ce skill genere un site Hugo complet a partir des reponses de l'utilisateur.

## Declenchement

L'utilisateur tape `/create-site` ou demande de creer un nouveau site.

## Etape 1 — Collecter les informations

Poser les questions suivantes a l'utilisateur. Attendre ses reponses avant de continuer.

### Questions obligatoires

1. **Nom du site** : Comment s'appelle le site ? (ex: "Mamie-The", "Mon Blog Voyage")
2. **Description courte** : En une phrase, de quoi parle le site ? (ex: "Un blog sur l'univers du the")
3. **Categories du blog** : Quelles sont les grandes categories d'articles ? (ex: "Thes verts, Thes noirs, Tisanes, Rituels et Conseils")
   - **IMPORTANT :** Ne JAMAIS utiliser le caractere `&` dans les noms de categories. Toujours le remplacer par "et". Hugo supprime le `&` lors de la generation du slug URL mais laisse un double espace, ce qui cree un double tiret `--` dans l'URL. Les liens du menu pointent vers un slug avec un seul tiret → 404. Si l'utilisateur propose un nom avec `&`, le remplacer automatiquement par "et".
4. **Charte graphique** : Deux options :
   - L'utilisateur fournit un screenshot ou une URL de reference → s'en inspirer
   - L'utilisateur decrit l'ambiance → proposer une palette de couleurs adaptee
5. **Langue principale** : Francais (fr), Anglais (en), autre ?

### Questions optionnelles

6. **Domaine cible** : Y a-t-il deja un nom de domaine prevu ? (pour configurer le baseURL)
7. **Logo** : Y a-t-il un logo a integrer ?
8. **Pages supplementaires** : Au-dela du blog, faut-il des pages statiques ? (A propos, Contact, etc.)
9. **Design Figma** : As-tu un design Figma (URL ou code HTML exporte) a utiliser comme base pour le layout du site ?
   - Si oui, recuperer le code via le MCP Figma (`get_design_context`) ou demander a l'utilisateur de coller le HTML exporte
   - Ce HTML servira de **reference visuelle et structurelle** a l'etape 4 pour creer les templates Hugo

## Etape 2 — Scaffolder Hugo et nettoyer les fichiers par defaut

Une fois les reponses collectees :

```bash
hugo new site . --force
hugo new theme [nom-du-theme-en-slug]
```

Le `--force` permet de scaffolder dans le repertoire courant (qui contient deja `.claude/`).

**IMPORTANT — Nettoyage obligatoire apres le scaffold :**

La commande `hugo new theme` genere des fichiers par defaut (templates quasi vides, config parasite) qui **entrent en conflit** avec nos templates custom. Il faut les supprimer AVANT de copier nos fichiers.

```bash
# Supprimer TOUS les layouts par defaut generes par le scaffold
rm -rf themes/[nom-du-theme]/layouts/*
rm -rf themes/[nom-du-theme]/assets/*

# Supprimer le hugo.toml du theme (il interfere avec le hugo.toml principal)
rm -f themes/[nom-du-theme]/hugo.toml

# Supprimer le archetype par defaut du theme (on utilise celui a la racine)
rm -f themes/[nom-du-theme]/archetypes/default.md
```

Apres ce nettoyage, le dossier du theme doit etre quasiment vide. On va le remplir avec nos propres fichiers a l'etape 4.

**Pourquoi :** Hugo a un systeme de priorite pour les templates. Si un fichier `index.html` existe dans le theme, il prend la priorite sur notre `home.html`. Si le `hugo.toml` du theme existe, il peut ecraser des parametres du `hugo.toml` principal. Le nettoyage elimine toute ambiguite.

## Etape 3 — Configurer hugo.toml

Creer le fichier `hugo.toml` **a la racine du projet** (PAS dans le theme) avec :

- `baseURL` : si domaine custom fourni, l'utiliser. Sinon, utiliser `https://USERNAME.github.io/NOM-DU-REPO/`
- `languageCode` : selon la langue choisie
- `title` : le nom du site
- `theme` : le slug du theme cree
- `[taxonomies]` : category + tag
- `[[menus.main]]` : Accueil + chaque categorie + Le Blog
- `[params]` : description du site, couleurs, nom du theme

**Note :** Il ne doit y avoir qu'UN SEUL `hugo.toml`, a la racine. Jamais dans le dossier du theme.

## Etape 4 — Creer le theme

Recreer la structure de dossiers dans le theme nettoye :

```bash
mkdir -p themes/[nom-du-theme]/layouts/_default
mkdir -p themes/[nom-du-theme]/layouts/partials
mkdir -p themes/[nom-du-theme]/assets/css
```

Lire les templates dans `.claude/templates/` et les adapter avec les informations de l'utilisateur.

### Si un design Figma a ete fourni (etape 1, question 9)

Le HTML Figma sert de **reference visuelle** pour la creation des templates Hugo. Le workflow est :

1. **Analyser le HTML Figma** : identifier la structure (header, footer, grille, typographie, couleurs, espacement)
2. **Extraire les styles** : couleurs, polices, tailles, spacings → les reporter dans les variables CSS de `main.css`
3. **Traduire la structure en templates Hugo** : adapter le HTML statique de Figma en templates dynamiques Hugo en remplacant le contenu statique par les variables Hugo (`{{ .Title }}`, `{{ .Content }}`, `{{ range }}`, etc.)
4. **Ne PAS copier le HTML Figma tel quel** : il faut le decomposer en `baseof.html`, `header.html`, `footer.html`, `home.html`, `single.html`, `list.html` selon la logique Hugo

Les templates dans `.claude/templates/layouts/` servent toujours de **base structurelle** (variables Hugo, boucles, logique conditionnelle). Le design Figma vient **habiller** cette base.

Si aucun design Figma n'a ete fourni, utiliser les templates tels quels avec les couleurs/polices choisies par l'utilisateur.

### CSS (main.css)

Lire `.claude/templates/main.css`, remplacer les variables CSS custom properties avec les couleurs choisies, puis ecrire le resultat dans `themes/[nom-du-theme]/assets/css/main.css` :

- `--primary` : couleur principale
- `--primary-light` : variante claire de la couleur principale
- `--background` : couleur de fond
- `--background-alt` : variante du fond (sections alternees)
- `--accent` : couleur d'accent
- `--cta` : couleur des boutons/CTA
- `--cta-hover` : couleur hover des boutons
- `--text` : couleur du texte
- `--text-light` : couleur du texte secondaire
- `--border` : couleur des bordures

Choisir les polices Google Fonts adaptees a l'univers du site et mettre a jour les variables `--font-heading`, `--font-body`, `--font-ui` :
- Police titres : serif bold (Playfair Display, Merriweather, Lora...)
- Police corps : serif lisible (Lora, Source Serif Pro, Libre Baskerville...)
- Police UI : sans-serif (Inter, DM Sans, Work Sans...)

### Layouts

Lire chaque template depuis `.claude/templates/layouts/` et `.claude/templates/partials/`, les adapter, puis les ecrire aux bons emplacements :

| Source (template) | Destination (theme) |
|-------------------|-------------------|
| `.claude/templates/layouts/baseof.html` | `themes/[theme]/layouts/_default/baseof.html` |
| `.claude/templates/layouts/home.html` | `themes/[theme]/layouts/_default/home.html` |
| `.claude/templates/layouts/list.html` | `themes/[theme]/layouts/_default/list.html` |
| `.claude/templates/layouts/single.html` | `themes/[theme]/layouts/_default/single.html` |
| `.claude/templates/layouts/sitemap-html.html` | `themes/[theme]/layouts/_default/sitemap-html.html` |
| `.claude/templates/partials/header.html` | `themes/[theme]/layouts/partials/header.html` |
| `.claude/templates/partials/footer.html` | `themes/[theme]/layouts/partials/footer.html` |
| `.claude/templates/partials/seo-head.html` | `themes/[theme]/layouts/partials/seo-head.html` |

**IMPORTANT :** Le fichier `home.html` doit etre place dans `layouts/_default/home.html`. NE PAS creer de fichier `index.html` dans `layouts/` — cela causerait un conflit de priorite avec Hugo.

Adapter dans chaque fichier :
- Le contenu du hero de la homepage (titre, description, badge, CTA)
- Les URLs des polices Google Fonts dans baseof.html
- Le footer (nom du site, description)

### SEO Head partial
Le partial `seo-head.html` genere automatiquement :
- Balise canonical
- Open Graph (og:title, og:description, og:type, og:url, og:image)
- Twitter Card
- JSON-LD (schema.org) pour les articles de blog (BlogPosting)

## Etape 5 — Creer le contenu initial

### Page d'accueil
Creer `content/_index.md` avec le frontmatter du site.

### Page liste blog
Creer `content/blog/_index.md`.

### Page plan du site (sitemap HTML)
Creer `content/plan-du-site.md` :
```markdown
---
title: "Plan du site"
layout: "sitemap-html"
description: "Retrouvez toutes les pages et articles de [NOM DU SITE]"
---
```

### Articles placeholder
Creer 2-3 articles placeholder dans chaque categorie pour que le site ne soit pas vide au lancement. Les articles doivent etre courts (300-500 mots) mais correctement structures (frontmatter complet avec `date` ET `lastmod`, H2/H3, un tableau ou une liste). Marquer `draft: false`.

## Etape 6 — Fichiers SEO techniques

Lancer le skill `/seo-setup` pour generer :
- `static/robots.txt`
- `static/llms.txt`
- Configuration du sitemap XML dans `hugo.toml`
- Sitemap HTML (layout + page de contenu deja crees aux etapes 4 et 5)
- Le partial `seo-head.html` est deja dans le theme

## Etape 7 — Configurer le deploiement

Copier `.claude/templates/hugo-workflow.yml` vers `.github/workflows/hugo.yml`.

Creer le `.gitignore` :
```
public/
resources/
.hugo_build.lock
.DS_Store
```

## Etape 8 — Mettre a jour le CLAUDE.md

Remplir la section "Contexte du site" du CLAUDE.md avec toutes les informations collectees :
- Nom du site
- Description
- URL (GitHub Pages ou domaine custom)
- Couleurs (codes hex)
- Polices choisies
- Categories
- Langue
- Auteur (nom complet)
- URL auteur (site ou profil LinkedIn)
- Fonction auteur (ex: "Redacteur", "Expert en X")

## Etape 9 — Build de verification

```bash
hugo
```

Verifier qu'il n'y a aucune erreur. Afficher le nombre de pages generees.

Proposer a l'utilisateur de lancer le serveur local pour voir le resultat :
```bash
hugo server
```

## Etape 10 — Recapitulatif

Afficher a l'utilisateur :
- Le resume de ce qui a ete cree (nombre de fichiers, articles, categories)
- L'URL locale pour voir le site (`http://localhost:1313/`)
- Les prochaines etapes (push sur GitHub, activer GitHub Pages)
- Comment creer de nouveaux articles (`/create-article`)
