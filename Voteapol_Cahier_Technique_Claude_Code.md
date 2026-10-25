# Voteapol — Cahier des charges technique pour Claude Code

**Version :** 0.1 — 19 octobre 2026  
**Objectif :** MVP public, transparent, reproductible et à coût d'hébergement nul sous quotas gratuits.  
**Source initiale :** `Scrutins.json.zip` fourni par le porteur de projet (27 Mo, **8 877 entrées JSON**, vérifiées dans l'archive).  
**Langue de l'application :** français.

## 1. Mission de Claude Code

Implémenter par étapes un explorateur des scrutins publics de la XVIIe législature de l'Assemblée nationale. Ne pas construire de notation politique ni inférer des intentions. Les données doivent toujours pouvoir être reliées au scrutin officiel.

**Livrables MVP :**
1. Un importeur Python lisant directement le ZIP sans extraction préalable, avec validation et rapports d'erreurs.
2. Un modèle relationnel SQLite pour développement local, servant de base de travail à l'ETL (le site public n'en dépend pas).
3. Une interface Vue 3 + Vite + Tailwind, déployable sur Cloudflare Workers avec Static Assets, **sans API ni base distante** : l'ETL génère des fichiers JSON statiques (voir §8).
4. Des pages de recherche de scrutins, détail de scrutin et comparaison descriptive des groupes.
5. Un workflow GitHub Actions de synchronisation planifiée, initialement en mode sûr (sans écriture distante automatique avant validation).
6. Tests, documentation de déploiement, fichiers d'exemple et README.

**Hors MVP :** IA/RAG, Sénat, Parlement européen, catégorisation sémantique automatique, analyse de tous les amendements non soumis à scrutin public, notation des partis, authentification.

## 2. Données sources : constats vérifiés

L'archive reçue contient 8 877 fichiers tels que `json/VTANR5L17V2657.json`. Chaque fichier possède une racine `scrutin` avec notamment :

- `uid`, `numero`, `legislature`, `dateScrutin`, `titre`, `objet`, `typeVote`, `sort` ;
- `syntheseVote` avec `nombreVotants`, `suffragesExprimes` et `decompte` (`pour`, `contre`, `abstentions`, `nonVotants`, etc.) ;
- `ventilationVotes.organe.groupes.groupe` contenant pour chaque groupe `organeRef`, `nombreMembresGroupe`, `vote.positionMajoritaire`, `vote.decompteVoix` et `vote.decompteNominatif` ;
- `decompteNominatif` contient les identifiants `acteurRef` et `mandatRef` des députés, selon la position.

**Important :** les références `PO...` et `PA...` sont des identifiants techniques, pas des noms. Il faudra importer les référentiels officiels d'organes et d'acteurs, ou afficher les identifiants avec mention « libellé non résolu ». Ne jamais attribuer un groupe à un député sur la base de sa seule affiliation actuelle : conserver l'affiliation enregistrée dans le scrutin.

Les valeurs XML converties en JSON peuvent être `null`, un objet ou un tableau. Normaliser systématiquement les collections en liste, y compris les cas à un seul votant ou un seul groupe. Convertir les nombres stockés comme chaînes. Inspecter plusieurs échantillons réels avant de figer le parseur.

## 3. Architecture recommandée

```text
Assemblée nationale (ZIP JSON, référentiels)
            │
            ▼
GitHub Actions (cron quotidien + workflow_dispatch)
            │
            ▼
Python 3.12+ : download → hash → parse → validate → normalize
            │
            ▼
SQLite de travail → export : fichiers JSON statiques
                                            │
                                            ▼
Vue 3 + Vite + Tailwind + JSON → wrangler deploy → Workers Static Assets
```

**Choix retenu (2026-10-22) :** pas d'API ni de D1. SQLite sert uniquement de base de travail à l'ETL ; le site déployé n'est que du statique (requêtes statiques gratuites et illimitées ; D1 limité à 100 000 écritures/jour, requêtes en échec au-delà depuis le 01/09/2026). Cloudflare Pages n'est pas utilisé : Workers Static Assets est la voie recommandée pour les nouveaux projets. Limite à respecter : 20 000 fichiers par déploiement en gratuit, 25 Mo maximum par fichier. Ne pas mettre FastAPI sur Workers par défaut. Ne pas déployer Kubernetes pour un import quotidien.

