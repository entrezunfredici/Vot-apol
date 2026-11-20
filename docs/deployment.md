# Déploiement

Ce document décrit la chaîne quotidienne (`.github/workflows/sync.yml`), la commande `etl sync` qui
l'alimente, la validation humaine et la restauration. Les règles de décision sont dans la fiche
[ALG-12](algorithmes/ALG-12-garde-fou-deploiement.md) ; le téléchargement dans
[ALG-13](algorithmes/ALG-13-telechargement.md).

## Vue d'ensemble

```text
sync (une fois par jour, ou à la demande)
  ├─ tests (pytest, vitest)                      -> G05
  ├─ etl sync                                    -> decision.json + dist-data/data/v1
  │    ALG-13 télécharger les scrutins et les référentiels (AMO30)
  │    ALG-12.1 « rien à faire » si TOUTES les entrées sont identiques à la version publiée
  │    ALG-01/02/04/06/07 import dans une base neuve, puis ALG-05
  │    ALG-09 noms des groupes et des députés
  │    ALG-11 export ; ALG-14 vérification indépendante (scripts/verifier_echantillon.py)
  │    ALG-12 décision : rien_a_faire | publier | attente_validation | bloquer
  └─ artefacts conservés 30 jours (décision, journaux, archives, données)

deploy (seulement si la décision est publier ou attente_validation)
  ├─ etl autoriser : décision et fichiers intacts, approbation reçue si nécessaire   (ALG-12.8)
  ├─ build du site + copie de l'artefact de données, contrôle des limites Cloudflare
  ├─ wrangler deploy
  └─ etl verifier-deploiement : meta.json en ligne = celui déployé                    (ALG-12.9)
```

`bloquer` fait échouer le travail `sync` (notification GitHub) et `deploy` ne démarre pas.
`rien_a_faire` réussit sans rien déployer.

## Réglages GitHub à créer une fois

| Où | Nom | Valeur |
|----|-----|--------|
| Variable | `VOTEAPOL_URL_PUBLIEE` | Racine en ligne des données, avec `/data/v1/` final. Vide : aucune version publiée connue |
| Secret | `CLOUDFLARE_API_TOKEN` | Jeton limité au déploiement du Worker |
| Secret | `CLOUDFLARE_ACCOUNT_ID` | Identifiant du compte |
| Environnement | `publication` | Sans relecteur (décision `publier`) |
| Environnement | `validation-publication` | **Un relecteur : le responsable du projet** (décision `attente_validation`) |

Aucun secret n'est lu par l'ETL : seul le travail `deploy` reçoit les identifiants Cloudflare.

## Mode sûr

Le mode sûr est actif par défaut (règle V00) : même un cas « tout est normal » attend l'approbation
du relecteur. Pour autoriser la publication automatique des cas normaux, sur instruction explicite
du responsable, ajouter `--mode-automatique` à la commande `etl sync` du workflow. Un changement
anormal (V01 à V08) attend toujours une validation ; un blocage (G01 à G06) n'est jamais levé par une
validation.

## Valider une publication

1. Ouvrir l'exécution du workflow : le travail `deploy` attend l'approbation.
2. Lire `decision.json` (artefact `decision`) : raisons `V…`, avertissements `A…`, différences avec la
   version publiée (`diff`), et `travail/journaux/` pour le détail de l'import.
3. Approuver ou rejeter l'environnement. L'approbation ne vaut que pour **cette** exécution : le
   `rapport_sha256` de la décision relie l'approbation à un état précis, et `etl autoriser` recalcule
   les empreintes des fichiers à déployer avant d'autoriser.

## Déployer le front seul (`deploy-web.yml`)

Un déploiement Cloudflare remplace tous les fichiers du site : publier une nouvelle version du code
du front exige de rejouer les données. Le workflow `deploy-web.yml` (poussée sur `main` touchant `web/`,
ou lancement manuel) les **reprend depuis le site en ligne** au lieu de les recalculer :

1. tests du front ;
2. `scripts/recuperer_donnees_publiees.py` télécharge `/data/v1/` (liste déduite de `scrutins-index.json`,
   `manifeste.json` et `groupes.json`), recalcule `donnees_sha256` et le compare au manifeste : un fichier
   manquant, altéré ou mélangé entre deux publications est refusé ;
3. build, contrôle des limites, `wrangler deploy`, puis `etl verifier-deploiement` ;
4. les données ne sont jamais modifiées : leur mise à jour reste le travail de `sync.yml` (décision ALG-12,
   validation humaine).

Ce workflow et `sync.yml` partagent le groupe de concurrence `deploiement` : jamais deux déploiements
en même temps. Il échoue tant qu'aucune version n'est publiée (404 sur `meta.json`) : lancer `sync.yml`
d'abord. Il n'utilise que les réglages déjà listés ci-dessus (variable `VOTEAPOL_URL_PUBLIEE` obligatoire).

## Commandes

```text
etl sync --workdir <dir> --out <dir> [--url-publiee <url>] [--tests-ok] [--forcer] [--mode-automatique]
etl autoriser --decision <decision.json> --data <dir> [--approuvee]
etl verifier-deploiement --url-publiee <url> --data <dir>
```

Codes de sortie de `etl sync` : 0 (`rien_a_faire`, `publier`, `attente_validation`), 1 (`bloquer`),
2 (écarts connus ou corrections illisibles). `etl autoriser` : 0 autorisé, 1 refusé.

Variables d'environnement facultatives : `VOTEAPOL_URL_SCRUTINS`, `VOTEAPOL_URL_REFERENTIELS`,
`VOTEAPOL_URL_PUBLIEE` (adresses officielles vérifiées par défaut, voir `etl/src/etl/config.py`).

## Cas particuliers

- **Première publication** : `meta.json` répond 404, ce qui n'est pas une erreur (V01 : validation
  demandée). Toute autre réponse que 200 ou 404 pour un fichier publié bloque (G01, `publie_inconnu`) :
  on ne prend jamais une panne pour une première publication.
- **Référentiels indisponibles ou illisibles** : la décision bloque (G01) ; sans eux les libellés des
  groupes et des députés régresseraient en « non résolu ».
- **Nom modifié par le référentiel** : comparé aux fichiers `groupes.json` et `deputes.json` publiés
  (la base est reconstruite à chaque exécution) ; une différence demande une validation (V06).
- **Republication forcée** : `workflow_dispatch` avec `forcer` ; demande une validation (V08).

## Restauration

La version précédente doit pouvoir être redéployée sans reconstruction. Moyen retenu : les artefacts
`donnees` des exécutions précédentes sont conservés **30 jours** ; pour revenir en arrière, relancer
le travail `deploy` d'une exécution antérieure (« Re-run » sur l'exécution voulue : il redéploie
l'artefact de cette exécution, et `etl autoriser` revérifie ses empreintes).

**À vérifier avant le premier déploiement, dans la documentation de Cloudflare** : ce que la
plateforme conserve des versions déployées (retour arrière natif) et pendant combien de temps, et
les limites actuelles (20 000 fichiers, 25 Mo par fichier ; `scripts/check_deploy_limits.py`).

## Ce que ce dépôt ne fait pas encore

- Le premier déploiement réel n'a pas été exécuté : variable, secrets et environnements GitHub sont
  à créer, et le comportement sur l'archive officielle complète (9 895 scrutins) est à observer.
- Les seuils d'ALG-12 (20 modifiés, 500 nouveaux) sont des propositions à recaler après quelques
  semaines d'observation.
