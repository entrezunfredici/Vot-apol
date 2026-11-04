# ALG-07 — Import idempotent (UPSERT, détection de changement, journal)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Écrire dans SQLite les lots produits par ALG-04 et ALG-06 de façon que rejouer le même import ne change aucune ligne, qu'un fichier modifié mette à jour son scrutin en entier (sans ligne résiduelle), qu'une donnée valide ne soit jamais remplacée par une donnée partielle, et que chaque exécution laisse un journal exploitable.

## Périmètre
Inclus : vérification du schéma, ligne `imports`, classement nouveau / inchangé / modifié / retraité, écriture transactionnelle par scrutin et par lot, scrutins absents de l'archive, reprise après erreur, mode simulation, journal.
Exclus : lecture de l'archive (ALG-01), construction des lignes (ALG-04), contrôles de cohérence (ALG-05, lancés après l'import), noms des groupes et députés (ALG-09), décision de publier (ALG-12), création des tables (migrations `db/migrations/NNNN_*.sql`).

## Principes
- **Une unité atomique = un scrutin.** Toutes ses lignes (scrutin, totaux, groupes, votes, mises au point) sont écrites ou aucune.
- **La clé de comparaison** est le couple (`source_hash`, `etl_version`) : le premier détecte un changement du fichier source, le second un changement des règles de traitement (ALG-02, 04, 06) qui modifierait les lignes à source égale.
- **Jamais de suppression automatique** d'un scrutin déjà en base.
- La base est un **outil de travail** de l'ETL (décision du 2026-10-22). L'archive reste la source de vérité.

