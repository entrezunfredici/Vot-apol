# CONVENTIONS.md — Conventions du projet

> Fichier spécifique à Voteapol. L'agent IA doit le lire avant toute implémentation.  
> Le détail fonctionnel (schéma, règles d'import, contrat des données statiques) est dans `Voteapol_Cahier_Technique_Claude_Code.md` ; la maquette dans `Voteapol — UX UI.html`.

---

## Stack technique

| Élément | Valeur |
|---------|--------|
| ETL | Python 3.12+, bibliothèque standard en priorité (`zipfile`, `sqlite3`, `json`, `hashlib`) |
| Tests ETL | pytest |
| Lint / types ETL | ruff + mypy |
| Base de données | SQLite, **uniquement comme base de travail de l'ETL** (pas de base en production) |
| Données publiques | Fichiers JSON statiques générés par l'ETL (`/data/v1/…`) — **pas d'API, pas de D1** (voir `DECISIONS.md`) |
| Front | Vue 3 + Vite + TypeScript |
| Styling | Tailwind CSS (tokens repris de la maquette) |
| Tests front | Vitest |
| Lint front | ESLint + Prettier + `vue-tsc` |
| Hébergement | Cloudflare Workers Static Assets (pas Pages), domaine `*.workers.dev`, déploiement par `wrangler deploy` depuis GitHub Actions |
| CI / sync | GitHub Actions (`ci.yml`, `sync.yml`) |
| Langue | Interface, messages d'erreur, documentation : français. Code (identifiants) : anglais **sauf** termes métier du domaine (voir Nommage) |

---

## Structure de dossiers

```text
Vot-apol/
├── etl/
│   ├── pyproject.toml
│   ├── src/etl/            # inspect, import, validate, export, normalisation, classification
│   └── tests/              # pytest + fixtures de vrais scrutins
├── web/
│   ├── package.json
│   ├── wrangler.jsonc      # assets uniquement, pas de code Worker
│   └── src/                # pages, components, composables, router
├── db/
│   └── migrations/         # SQL numérotés (0001_init.sql, …)
├── docs/                   # architecture, methodology, data-dictionary, deployment
├── data/                   # archives, bases locales — ignoré par Git
├── .agents/                # ce dossier
├── .github/workflows/      # ci.yml, sync.yml
└── README.md
```

---

## Nommage

| Élément | Convention | Exemple |
|---------|-----------|---------|
| Modules / fonctions Python | snake_case | `parse_scrutin`, `import_archive` |
| Classes Python | PascalCase | `ImportReport` |
| Constantes | UPPER_SNAKE_CASE | `MAX_UNCOMPRESSED_BYTES` |
| Tables et colonnes SQL | snake_case, pluriel pour les tables | `scrutins`, `scrutin_group_votes`, `date_scrutin` |
| Migrations | `NNNN_description.sql` | `0001_init.sql` |
| Fichiers de données publiques | minuscules, versionnés sous `/data/v1/` | `/data/v1/scrutins/VTANR5L17V2657.json` |
| Fichiers TS (non-composants) | camelCase | `scrutinsData.ts` |
| Composants et pages Vue | PascalCase | `ScrutinsPage.vue`, `VoteBadge.vue` |
| Composables | `useXxx` | `useScrutinsSearch` |
| Commandes ETL | `python -m etl <inspect\|import\|validate\|export>` | |

**Termes métier conservés en français** (ne pas les traduire, ils correspondent à la source officielle) : `scrutin`, `groupe`, `depute`. Les positions normalisées sont : `pour`, `contre`, `abstention`, `non_votant`, `non_votant_volontaire` (valeur source conservée si inconnue).

---

## Règles de données (ETL)

- Lecture du ZIP **en streaming**, sans extraction complète. Rejeter les chemins suspects (zip-slip) et les entrées dont la taille décompressée est excessive.
- Les collections XML→JSON peuvent être `null`, un objet ou un tableau : **toujours normaliser en liste**. Les nombres stockés en chaînes sont convertis.
- Import **idempotent** : transactions par lots, UPSERT ; un réimport identique ne crée aucune ligne. Un fichier modifié met à jour la ligne existante.
- Chaque scrutin garde sa provenance : `source_url`, `source_hash`, `imported_at`.
- Les totaux de chaque scrutin et de chaque groupe sont vérifiés ; les écarts sont **signalés, jamais masqués ni corrigés silencieusement**.
- L'affiliation d'un député est celle **enregistrée dans le scrutin** (`scrutin_individual_votes.groupe_id`), jamais l'affiliation actuelle.
- Les identifiants `PO…` / `PA…` sont techniques. Tant que le référentiel n'est pas importé, ils s'affichent avec la mention « libellé non résolu ».
- Les champs sources inconnus sont conservés (données brutes) ou réimportables ; ne pas multiplier les colonnes sans utilité démontrée.
- Journal d'import minimal : fichiers lus, ignorés, en erreur, doublons, nouveaux scrutins, scrutins modifiés, durée, SHA-256 de l'archive.
- L'ETL doit pouvoir tourner **hors ligne** sur une archive locale et reprendre après erreur.

---

## Règles de neutralité (affichage et statistiques)

> Les 12 garanties de `docs/methodology.md` (« Garanties d'intégrité et de neutralité ») sont obligatoires. En cas de doute sur une donnée ou un libellé : ne pas afficher, ou afficher « non déterminé », et poser la question.

- Toujours afficher les **effectifs exacts** (pour, contre, abstentions, non-votants) avec leur **dénominateur**.
- Une « position du groupe » = majorité parmi les positions exprimées, dénominateur explicite ; signaler partage ou faible participation.
- Ne **jamais** présenter une absence comme une abstention.
- Calculer séparément la répartition des positions individuelles et le nombre de scrutins où une position est majoritaire. Distinguer députés participants, effectif du groupe et taux de participation.
- Afficher le nombre de scrutins retenus et les filtres appliqués. Ne pas additionner des scrutins différents comme des lois distinctes.
- Pas de score de « qualité », « cohérence idéologique » ou « meilleur parti ». Seuls les indicateurs définis dans `DECISIONS.md` (« Indicateurs sur les groupes ») sont autorisés : pas de mot « cohésion », « discipline », « dissident », « rebelle » ni tri par alignement.
- Ne pas interpréter « contre » comme une opposition au thème général du texte.
- Chaque scrutin affiché renvoie vers sa page officielle.
- Classification des scrutins (`categorie`) : métadonnées officielles d'abord ; à défaut, règles explicites versionnées et testées, avec `classification_method` et un indicateur « à vérifier ». Une détection par mot-clé n'est jamais une certitude.

---

## Règles spécifiques export statique et déploiement

- Contrat des fichiers décrit dans le cahier §8 et dans `docs/data-dictionary.md` ; chaque schéma est validé par des tests dans `etl/tests/`.
- Changer le format d'un fichier de données = interface publique : le signaler, incrémenter la version (`/data/v2/`) si le front en dépend.
- Contraintes Cloudflare gratuit : **moins de 20 000 fichiers** par déploiement, **25 Mo maximum par fichier**. L'export vérifie ces bornes et échoue sinon. Regrouper plutôt que produire un fichier par député.
- Fichiers de liste volumineux : fragmenter (par mois ou par législature) plutôt que de charger un fichier géant sur mobile.
- L'export est déterministe : mêmes entrées → mêmes octets (tri stable), pour que les diffs et le hash soient exploitables.
- Aucun secret dans le dépôt ; jetons Cloudflare via secrets GitHub Actions. Déploiement uniquement si le hash de l'archive a changé et que les contrôles passent ; jamais de déploiement sans confirmation de l'utilisateur tant que la CI n'est pas validée.

---

## Règles spécifiques front

- Respecter la maquette (`Voteapol — UX UI.html`) : routes, tokens, composants partagés. En cas d'écart nécessaire, le signaler.
- `VoteBadge` est le **seul** composant qui porte les couleurs de vote ; toujours icône + libellé. Aucune couleur de vote codée ailleurs.
- Aucune couleur en dur dans les composants : tokens du thème Tailwind.
- Les indicateurs de la page d'accueil (nombre de scrutins, période, date de dernière synchronisation) viennent de `/data/v1/meta.json`, **jamais codés en dur**.
- États obligatoires : chargement (squelettes), liste vide, erreur réseau avec nouvelle tentative, fin de pagination.
- Accessibilité : éléments interactifs natifs (`button`, `a href`, `input` + `label`), navigation clavier, `aria-label` sur les boutons icône, contraste de texte ≥ 4,5:1, responsive mobile (rupture à 768 px).
- Pas de graphique trompeur : axes honnêtes, valeurs absolues et dénominateurs visibles.
- Les fonctionnalités P3 sont présentées comme « à venir », jamais comme opérationnelles.
- Un composant Vue responsive unique couvre desktop et mobile (pas de doublon par taille d'écran).

---

## Dépendances approuvées

À compléter au fil du projet. Tout ajout est signalé et justifié dans `DECISIONS.md`.

| Usage | Librairie |
|-------|-----------|
| ETL | bibliothèque standard Python ; pytest, ruff, mypy (dev) |
| Front | vue, vue-router, vite, typescript, tailwindcss, vitest |
| Déploiement | wrangler (dev) |
| Recherche côté navigateur | MiniSearch ou Pagefind (à choisir, voir `DECISIONS.md`) |

---

## Ce qui est hors-scope du MVP

- IA / RAG, recherche sémantique
- Sénat, Parlement européen
- Analyse des amendements non soumis à scrutin public
- Catégorisation sémantique automatique (thèmes/sujets)
- Notation ou classement des partis
- Authentification et comptes utilisateurs
- API, base de données distante (D1), FastAPI, Kubernetes
