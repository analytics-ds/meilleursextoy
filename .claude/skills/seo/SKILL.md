# Skill : Mode SEO

Ce skill active un mode conversationnel pour effectuer des modifications SEO techniques sur le site.

## Declenchement

L'utilisateur tape `/seo` ou demande de modifier/ajouter des elements SEO.

## Comportement

Ce skill n'est PAS un workflow lineaire comme les autres. C'est un mode interactif :

1. Claude lit l'etat actuel du site (hugo.toml, templates, fichiers SEO existants)
2. Claude demande a l'utilisateur ce qu'il veut faire
3. Claude execute la modification
4. Claude reste en mode SEO pour d'autres demandes

## Actions possibles

### Fichiers SEO techniques

| Action | Fichiers concernes |
|--------|-------------------|
| Creer/modifier robots.txt | `static/robots.txt` |
| Creer/modifier llms.txt | `static/llms.txt` — lire le template dans `.claude/templates/seo/robots.txt` et `.claude/templates/seo/llms.txt` |
| Configurer le sitemap | `hugo.toml` section `[sitemap]` |
| Configurer le RSS | `hugo.toml` section `[outputs]` |

### Meta tags et balises

| Action | Fichiers concernes |
|--------|-------------------|
| Modifier les meta tags | `themes/[theme]/layouts/partials/seo-head.html` |
| Ajouter Open Graph / Twitter Card | `themes/[theme]/layouts/partials/seo-head.html` |
| Modifier la balise canonical | `themes/[theme]/layouts/partials/seo-head.html` |
| Ajouter des hreflang (multilingue) | `themes/[theme]/layouts/partials/seo-head.html` |

### Donnees structurees (JSON-LD)

Les schemas disponibles sont dans `.claude/templates/seo/structured-data/`. Pour ajouter un nouveau schema :

1. Lire le template JSON-LD dans `.claude/templates/seo/structured-data/`
2. L'adapter avec les donnees du site
3. L'integrer dans `seo-head.html` avec les conditions Hugo appropriees

**Schemas disponibles par defaut :**

| Schema | Fichier template | Utilise sur |
|--------|-----------------|-------------|
| BlogPosting | `article.json` | Pages articles (`single.html`) |
| Organization | `organization.json` | Toutes les pages |
| Person (auteur) | `author.json` | Pages articles |
| FAQPage | `faq.json` | Articles avec section FAQ |
| BreadcrumbList | `breadcrumb.json` | Toutes les pages sauf accueil |
| WebSite | `website.json` | Page d'accueil uniquement |

**Pour ajouter un schema custom :** l'utilisateur peut creer un fichier `.json` dans `.claude/templates/seo/structured-data/` puis demander via `/seo` de l'integrer. Claude lit le fichier et l'ajoute au partial `seo-head.html`.

### Optimisations on-page

| Action | Description |
|--------|------------|
| Auditer un article | Verifier la structure Hn, la densite de mots-cles, les meta tags, les liens internes |
| Optimiser les images | Verifier les attributs alt, title, les formats, le lazy loading |
| Verifier le maillage interne | Lister les articles et identifier les opportunites de liens manquants |
| Ajouter des breadcrumbs | Integrer un fil d'Ariane avec schema BreadcrumbList |

### Configuration Hugo liee au SEO

| Action | Detail |
|--------|--------|
| Ajouter une redirection | Via `aliases` dans le frontmatter d'un article |
| Modifier les URLs | Configurer `[permalinks]` dans `hugo.toml` |
| Ajouter un fichier custom | Creer dans `static/` (ex: ads.txt, security.txt) |
| Configurer noindex | Via frontmatter ou meta tag conditionnel |

## Regles

- Toujours lire l'etat actuel du fichier avant de le modifier (ne jamais ecraser sans verifier)
- Toujours expliquer a l'utilisateur ce qui va etre modifie et pourquoi
- Proposer un build de verification apres chaque modification (`hugo`)
- Si une modification impacte plusieurs fichiers, les lister avant d'agir
- Les templates dans `.claude/templates/seo/` font reference. Si l'utilisateur a modifie un template, utiliser sa version.

## Sortie du mode

L'utilisateur sort du mode SEO en changeant de sujet ou en demandant autre chose. Pas besoin de commande explicite de sortie.