## 4. Schéma relationnel minimum

- `scrutins(id TEXT PRIMARY KEY, numero INTEGER, legislature INTEGER, date_scrutin TEXT, titre TEXT, objet TEXT, type_vote_code TEXT, type_vote_libelle TEXT, resultat_code TEXT, source_url TEXT, source_hash TEXT, imported_at TEXT)`
- `scrutin_totals(scrutin_id TEXT PRIMARY KEY, pour INTEGER, contre INTEGER, abstentions INTEGER, non_votants INTEGER, suffrages_exprimes INTEGER, nombre_votants INTEGER)`
- `groupes(id TEXT PRIMARY KEY, libelle TEXT NULL, sigle TEXT NULL)`
- `scrutin_group_votes(scrutin_id TEXT, groupe_id TEXT, membres INTEGER, pour INTEGER, contre INTEGER, abstentions INTEGER, non_votants INTEGER, position_majoritaire_source TEXT, PRIMARY KEY(scrutin_id,groupe_id))` : la position majoritaire affichée n'est **pas** la valeur source, elle est recalculée (voir `docs/methodology.md`)
- `deputes(id TEXT PRIMARY KEY, nom TEXT NULL, prenom TEXT NULL)`
- `scrutin_individual_votes(scrutin_id TEXT, depute_id TEXT, groupe_id TEXT, mandat_id TEXT NULL, position TEXT, par_delegation INTEGER NULL, PRIMARY KEY(scrutin_id,depute_id))`
- `scrutin_mises_au_point(scrutin_id TEXT, depute_id TEXT, groupe_id TEXT NULL, position_initiale TEXT NULL, position_declaree TEXT, PRIMARY KEY(scrutin_id,depute_id))` : rectifications déclarées après le vote ; `groupe_id` et `position_initiale` sont retrouvés dans le décompte nominatif, et restent `NULL` si le député y est introuvable. Ne modifie jamais les décomptes officiels (voir `docs/methodology.md`).
- `imports(id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, archive_sha256 TEXT, files_seen INTEGER, files_ok INTEGER, files_failed INTEGER, status TEXT, error_summary TEXT)`

Index recommandés : `scrutins(date_scrutin)`, `scrutins(type_vote_code)`, `scrutin_group_votes(groupe_id)`, `scrutin_individual_votes(depute_id)`. La recherche publique s'exécute côté navigateur sur un index généré par l'ETL (bibliothèque à choisir, par ex. MiniSearch ou Pagefind).

Conserver les champs sources inconnus dans les données brutes ou permettre leur réimport. Éviter de multiplier les colonnes sans utilité démontrée.

## 5. Import ETL

### 5.1 Commandes attendues

```bash
python -m etl inspect --zip ./data/Scrutins.json.zip
python -m etl import --zip ./data/Scrutins.json.zip --db ./data/voteapol.sqlite
python -m etl validate --db ./data/voteapol.sqlite
python -m etl export --db ./data/voteapol.sqlite --out ./dist-data
```

### 5.2 Règles

1. Lire les entrées du ZIP en streaming, sans extraction complète.
2. Vérifier la validité du ZIP, filtrer les chemins `.json` attendus et rejeter les entrées suspectes (zip-slip, taille décompressée excessive).
3. Traiter les valeurs `null` / objet / liste et les variantes des décomptes nominatifs.
4. Normaliser les positions : `pour`, `contre`, `abstention`, `non_votant`, `non_votant_volontaire` ; garder la valeur source si inconnue.
5. Utiliser des transactions par lots et des UPSERT idempotents. Un réimport identique ne doit créer aucun doublon.
6. Ne jamais remplacer des données valides par des données partielles sans journaliser l'opération.
7. Vérifier les totaux de chaque scrutin et de chaque groupe, signaler les écarts sans les masquer.
8. Journaliser : fichiers lus, ignorés, erreurs, doublons, nouveaux scrutins, scrutins modifiés, durée, empreinte SHA-256.
9. Permettre une reprise après erreur et une exécution locale sans accès réseau.
10. Conserver les fichiers sources ou, a minima, leur hash et leur provenance pour permettre l'audit.

### 5.3 Tests obligatoires

