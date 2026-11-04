# ALG-12 — Garde-fou avant déploiement (changement anormal, écarts nouveaux)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Décider, à partir des rapports des étapes précédentes et d'une comparaison avec la version **publiée**, si les données peuvent être déployées automatiquement, doivent attendre une validation humaine, ou doivent être bloquées ; la décision est toujours accompagnée de ses raisons, et rien n'est jamais déployé sans que cette décision l'autorise.

## Périmètre
Inclus : comparaison avec la version publiée, règles de décision, seuils, mode sûr, lien entre validation et artefact, restauration.
Exclus : détail des contrôles (ALG-01, 05, 07, 11, 13), commandes `wrangler`, contenu du workflow GitHub Actions (`sync.yml`, à décrire dans la documentation de déploiement), vérification indépendante sur fichiers bruts (ALG-14 proposé).

## Principes
- **Construire une fois, déployer ce qui a été validé** : le répertoire exporté est un artefact de l'exécution ; le déploiement publie cet artefact, jamais un recalcul.
- **Un blocage n'est pas contournable par une validation** : une validation humaine ne lève que les cas « à examiner », jamais un échec de contrôle.
- **Mode sûr au départ** (cahier §1 et §10) : tant qu'il est actif, même un cas « tout est normal » attend une confirmation.
- Tout est décidé à partir de **rapports** : la fonction est pure, sans accès réseau ni horloge, donc testable.

## Constats
- Il n'existe pas encore de version publiée : la première publication sera une validation humaine (règle V01).
- Aucune donnée n'existe sur le rythme réel de modification des scrutins déjà publiés ; les seuils ci-dessous sont des propositions à recaler après quelques semaines d'observation.
- Rythme moyen d'ajout : environ 360 scrutins par mois (8 877 en 25 mois) soit environ 12 par jour.

