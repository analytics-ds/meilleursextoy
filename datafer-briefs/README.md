# Briefs Datafer (RankShaker) - Meilleur Sextoy

Source KW : `~/Downloads/sextoy_broad-match_fr_2026-06-01.csv` (8 mots-cles, marche FR).
Folder RankShaker : **Meilleur Sextoy** `f11defd3-952e-410b-bc85-044498ab2820` (https://meilleursextoy.com/).
Briefs crees + analyses le 2026-06-01 (tous `ready`, 50 targetTerms chacun). JSON complets dans ce dossier.

## Architecture editoriale (slugs courts)

| Slug | Mot-cle | Vol | Type | Mots cibles | Best a battre | Brief ID |
|---|---|---|---|---|---|---|
| meilleur-sextoy | quel est le meilleur sextoy | 70 | **Pilier** top/comparatif | 2246 | 64 | cd212533-ff61-4d00-87a3-8d9bdc372832 |
| utiliser-sextoy | comment utiliser un sextoy | 260 | Guide | 1533 | 67 | 5328c258-5e35-48ba-ae4f-5d4aa54d6dce |
| choisir-sextoy | quel sextoy choisir | 90 | Guide d'achat | 2076 | 76 | e7d25c77-4d8d-4231-b300-024330c180f4 |
| nettoyer-sextoy | comment nettoyer un sextoy | 70 | Entretien | 1113 | 63 | ce897214-82a7-4663-aa4e-be6859f09719 |
| meilleur-sextoy-femme | quel est le meilleur sextoy pour femme | 30 | Top femme | 2205 | 73 | 9bef3a77-a110-4544-9dc7-5f84d80fc03f |
| meilleur-sextoy-homme | quel est le meilleur sextoy pour homme | 30 | Top homme | 1782 | 71 | 37544e0a-a425-4cb0-b613-92c30ab237d7 |
| fabriquer-sextoy-maison | comment faire un sextoy | 40 | DIY / securite | 1603 | 70 | c0885582-801e-4bd2-a742-4fcbad005334 |
| ou-acheter-sextoy | ou trouver des sextoys | 20 | Ou acheter | 1970 | 66 | 05fbbf55-708f-44d1-bd8a-ba6dbe42df81 |

Chaque `<slug>.json` contient : targetTerms (50), targetWordCount, competitors.best (score a depasser), keyword.

## Maillage interne prevu
- Pilier `meilleur-sextoy` linke vers tous les tops + guides
- `meilleur-sextoy` <-> `meilleur-sextoy-femme` <-> `meilleur-sextoy-homme`
- `choisir-sextoy` -> `meilleur-sextoy`, `utiliser-sextoy`, `ou-acheter-sextoy`
- `utiliser-sextoy` -> `nettoyer-sextoy`, `choisir-sextoy`
- `nettoyer-sextoy` -> `utiliser-sextoy`
- `ou-acheter-sextoy` -> `choisir-sextoy`, `meilleur-sextoy`
- `fabriquer-sextoy-maison` -> `nettoyer-sextoy`, `choisir-sextoy` (angle securite/hygiene corps)

## Process par article
1. Lire le brief (`<slug>.json`) : targetTerms + targetWordCount + best
2. Rediger HTML (encart En bref, tableau, listes a puces, gras strategiques, FAQ H3, maillage 3+ liens)
3. Humaniser (skill sem-humaniser, 19 marqueurs IA bannis) des la redaction
4. Scorer via POST /api/v1/briefs/{id}/content jusqu'a depasser `best`
5. Images (sites marques + ambiance stock) via Playwright
6. Publier dans content/blog/<slug>.md (slug court) + lastmod