- Scrutin avec un seul votant et scrutin avec plusieurs centaines de votants.
- Groupe représenté par un objet unique plutôt qu'un tableau.
- Champs absents, `null`, nombre sous forme de chaîne, position inattendue.
- Réimport du même ZIP (nombre de lignes inchangé).
- Import d'un fichier modifié (UPSERT correct).
- Fichier corrompu au milieu de l'archive (rapport d'erreur exploitable).
- Vérification de cohérence : sommes des positions individuelles et agrégats de groupe lorsque le mode de publication le permet.

## 6. Classification des scrutins

Créer un champ `categorie` dérivé avec : `texte_ensemble`, `article`, `amendement`, `motion_censure`, `motion_rejet`, `autre_motion`, `procedure`, `autre`, `indetermine`.

La classification doit s'appuyer prioritairement sur les métadonnées officielles. À défaut, utiliser des règles explicites sur `titre` / `objet`, versionnées et testées. Prévoir `classification_method` et `classification_confidence` ou un indicateur « à vérifier ». Ne pas considérer une détection par mot-clé comme une certitude.

**Ne pas confondre :** vote sur un texte complet, vote définitif d'une loi promulguée, vote d'article, vote d'amendement et motion. Plusieurs votes peuvent concerner un même texte et différentes lectures.

## 7. Statistiques et neutralité

Pour chaque groupe et scrutin, afficher **les effectifs exacts** : pour, contre, abstentions, non-votants. Une « position du groupe » doit être décrite comme **majorité parmi les positions exprimées** avec le dénominateur explicite ; si partage ou faible participation, le signaler. Ne jamais présenter une absence comme une abstention.

Pour les tableaux agrégés :
- calculer séparément la répartition des positions individuelles et le nombre de scrutins où une position est majoritaire ;
- distinguer le nombre de députés participant, les effectifs de groupe et le taux de participation ;
- afficher le nombre de scrutins retenus et les filtres appliqués ;
- ne pas additionner des scrutins différents comme s'ils étaient des lois distinctes ;
- ne pas interpréter « contre » comme une opposition au thème général du texte ;
- éviter les scores de « qualité », « cohérence idéologique » ou « meilleur parti ».

## 8. Données statiques (contrat ETL → front)

Remplace l'ancienne API `/api/v1`. L'ETL génère, dans `dist-data/` (copié dans les assets du site), des fichiers JSON versionnés sous `/data/v1/`. Le front les charge avec `fetch` ; recherche, filtres et pagination s'exécutent dans le navigateur.

- `meta.json` : nombre de scrutins et de groupes, période couverte, date de dernière synchronisation, version de données, SHA-256 de l'archive source.
- `scrutins-index.json` (ou fragments par mois si trop lourd) : une ligne compacte par scrutin (id, numéro, date, titre, catégorie, résultat, totaux) ; sert à la recherche et aux filtres.
- `scrutins/<id>.json` : détail d'un scrutin (totaux, ventilation par groupe, lien officiel). Les votes individuels sont fournis dans ce fichier ou dans un fichier voisin chargé à la demande.
- `groupes.json`, `groupes/<id>.json` : groupes, noms résolus, positions par scrutin.
- `stats.json` (+ découpages par catégorie/période si nécessaire) : agrégats avec dénominateurs.
- La comparaison de groupes est calculée dans le navigateur à partir des fichiers de groupes.

Contraintes : taille de chaque fichier raisonnable pour un chargement mobile (compression gzip/brotli par Cloudflare), moins de 20 000 fichiers au total, schéma de chaque fichier documenté dans `docs/data-dictionary.md` et validé par des tests. Aucune requête SQL côté public.

## 9. Frontend Vue

Pages MVP :
1. **Accueil** : présentation, période couverte, date du dernier import, avertissement méthodologique.
2. **Scrutins** : recherche, filtres (date, catégorie, résultat), pagination.
3. **Détail scrutin** : titre, date, résultat, compte global, ventilation par groupe, lien vers l'Assemblée.
4. **Comparateur** : sélection de deux ou plusieurs groupes, résultats bruts et dénominateurs.
5. **Méthodologie** : limites des scrutins publics, définitions, provenance, code source.