## Entrées / Sorties
- Entrées : `RapportTelechargement` (ALG-13), `RapportLecture` (ALG-01), `RapportImport` (ALG-07), `RapportReconciliation` niveau base (ALG-05), `RapportExport` (ALG-11), `tests_ok` (résultat de la CI, y compris le test du lexique contrôlé), `manifeste_precedent` (le `manifeste.json` actuellement publié, absent s'il n'y a pas de publication), `manifeste_courant` (celui qui vient d'être exporté), `forcer` (booléen), `mode_sur` (booléen).
- Sortie : `DecisionPublication` = `{decision, raisons (liste {id, detail}), diff, rapport_sha256}` avec `decision` ∈ `rien_a_faire` | `publier` | `attente_validation` | `bloquer`. Écrite en fichier `decision.json` et affichée dans le résumé de l'exécution.

### Manifeste
`manifeste.json` : pour chaque scrutin, `{source_hash, empreinte_chiffres}`. `empreinte_chiffres` est le SHA-256 de la forme sérialisée canonique (ALG-11, étape 9) de : `resultat`, `totaux`, les compteurs de chaque groupe, et la liste complète des votes. Un changement d'`empreinte_chiffres` signifie qu'un **chiffre officiel publié** a changé ; un changement du seul `source_hash` peut venir d'un titre ou d'un champ non publié.

### Différences
`diff` = `{nouveaux (nombre, liste), modifies_chiffres (liste), modifies_autres (liste), supprimes (liste)}` calculé entre `manifeste_precedent` et `manifeste_courant`, par identifiant de scrutin.

**Ordre d'exécution en deux temps.** `qualite.json` (écrit par ALG-11) a besoin de `diff`, et `diff` a besoin du manifeste courant. Le calcul du manifeste courant et de `diff` (étape 3 ci-dessous) est donc appelé par ALG-11 à son étape 8, sur les documents déjà construits en mémoire ; la **décision** (étapes 1, 2 et 4 à 10) est prise après la fin de l'export, avec `RapportExport`.

## Paramètres (propositions, à recaler)
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `SEUIL_MODIFIES` | 20 scrutins | Environ 0,2 % des scrutins publiés ; des corrections ponctuelles de titre sont plausibles, une vague de modifications ne l'est pas |
| `SEUIL_NOUVEAUX` | 500 scrutins | Environ 6 % du total, soit un mois et demi d'activité normale : au-delà, il s'agit d'une reprise après une longue interruption ou d'une anomalie |

## Règles
Sévérité : **B** → `bloquer` ; **V** → `attente_validation` ; **A** → avertissement seul.

| ID | Condition | Sév. |
|----|-----------|------|
| G01 | Le téléchargement a échoué (ALG-13) ou la lecture est `echec` ou `partiel` (ALG-01) | B |
| G02 | L'import (ALG-07) est `echoue`, `interrompu` ou `termine_avec_erreurs` | B |
| G03 | La réconciliation (ALG-05) est `ecarts_nouveaux` | B |
| G04 | L'export (ALG-11) est en `echec` | B |
| G05 | `tests_ok` est faux (tests, lexique contrôlé, couleurs) | B |
| V00 | `mode_sur` est actif | V |
| V01 | Il n'y a pas de manifeste précédent (première publication) | V |
| V02 | `supprimes` n'est pas vide ou ALG-07 a signalé des scrutins `absents_de_l_archive` | V |
| V03 | `modifies_chiffres` n'est pas vide | V |
| V04 | `len(modifies_autres) + len(modifies_chiffres)` dépasse `SEUIL_MODIFIES` | V |
| V05 | `nouveaux` dépasse `SEUIL_NOUVEAUX` | V |
| V06 | ALG-09 a signalé des `noms_modifies` | V |
| V07 | Le nombre de groupes diffère de celui de la version publiée | V |
| V08 | `forcer` est actif (republication avec archive identique) | V |
| A01 | ALG-13 a signalé un avertissement de fraîcheur | A |
| A02 | Le nombre de scrutins `indetermine` (ALG-08) a augmenté | A |
| A03 | ALG-11 a produit un avertissement de taille ou de nombre de fichiers | A |

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Fonction pure : elle ne lit que des rapports.

```text
# Notations
rapports = Entrée[telechargement, lecture, import, reconciliation, export, tests_ok]
prec     = manifeste_precedent (absent si aucune publication)
cour     = manifeste_courant
raisons  = liste vide

si rapports.telechargement.sha256 = empreinte de la version publiée et non forcer:
    decision = "rien_a_faire" ; arrêt                                              [1]

# Règles bloquantes (B)
pour chaque règle G01 … G05:                                                       [2]
    G01 : téléchargement échoué, ou lecture "echec" / "partiel"
    G02 : import "echoue", "interrompu" ou "termine_avec_erreurs"
    G03 : réconciliation "ecarts_nouveaux"
    G04 : export "echec"
    G05 : tests_ok = faux
    si vraie: raisons.ajouter(règle)
si raisons non vide:  decision = "bloquer" ; arrêt   # toutes les raisons sont données

# Différences avec la version publiée
diff = { nouveaux      = ids(cour) \ ids(prec),
         supprimes     = ids(prec) \ ids(cour),
         modifies_chiffres = { id | empreinte_chiffres(cour, id) ≠ empreinte_chiffres(prec, id) },
         modifies_autres   = { id | source_hash différent mais empreinte_chiffres égale } }   [3]

# Règles de validation (V)
V00 mode_sur actif ; V01 prec absent ; V02 supprimes ≠ ∅ ou scrutins absents de l'archive
V03 modifies_chiffres ≠ ∅
V04 |modifies_autres| + |modifies_chiffres| > 20
V05 |nouveaux| > 500
V06 noms modifiés (ALG-09) ; V07 nombre de groupes différent ; V08 forcer actif       [4]

si au moins une V est vraie:  decision = "attente_validation"
sinon:                        decision = "publier"                                  [5]

joindre les avertissements A01 … A03 aux raisons (sans effet sur la décision)       [6]
rapport_sha256 = SHA256(decision.json canonique)                                    [7]

si decision = "attente_validation": déploiement dans un travail distinct,
    exigeant l'approbation d'un relecteur, sur l'artefact de CETTE exécution        [8]
si decision ∈ {"publier", approuvée}:
    déployer l'artefact ; relire meta.json en ligne ;
    si archive_sha256 ou nombre de scrutins diffère: échec de déploiement          [9]
en cas d'échec: ne rien déployer, conserver la version publiée                     [10]

affichage: "décision : " + decision + " (" + raisons + ")"
```

Propriétés : une règle B vraie impose `bloquer` quelles que soient les autres ; `publier` n'est retourné que si aucune règle B ni V n'est vraie ; une validation humaine ne lève jamais un blocage. Exemples : 12 nouveaux scrutins, tout ok, mode sûr inactif → `publier` ; un `pour` modifié sur un scrutin publié → `attente_validation` (V03) ; écart de réconciliation nouveau → `bloquer` (G03) même si V03 est vraie.

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Si l'empreinte d'archive du téléchargement est égale à celle de la version **publiée** et que `forcer` est faux : `rien_a_faire`, arrêt | Cahier §10 : ne pas importer ni déployer si l'archive est inchangée. On compare à la version publiée et **non** au dernier import : si un déploiement a échoué, l'exécution suivante doit retenter |
| 2 | Évaluer G01 à G05 ; si au moins une est vraie : `bloquer`, avec **toutes** les raisons | Un échec de contrôle ne se discute pas ; le rapport doit tout dire d'un coup |
| 3 | Calculer `diff` entre manifestes (étape non exécutée s'il n'y a pas de manifeste précédent, `nouveaux` = tous) | Mesure objective de l'ampleur du changement |
| 4 | Évaluer V00 à V08 ; relever **toutes** celles qui sont vraies | Idem |
| 5 | Si au moins une V est vraie : `attente_validation` ; sinon `publier` | Garantie 5 : un changement anormal attend une validation humaine |
| 6 | Évaluer A01 à A03 et les joindre aux raisons, sans effet sur la décision | L'information doit être visible sans bloquer |
| 7 | Calculer `rapport_sha256` = SHA-256 de `decision.json` sérialisé de façon canonique ; l'écrire avec le rapport | La validation se rattache à un état précis |
| 8 | `attente_validation` : le déploiement est un travail distinct attaché à un environnement exigeant l'approbation d'un relecteur identifié ; il s'exécute sur l'artefact de **cette** exécution ; une nouvelle exécution demande une nouvelle approbation | Une validation ne vaut que pour ce qui a été examiné ; l'artefact ne peut pas changer entre l'approbation et le déploiement |
| 9 | `publier` ou `attente_validation` approuvée : déployer l'artefact, puis relire `meta.json` en ligne et comparer `archive_sha256` et le nombre de scrutins ; en cas de différence, signaler un échec de déploiement | On ne suppose pas que le déploiement a réussi |
| 10 | Échec à n'importe quelle étape : conserver les journaux, ne rien déployer, laisser la version publiée telle quelle | Cahier §10, point 6 |

## Restauration
La version publiée précédente doit pouvoir être redéployée sans reconstruction : conserver pour chaque publication l'artefact (ou la révision du code et l'empreinte de l'archive) pendant une durée à fixer. La procédure exacte (redéploiement de l'artefact précédent, ou fonction de retour arrière de la plateforme) sera décrite dans `docs/deployment.md`. **À vérifier dans la documentation de Cloudflare avant le premier déploiement** : ce que la plateforme conserve et sa durée.

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Même archive que la version publiée | `rien_a_faire` | étape 1 |
| 12 nouveaux scrutins, aucun autre changement, contrôles ok, `mode_sur` inactif | `publier` | cas courant |
| Même cas, `mode_sur` actif | `attente_validation` (V00) | mode sûr initial |
| Un scrutin publié dont `pour` change | `attente_validation` (V03) | un chiffre officiel publié a changé |
| 25 scrutins modifiés dont aucun chiffre | `attente_validation` (V04) | dépasse 20 |
| Un scrutin disparaît de l'archive | `attente_validation` (V02) | garantie 5 |
| Écart de réconciliation nouveau | `bloquer` (G03), même si V03 est vraie | le blocage prime |
| Archive `partiel` (un scrutin illisible) | `bloquer` (G01) | un scrutin manquant n'est pas passé sous silence |
| Première publication | `attente_validation` (V01) | aucune référence de comparaison |
| 600 nouveaux scrutins | `attente_validation` (V05) | reprise après interruption, ou anomalie |
| `forcer` avec archive identique, tout ok | `attente_validation` (V08) | décision humaine explicite |
| Le déploiement réussit mais `meta.json` en ligne diffère | échec signalé, version précédente disponible | étape 9 |