## Entrées / Sorties
- Entrées : chemin de la base, flux de `LotScrutin` (après ALG-06, partie A) accompagné de l'`RapportLecture` d'ALG-01, `importe_le` (horodatage UTC fourni par l'appelant), `version_etl`, `TAILLE_LOT`, option `--dry-run`.
- Sorties : base mise à jour ; ligne `imports` ; `RapportImport` journalisé en entier (fichier `import-<id>.json`) : `import_id`, `archive_sha256`, `type_empreinte`, `statut_lecture`, `fichiers_vus`, `fichiers_ok`, `fichiers_en_echec`, `nouveaux`, `inchanges`, `modifies` (liste `{id, ancien_hash, nouveau_hash, champs_modifies}`), `retraites`, `refuses` (liste `{id, cause}`), `absents_de_l_archive` (liste d'identifiants), `duree_secondes`, `statut`.
- `statut` ∈ `termine` | `termine_avec_erreurs` | `echoue` | `interrompu` | `simulation`.

## Paramètres
| Paramètre | Valeur proposée | Justification |
|-----------|-----------------|---------------|
| `TAILLE_LOT` | 200 scrutins par transaction | Environ 150 votes par scrutin en moyenne (1 323 978 votes pour 8 877 scrutins), soit 30 000 lignes par transaction : peu de transactions, peu de travail perdu en cas d'échec |
| `VERSION_SCHEMA_ATTENDUE` | numéro de la dernière migration | La base doit correspondre au schéma que le code attend |
| Verrou d'écriture | `BEGIN IMMEDIATE` | SQLite n'admet qu'un écrivain ; un second import échoue proprement au lieu d'attendre indéfiniment |

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Unité atomique : un scrutin.

```text
# Notations
base      = ouvrir(chemin) avec clés étrangères
lecture   = Entrée[RapportLecture d'ALG-01]
journal   = RapportImport vide

si schéma(base) ≠ VERSION_SCHEMA_ATTENDUE:   statut = "echoue" ; arrêt              [1]
si lecture.statut = "echec":                 statut = "echoue" ; arrêt              [2]
ajouter une ligne imports (status = "en_cours") et la valider tout de suite        [3]

pour chaque lot L de TAILLE_LOT scrutins (ordre des numéros):
    démarrer une transaction (BEGIN IMMEDIATE)
    pour chaque scrutin s du lot:
        si s a des erreurs (ALG-02, 04, 06):
            journal.refuses += {id, cause} ; ne rien écrire pour s ; suivant       [4]
        ancien = lire(scrutins, id = s.id)                                         [5]
        classe = si ancien absent:                                  "nouveau"
                 sinon si (hash, etl_version) identiques:           "inchange"
                 sinon si hash différent:                           "modifie"
                 sinon:                                             "retraite"      [6]
        si classe = "inchange":
            compter ; ne rien écrire (même pas imported_at)                         [7]
        sinon:
            INSERT OR IGNORE groupes, deputes vus (sans nom)                        [8]
            si classe ∈ {modifie, retraite}:
                champs_modifies = comparer(ancien, s)
                supprimer les lignes enfants de s (mises au point, votes, groupes, totaux)   [9]
            UPSERT scrutins ; insérer totaux, groupes, votes, mises au point        [10]
    valider la transaction                                                          [11]
    # erreur de base → annuler le lot en cours, "echoue", arrêt

journal.absents = { id ∈ scrutins } \ { id acceptés ou refusés dans cet import }   [13]
                  # jamais supprimés
statut = "termine_avec_erreurs" si refuses ≠ ∅ ou lecture.statut = "partiel"
                                 ou absents ≠ ∅
         sinon "termine"                                                            [14]
mettre à jour imports ; écrire import-<id>.json en entier                           [15]
```

Propriétés : `nouveaux + inchanges + modifies + retraites + refuses = acceptees (ALG-01)` ; rejouer deux fois la même archive donne `inchanges = 8 877` et aucune ligne modifiée ; un scrutin modifié est entièrement réécrit (aucun député résiduel) ; une donnée valide n'est jamais remplacée par une donnée refusée. `--dry-run` exécute les mêmes comparaisons sans rien écrire (`simulation`) [16].

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Ouvrir la base, activer les clés étrangères, lire `PRAGMA user_version` ; si différent de `VERSION_SCHEMA_ATTENDUE` : `echoue`, arrêt (aucune migration implicite) | Un import ne doit jamais modifier un schéma sans que l'on l'ait demandé |
| 2 | Si `statut_lecture` d'ALG-01 est `echec` : ne rien écrire dans les tables de scrutins, journaliser, `echoue`, arrêt | Rien de fiable à importer |
| 3 | En mode normal : insérer la ligne `imports` (`started_at` = `importe_le`, `archive_sha256`, `status = en_cours`) et la valider **immédiatement** | Même en cas de plantage, la trace d'une exécution commencée existe |
| 4 | Pour chaque entrée du flux, dans l'ordre des numéros : si ALG-02 (ou ALG-04, ALG-06) a produit des erreurs, ajouter `{id, cause}` à `refuses`, **ne rien écrire pour ce scrutin**, passer à la suite | Une donnée valide existante n'est jamais remplacée par une donnée partielle (cahier §5.2, règle 6) |
| 5 | Lire dans `scrutins` la ligne existante (`source_hash`, `etl_version`) | Base de la détection de changement |
| 6 | Classer : aucune ligne → `nouveau` ; (`source_hash`, `etl_version`) identiques → `inchange` ; `source_hash` différent → `modifie` ; `source_hash` identique et `etl_version` différente → `retraite` | Quatre cas distincts, comptés séparément |
| 7 | `inchange` : compter, ne rien écrire (en particulier ne pas toucher `imported_at`) | Un réimport identique ne doit pas modifier une seule ligne de scrutin |
| 8 | `nouveau`, `modifie`, `retraite` : dans la transaction du lot, `INSERT OR IGNORE` dans `groupes` et `deputes` pour les identifiants de `groupes_vus` et `deputes_vus` (sans nom) | Respect des clés étrangères ; les noms sont ajoutés plus tard par ALG-09 |
| 9 | `modifie` ou `retraite` : lire les anciennes lignes du scrutin, calculer `champs_modifies` (colonnes de `scrutins`, `scrutin_totals` qui changent ; nombre de lignes de groupes, votes, mises au point qui diffèrent), puis supprimer toutes les lignes enfants du scrutin (mises au point, votes, groupes, totaux) | Les lignes enfants sont supprimées puis réécrites : un député retiré d'un scrutin corrigé ne doit pas survivre dans l'ancienne version |
| 10 | Écrire la ligne `scrutins` par `INSERT … ON CONFLICT(id) DO UPDATE`, puis insérer totaux, groupes, votes, mises au point (requêtes paramétrées, `executemany`) | UPSERT idempotent ; aucune concaténation SQL (règle du projet) |
| 11 | Valider la transaction tous les `TAILLE_LOT` scrutins écrits et à la fin ; en cas d'erreur de base (disque plein, contrainte) : annuler **le lot en cours**, `echoue`, arrêt | Chaque lot validé est cohérent ; l'échec ne laisse pas de scrutin à moitié écrit |
| 12 | Sur signal d'interruption : terminer le scrutin en cours, valider le lot, `interrompu` | Une interruption volontaire ne perd pas le travail fait |
| 13 | Après le flux, calculer `absents_de_l_archive` = identifiants présents dans `scrutins` mais ni acceptés ni refusés dans cet import ; **ne rien supprimer** | La disparition d'un scrutin publié est anormale : elle est signalée (ALG-12), jamais appliquée en silence |
| 14 | `statut` : `termine_avec_erreurs` si `fichiers_en_echec > 0`, ou `statut_lecture = partiel`, ou `absents_de_l_archive` non vide ; sinon `termine` | Un scrutin refusé est un scrutin manquant : jamais passé sous silence |
| 15 | Mettre à jour `imports` (`finished_at`, compteurs, `status`, `error_summary` = les 20 premières causes) ; écrire le journal complet dans le fichier `import-<id>.json` | Journal minimal du cahier §5.2 règle 8 : fichiers lus, ignorés, en erreur, doublons, nouveaux, modifiés, durée, empreinte |
| 16 | Mode `--dry-run` : ouvrir la base en lecture seule, exécuter les étapes 4 à 6, 9 (lecture), 13 et 14 sans aucune écriture, statut `simulation` | Permet à ALG-12 de mesurer l'ampleur d'un changement avant d'écrire quoi que ce soit |

## Reprise après erreur
Aucun point de reprise n'est stocké. Rejouer l'import suffit : les scrutins déjà écrits sont `inchange` (étape 7) et sont sautés, les autres sont repris. C'est la conséquence directe de l'idempotence.

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Même archive importée deux fois | 2ᵉ passage : `nouveaux = 0`, `modifies = 0`, `inchanges = 8 877`, aucune ligne modifiée dans les tables de scrutins ; une ligne `imports` de plus | étape 7 |
| Un fichier modifié (une valeur de `pour`) | `modifies = 1`, `champs_modifies` liste `pour` (et les compteurs de groupe concernés), nombre de lignes de scrutins inchangé | étapes 9, 10 |
| Fichier modifié où un député disparaît | la ligne du député est supprimée, il n'en reste aucune | étape 9 |
| Fichier modifié devenu invalide (ALG-02 en erreur) | ancien scrutin conservé, `refuses` contient l'identifiant, statut `termine_avec_erreurs` | étape 4 |
| Même fichier, `version_etl` changée | `retraite`, lignes recalculées | étape 6 |
| Archive sans le scrutin 4000 présent en base | `absents_de_l_archive = [VTANR5L17V4000]`, rien supprimé | étape 13 |
| Coupure pendant un lot | le lot en cours est annulé, les lots précédents restent ; relance = reprise | étapes 11, 12 |
| Disque plein | `echoue`, base cohérente jusqu'au dernier lot validé | étape 11 |
| Base de schéma ancien | `echoue`, aucune écriture | étape 1 |
| Deux imports simultanés | le second échoue (`base_verrouillee`) | verrou |
| ALG-01 `partiel` | scrutins valides importés, statut `termine_avec_erreurs` | étape 14 |

## Exemples chiffrés (à reproduire en test)
- Base vide + archive réelle : `nouveaux = 8 877`, `inchanges = 0`, lignes : 8 877 `scrutins`, 8 877 `scrutin_totals`, 106 524 `scrutin_group_votes`, 1 323 978 `scrutin_individual_votes`, 3 406 `scrutin_mises_au_point` (valeurs d'ALG-04).
- Deuxième passage identique : `nouveaux = 0`, `inchanges = 8 877`, mêmes nombres de lignes, même empreinte des tables (somme de contrôle calculée en test sur les tables triées).
- Fixture : un scrutin à un seul votant, puis le même avec un vote de plus : `modifies = 1`, 2 lignes de vote au lieu de 1.

## Invariants vérifiés
- Pour chaque scrutin en base, ses lignes enfants proviennent toutes de la même version de fichier (même `source_hash`).
- Un import identique ne modifie aucune ligne de `scrutins` (`imported_at` inclus) ni des tables enfants.
- Aucune ligne de `scrutins` n'est supprimée par l'import.
- `nouveaux + inchanges + modifies + retraites + refuses` = nombre d'entrées acceptées par ALG-01 (`acceptees`) ; `refuses` ne contient ici que les refus de normalisation, d'extraction ou de rattachement (ceux d'ALG-01 sont dans son propre rapport).
- Toutes les requêtes sont paramétrées.

## Questions à trancher avant de coder
1. **La base est-elle conservée entre deux exécutions de la CI ?** Je propose que non : la base est reconstruite à chaque synchronisation à partir de l'archive (27 Mo, 8 877 fichiers). Conséquence : « nouveau / modifié » du point de vue d'ALG-07 n'a de sens qu'en local ; la comparaison avec la **version publiée** se fait dans ALG-12 à partir du manifeste public. L'idempotence reste exigée (relances, reprise, usage local).
2. **`etl_version`** : à incrémenter à chaque nouvelle version d'une fiche ALG-02, 04 ou 06. D'accord pour une valeur manuelle plutôt que calculée ?
3. **Scrutin absent de l'archive** : jamais supprimé automatiquement, signalé. Veux-tu un mode de suppression explicite (`etl prune`) ou aucun ?
4. **`TAILLE_LOT = 200`** : valeur raisonnée, à confirmer par une mesure de durée sur la vraie archive.
5. **Mode `--dry-run`** : utile à ALG-12 ; confirmes-tu que cette commande est ajoutée à la liste du cahier §5.1 (modification d'interface) ?

## Sources et constats
Cahier technique §4 (`imports`), §5.2 (règles 5, 6, 8, 9, 10), §5.3 (tests de réimport et d'import d'un fichier modifié) ; `.agents/AGENT.md` (« Gestion d'erreurs ») ; `.agents/CONVENTIONS.md` (« Règles de données ») ; fiches ALG-01, 04, 05, 06.

## Historique
- v1 (2026-11-03) : première rédaction.
