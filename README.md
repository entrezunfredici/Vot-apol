# Voteapol

Explorateur public des scrutins de l'Assemblée nationale (XVIIe législature) : retrouver un vote, voir comment chaque groupe politique a voté, et remonter à la source officielle.

> **Statut : conception.** Aucun code n'est encore écrit. Ce dépôt contient le cahier technique et la maquette ; tout ce qui est décrit ci-dessous est l'objectif, pas l'existant.

## Principes

- **Données officielles uniquement.** Les scrutins publics sont publiés en open data par l'Assemblée nationale. Voteapol les télécharge (pas de scraping de pages web) et en garde la provenance (URL source, empreinte SHA-256).
- **Descriptif, jamais évaluatif.** On affiche des effectifs exacts (pour, contre, abstentions, non-votants) avec leurs dénominateurs. Pas de note, pas de classement « du meilleur parti », pas d'interprétation des intentions.
- **Une absence n'est pas une abstention.** Les non-votants sont affichés comme tels.
- **Groupes parlementaires ≠ partis.** L'affiliation retenue est celle enregistrée au moment du scrutin, pas l'affiliation actuelle du député.
- **Chaque chiffre est vérifiable** : chaque scrutin renvoie vers sa page officielle.

## Fonctionnalités visées

| Priorité | Contenu |
|---|---|
| P1 | Accueil, recherche et liste des scrutins, fiche scrutin, liste et fiche des groupes, statistiques générales |
| P2 | Filtres par sujet, comparaison de 2 à 3 groupes, graphiques chronologiques, explications pédagogiques |
| P3 | Propositions de loi, amendements, recherche sémantique, Sénat et Parlement européen (hors MVP, à présenter comme « à venir ») |

## Architecture prévue

**Pas d'API, pas de base de données en production.** Le site est entièrement statique : l'ETL pré-calcule des fichiers JSON, le front Vue les lit, et Cloudflare les sert gratuitement.

```text
Assemblée nationale (open data : ZIP JSON + référentiels acteurs/organes)
        │
        ▼
GitHub Actions (cron quotidien + déclenchement manuel)
        │   ETL Python : téléchargement → hash → parsing → validation → SQLite de travail
        │   export : fichiers JSON statiques (scrutins, groupes, agrégats, index de recherche)
        ▼
Vue 3 + Vite + Tailwind  +  JSON générés  ──►  `wrangler deploy`
        ▼
Cloudflare Workers « Static Assets » (*.workers.dev)
```

- **Pourquoi pas d'API ni de D1.** Les requêtes sur des fichiers statiques sont gratuites et illimitées chez Cloudflare. D1, lui, est plafonné en écritures (100 000 lignes/jour en gratuit) et, depuis le 1er septembre 2026, les requêtes échouent une fois le quota dépassé. Pour des données qui ne changent qu'après chaque import, du statique est plus simple, plus rapide et sans risque de quota.
- **Pages ou Workers.** Cloudflare Pages reste supporté mais Cloudflare oriente les nouveaux projets vers Workers avec Static Assets. On utilise donc Workers Static Assets, sans code Worker à écrire.
- **Recherche et filtres** : exécutés dans le navigateur sur un index compact généré par l'ETL.
- **Contrainte à surveiller** : 20 000 fichiers maximum par déploiement en gratuit (25 Mo max par fichier). L'export regroupe donc les données plutôt que de produire un fichier par député.

## Documents du dépôt

| Fichier | Rôle |
|---|---|
| [Voteapol_Cahier_Technique_Claude_Code.md](Voteapol_Cahier_Technique_Claude_Code.md) | Cahier des charges technique : schéma relationnel, règles de l'ETL, contrat des données statiques, plan de réalisation, critères d'acceptation |
| [Voteapol — UX UI.html](Voteapol%20—%20UX%20UI.html) | Maquette (16 écrans/composants) et documentation d'intégration : routes, modèle de données par écran, design tokens. À ouvrir dans un navigateur |

## Organisation cible du dépôt

```text
etl/        ETL Python (inspect, import, validate, export) et ses tests
web/        Front Vue 3 + Tailwind + wrangler.jsonc (Static Assets)
db/         Migrations SQL
docs/       architecture, méthodologie, dictionnaire de données, déploiement
data/       archives et bases locales (ignoré par Git)
.github/    workflows ci.yml et sync.yml
```

## Commandes prévues (ETL)

```bash
python -m etl inspect  --zip ./data/Scrutins.json.zip
python -m etl import   --zip ./data/Scrutins.json.zip --db ./data/voteapol.sqlite
python -m etl validate --db ./data/voteapol.sqlite
python -m etl export   --db ./data/voteapol.sqlite --out ./dist-data
```

L'import est idempotent : relancer le même ZIP ne crée aucun doublon.

## Feuille de route

1. **Phase A — ETL fiable** : inspection des JSON, import SQLite, validation des totaux, rapport d'import, tests. Résolution des noms de groupes et de députés (référentiels officiels), sans quoi l'interface n'afficherait que des identifiants `PA…` / `PO…`.
2. **Phase B — MVP public** : export JSON, interface Vue d'après la maquette, déploiement Cloudflare, contrôle des quotas.
3. **Phase C — exploitation** : synchronisation quotidienne incrémentale, contrôles qualité, historisation des modifications.

## Limites à connaître

- Les scrutins publics ne couvrent pas tous les votes : les votes à main levée n'y figurent pas.
- La catégorie d'un scrutin (texte, article, amendement, motion) est dérivée de son titre. Elle peut se tromper et est alors signalée « à vérifier ».
- Plusieurs scrutins peuvent concerner un même texte (lectures, articles, amendements) : ils ne se comptent pas comme autant de lois.
- Voter « contre » un amendement ou un article ne dit rien de la position sur le thème général du texte.

## Coût

Objectif de 0 € sous quotas gratuits (Cloudflare Workers Static Assets, GitHub Actions, domaine `*.workers.dev`). C'est un objectif, pas une garantie : les quotas seront revérifiés avant déploiement. Aucun secret n'est versionné ; les jetons Cloudflare passent par les secrets GitHub Actions.

## Licence et données

Licence du code : à définir. Les données proviennent de l'Assemblée nationale (open data) ; leurs conditions de réutilisation seront rappelées dans `docs/methodology.md`.