Accessibilité clavier, responsive mobile, états chargement/erreur/vide, affichage de la provenance et absence de graphiques trompeurs.

## 10. Synchronisation automatique

Workflow GitHub Actions `schedule` quotidien + `workflow_dispatch` manuel :
1. Télécharger l'archive depuis la source officielle configurée (URL en variable de configuration, vérifier son actualité).
2. Contrôler les codes HTTP, la taille et l'empreinte SHA-256 ; ne pas importer si inchangée.
3. Valider et importer dans une base temporaire.
4. Générer un rapport de différences et effectuer les contrôles de cohérence.
5. Publier uniquement si les tests passent, avec mécanisme de restauration documenté.
6. Sur échec, conserver les logs et ne pas casser la version publiée.

**Important :** le déploiement (`wrangler deploy`) republie l'ensemble des assets ; ne le lancer que si le hash de l'archive a changé et que les contrôles passent. Vérifier avant chaque release le nombre de fichiers (< 20 000) et la taille du plus gros (< 25 Mo). Ne jamais intégrer de secret Cloudflare au dépôt ; utiliser les secrets GitHub Actions (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`).

## 11. Déploiement et budget

Cible : Cloudflare Workers + Static Assets pour Vue et les données JSON (pas de D1, pas de code Worker), GitHub Actions pour l'ETL et le déploiement. Prévoir un domaine `*.workers.dev` pour éviter le coût d'un nom de domaine. Les quotas, conditions et éventuels frais doivent être revérifiés avant mise en production ; le budget de **0 €** est un objectif, pas une garantie. Configurer alertes et limites lorsque disponibles.

## 12. Organisation du dépôt

```text
voteapol/
  etl/
    pyproject.toml
    src/etl/
    tests/
  web/
    package.json
    src/
    worker/
    wrangler.jsonc
  db/
    migrations/
  .github/workflows/
    sync.yml
    ci.yml
  docs/
    architecture.md
    methodology.md
    data-dictionary.md
    deployment.md
  data/             # ignoré par Git
  README.md
  .gitignore
```

Ne pas versionner l'archive ZIP, les bases volumineuses, les clés API ni les données intermédiaires générées.

## 13. Plan de réalisation

**Phase A — ce soir, priorité absolue**
- Initialiser le monorepo.
- Examiner les structures JSON et les cas particuliers.
- Implémenter `inspect`, `import`, `validate` et les tests Python.
- Obtenir une base SQLite fiable et un rapport d'import.
- Créer une page de recherche simple si le temps le permet.

**Phase B — MVP public**
- Référentiels de noms de groupes et députés.
- Export JSON statique et interface Vue complète.
- Déploiement Cloudflare et contrôle des quotas.

**Phase C — exploitation**
- Synchronisation incrémentale automatique.
- Contrôles qualité et historisation des modifications.
- Documentation publique et observabilité.

## 14. Critères d'acceptation

- Tous les fichiers JSON valides du ZIP sont analysés, avec comptage exact et erreurs documentées.
- Aucun doublon après deux imports successifs.
- Les chiffres affichés pour un échantillon de scrutins concordent avec les JSON sources.
- Les groupes ne sont pas confondus avec les partis, et les affiliations historiques sont préservées.
- Les votes sur articles, amendements, textes et motions sont distingués ou marqués « indéterminé ».
- Un visiteur peut retrouver un scrutin, ses votes par groupe et la source officielle.
- Les tests CI passent et la documentation permet de reproduire l'import.
- Les secrets et les coûts potentiels sont maîtrisés.

## 15. Prompt initial à transmettre à Claude Code

> Tu es mon binôme de développement senior. Lis entièrement `Voteapol_Cahier_Technique_Claude_Code.md` puis inspecte `Scrutins.json.zip`. Commence uniquement par la phase A. Avant de coder, analyse un échantillon représentatif des fichiers JSON et documente les variantes de structure. Implémente ensuite un ETL Python robuste et testé, avec stockage SQLite, validation des totaux et idempotence. Exécute réellement les tests et l'import sur l'archive fournie. Donne-moi les commandes exactes et le bilan des fichiers traités. Ne suppose aucune structure non vérifiée, n'invente aucun résultat parlementaire, et demande confirmation avant tout déploiement, dépense ou changement majeur d'architecture.