## Exemples chiffrés (à reproduire en test)
Tests sur des rapports construits (aucune donnée parlementaire n'est produite) : un test par ligne de la table des cas limites ; la fonction reçoit des rapports sous forme de données, retourne `decision` et `raisons`, et le test compare les deux.

## Invariants vérifiés
- La décision est une fonction des seuls rapports d'entrée : mêmes entrées, même décision, mêmes raisons.
- Si une règle B est vraie, la décision est `bloquer` quelles que soient les autres.
- `publier` n'est retourné que si aucune règle B ni V n'est vraie.
- Le déploiement ne publie que l'artefact dont le `rapport_sha256` correspond à la décision.
- Aucun secret n'apparaît dans les rapports ni dans `decision.json`.

## Questions à trancher avant de coder
1. **Seuils** `SEUIL_MODIFIES = 20` et `SEUIL_NOUVEAUX = 500` : propositions, sans donnée d'observation. Les recaler après quelques semaines de synchronisation ?
2. **Où vit le manifeste précédent ?** Je propose de le lire dans la version publiée (`/data/v1/manifeste.json`), pas dans la base (la base n'est pas conservée entre deux exécutions, voir ALG-07, question 1). Ajouter `manifeste.json` modifie le contrat de ALG-11 : voir ALG-11, question 4.
3. **Mode sûr** : je propose que `publier` automatique ne soit autorisé que sur ton instruction explicite, selon `.agents/AGENT.md`. Quand le lèves-tu ?
4. **Validation** : par un relecteur de l'environnement GitHub (approbation requise), par défaut un seul : toi. D'accord ?
5. **ALG-14** (vérification indépendante) : si elle est créée, elle devient une règle B de plus (G06).
6. **Durée de conservation des artefacts** pour la restauration : à fixer avec les limites de GitHub Actions.

## Sources et constats
Cahier technique §10 et §11 ; `docs/methodology.md` (garanties 2, 4, 5, 6) ; `.agents/AGENT.md` (« Ce que l'agent NE doit PAS faire », déploiement) ; `.agents/CONVENTIONS.md` (« Règles spécifiques export statique et déploiement ») ; fiches ALG-01, 05, 07, 09, 11, 13.

## Historique
- v1 (2026-11-03) : première rédaction.
