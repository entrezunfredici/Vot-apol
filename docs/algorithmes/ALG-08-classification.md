# ALG-08 — Classification des scrutins (catégorie, confiance, « à vérifier »)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Attribuer à chaque scrutin une catégorie parmi un vocabulaire fermé, en s'appuyant d'abord sur les métadonnées officielles, puis sur des règles explicites appliquées au titre, en indiquant toujours comment la catégorie a été obtenue et sans jamais présenter une déduction comme une certitude. Cette catégorie sert uniquement de filtre.

## Périmètre
Inclus : vocabulaire, règles ordonnées, table de corrections manuelles, méthode, confiance, indicateur « à vérifier », versionnage.
Exclus : thèmes et sujets (hors MVP, décision du 2026-10-22), regroupement de plusieurs votes sur un même texte (voir ce que la catégorie ne dit pas), affichage du filtre (front).
Fonction pure : elle est appliquée à l'export (ALG-11) à partir de la base ; le résultat n'est pas stocké (voir question 3).

## Constats (mesurés le 2026-11-03 sur les 8 877 titres)
- `titre` et `objet.libelle` sont identiques dans 8 877 scrutins sur 8 877 : un seul texte à analyser.
- `typeVote.codeTypeVote` : `SPO` 8 780, `SPS` 74, `MOC` 23. Les 23 `MOC` sont exactement les 23 titres commençant par « la motion de censure ».
- `objet.dossierLegislatif` est `null` pour 5 826 scrutins : le dossier ne peut pas servir de critère.
- Les titres suivent une formule régulière : « l'amendement n° … », « l'article … », « l'ensemble de la proposition de loi … », « la motion de rejet préalable … ».
- Les titres contiennent des **variantes typographiques** (apostrophe courbe ’ au lieu de ', par exemple « l’amendement ») et **six fautes de frappe réelles** : « sous-amendmeent » (scrutins 1633 et 6214), « amenedement » (4988), « péalable » (7432), « aticle » (7950), « de de la proposition » (918).
- Aucune motion autre que censure ou rejet préalable n'apparaît (aucun exemple d'« autre motion » dans les données actuelles).

## Entrées / Sorties
- Entrées : `id`, `type_vote_code`, `titre` ; la table de corrections ; `VERSION_REGLES`.
- Sortie : `categorie` ∈ {`texte_ensemble`, `article`, `amendement`, `motion_censure`, `motion_rejet`, `autre_motion`, `procedure`, `autre`, `indetermine`} ; `classification_method` ∈ {`metadonnee_officielle`, `regle_titre`, `correction_manuelle`, `aucune`} ; `regle_id` (ex. `R4`, ou `null`) ; `classification_confidence` ∈ {`haute`, `moyenne`, `aucune`} ; `a_verifier` (booléen) ; `version_regles`.

### Table de corrections manuelles
Fichier versionné dans le dépôt : `{id, titre, categorie, motif, valide_le, valide_par}`. Une correction ne s'applique que si `titre` est **identique** au titre actuel du scrutin ; sinon elle est ignorée avec un avertissement `correction_obsolete`.

## Règles
Normalisation du titre avant comparaison : NFC, minuscules, apostrophes ’ et ‘ remplacées par ', espaces multiples réduits à un, espaces de début et de fin retirés. Les règles sont évaluées **dans cet ordre** ; chaque expression est ancrée au début du titre sauf R1.

| ID | Catégorie | Expression (sur titre normalisé) | Titres couverts |
|----|-----------|----------------------------------|-----------------|
| M0 | `motion_censure` | métadonnée : `type_vote_code = MOC` | 23 |
| R1 | `motion_rejet` | contient `motion de rejet préalable` | 58 |
| R2 | `autre` | `^la déclaration (du gouvernement\|de politique générale)` | 4 |
| R3 | `procedure` | `^(la demande de \|la proposition du gouvernement de prolonger)` | 18 |
| R4 | `amendement` | `^(l'\|le )(sous-)?amendement\b` | 7 585 |
| R5 | `article` | `^l'article\b` | 936 |
| R6 | `autre` | `^la (première\|deuxième\|troisième) partie\b` | 7 |
| R7 | `texte_ensemble` | `^(l'ensemble (du\|de la\|des) \|la proposition de (loi\|résolution)\|le projet de loi)` | 240 |
| — | `indetermine` | aucune règle ne correspond | 6 |

Remarques :
- L'ordre place R4 avant R5 : « l'amendement … à l'article 2 » est un amendement, pas un article (les expressions sont ancrées au début du titre).
- `autre_motion` n'a **aucune règle** : aucun cas réel n'existe. Elle reste dans le vocabulaire du cahier ; une règle sera ajoutée (nouvelle version de cette fiche) le jour où un titre réel l'exige.
- Les sous-amendements sont classés dans `amendement` (654 titres) ; voir question 2.
- Les titres couverts par R1 à R7 totalisent 8 848 ; avec M0 (23) et les 6 indéterminés on retrouve 8 877.

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Fonction pure, sans stockage.

```text
# Notations
scrutin = Data[x]                       # id, type_vote_code, titre
titre   = scrutin.titre
corrections = Data[table de corrections]

si ∃ correction c avec c.id = scrutin.id:                                           [1]
    si c.titre = titre:
        retourner (c.categorie, "correction_manuelle", confiance "haute", a_verifier = faux)
    sinon:
        avertissement "correction_obsolete"                    # on continue

si scrutin.type_vote_code = "MOC":                                                  [2]
    categorie = "motion_censure" ; méthode = "metadonnee_officielle" ; a_verifier = faux
    si "motion de censure" ∉ normaliser(titre):
        avertissement "incoherence_metadonnee" ; a_verifier = vrai
    retourner

t = normaliser(titre)    # NFC, minuscules, ’ → ', espaces réduits                  [3]

correspondances = { règle ∈ (R1, …, R7) | t correspond à règle.expression }         [4]
categories      = { règle.categorie | règle ∈ correspondances }

si |categories| ≥ 2:                                                                [5]
    categorie = "indetermine" ; méthode = "aucune" ; a_verifier = vrai
    avertissement "regles_en_conflit"
sinon si |categories| = 1:                                                          [6]
    categorie = l'unique catégorie ; méthode = "regle_titre"
    confiance = "moyenne" ; a_verifier = vrai
sinon:                                                                              [7]
    categorie = "indetermine" ; méthode = "aucune" ; confiance = "aucune" ; a_verifier = vrai

ajouter version_regles                                                              [8]

# Exemple d'ordre des règles : « l'amendement n° 19 … à l'article 2 … »
#   R4 (amendement) correspond car ancrée au début ; R5 (article) ne correspond pas
#   → catégorie unique "amendement"
affichage:
    pour categorie = "amendement":  afficher "Vote sur un amendement"
    pour categorie = "indetermine": afficher "Catégorie non déterminée"
```

Propriétés : chaque scrutin reçoit exactement une catégorie ; `a_verifier = faux` seulement pour une métadonnée officielle ou une correction manuelle ; les décomptes sur les données réelles sont 7 585 amendements, 936 articles, 240 textes, 58 motions de rejet, 23 motions de censure, 18 procédures, 11 autres, 6 indéterminés (somme 8 877).

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Si une correction existe pour `id` et que son `titre` est identique : retourner sa catégorie, méthode `correction_manuelle`, confiance `haute`, `a_verifier = faux`, `regle_id = null` ; si le titre diffère : avertissement `correction_obsolete` et continuer | Une vérification humaine du titre exact prime ; une correction sur un titre qui a changé n'est plus une vérification |
| 2 | Si `type_vote_code = MOC` : catégorie `motion_censure`, méthode `metadonnee_officielle`, confiance `haute`, `a_verifier = faux`. Si le titre normalisé ne contient pas `motion de censure` : avertissement `incoherence_metadonnee` et `a_verifier = vrai` | Priorité à la métadonnée officielle (cahier §6) ; une incohérence entre métadonnée et titre est signalée, pas tranchée |
| 3 | Normaliser le titre | Rendre les règles insensibles à la casse, aux apostrophes typographiques et aux espaces, sans modifier le titre affiché |
| 4 | Évaluer R1 à R7 dans l'ordre ; relever **toutes** les règles qui correspondent | Détecter les titres ambigus |
| 5 | Si au moins deux règles de **catégories différentes** correspondent : `indetermine`, méthode `aucune`, `a_verifier = vrai`, avertissement `regles_en_conflit` (aucun cas observé) | Plutôt une catégorie « indéterminée » qu'un choix arbitraire entre deux lectures |
| 6 | Si une seule catégorie correspond : la retourner avec méthode `regle_titre`, `regle_id`, confiance `moyenne`, `a_verifier = vrai` | Le cahier §6 et la garantie 10 interdisent de présenter une catégorie déduite d'un titre comme une certitude |
| 7 | Si aucune règle ne correspond : `indetermine`, méthode `aucune`, confiance `aucune`, `a_verifier = vrai` | « Non déterminé » vaut mieux qu'une catégorie inventée |
| 8 | Ajouter `version_regles` à chaque résultat | La catégorie est reproductible : mêmes entrées et même version, mêmes résultats |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| « l’amendement n° 1972 de M. Davi à l’article 15 … » (apostrophes courbes) | `amendement` (R4) | étape 3 |
| « l'amendement n° 19 … à l'article 2 de la proposition de loi … » | `amendement`, pas `article` ni `texte_ensemble` | ancrage, ordre |
| « l'ensemble de la proposition de loi … (première lecture) » | `texte_ensemble` (R7) | cas nominal |
| « la proposition du Gouvernement de prolonger la séance … » | `procedure` (R3), pas `texte_ensemble` | « la proposition du » ≠ « la proposition de loi » |
| « la proposition de loi apportant une réponse … » (vote `SPS`) | `texte_ensemble` | R7 |
| « sur la motion de rejet préalable, déposée par … » | `motion_rejet` (R1 n'est pas ancrée) | libellé réel du scrutin 5156 |
| « la motion de censure déposée … » avec `MOC` | `motion_censure`, méthode `metadonnee_officielle` | étape 2 |
| `MOC` avec un titre qui ne parle pas de motion de censure | `motion_censure`, `a_verifier = vrai`, avertissement | étape 2 |
| « la déclaration de politique générale du Gouvernement … » | `autre` (R2) | pas une catégorie du vocabulaire propre |
| « la première partie du projet de loi de finances … » | `autre` (R6) | ni ensemble, ni article |
| Titre avec faute de frappe sans correction (« l'aticle 6 … ») | `indetermine` | étape 7 |
| Même titre avec correction validée | `article`, `correction_manuelle` | étape 1 |
| Correction dont le titre ne correspond plus | ignorée, avertissement | étape 1 |

## Exemples chiffrés (à reproduire en test)
Chaque règle a au moins un test sur un **vrai titre** et un test « presque correspondant » qui ne doit pas la déclencher (ex. « la proposition du Gouvernement… » pour R7). Les tests utilisent des fixtures extraites des vrais scrutins ; aucun titre fabriqué.

Sur l'ensemble des 8 877 scrutins (mesure du 2026-11-03, à confirmer par le test d'intégration), **sans** la table de corrections :

| Catégorie | Nombre |
|-----------|--------|
| `amendement` | 7 585 |
| `article` | 936 |
| `texte_ensemble` | 240 |
| `motion_rejet` | 58 |
| `motion_censure` | 23 |
| `procedure` | 18 |
| `autre` | 11 (R2 : 4, R6 : 7) |
| `indetermine` | 6 (scrutins 1633, 4988, 6214, 7432, 7950, 918) |
| `autre_motion` | 0 |
| Total | 8 877 |

Aucun conflit entre règles (0 titre correspondant à deux catégories). Avec les six corrections proposées (1633 → `amendement`, 4988 → `amendement`, 6214 → `amendement`, 7432 → `motion_rejet`, 7950 → `article`, 918 → `texte_ensemble`), `indetermine` tombe à 0.

## Ce que la catégorie ne dit pas
- `texte_ensemble` ne distingue pas un vote sur un texte en première lecture, en nouvelle lecture, en lecture définitive ou sur le texte d'une commission mixte paritaire : la lecture est dans le titre mais n'est pas extraite ici.
- Elle ne dit pas si le texte a été promulgué. Plusieurs scrutins peuvent concerner un même texte (cahier §6).
- Elle ne dit rien du sujet du texte.

## Invariants vérifiés
- Chaque scrutin reçoit exactement une catégorie du vocabulaire fermé.
- `a_verifier = faux` ⇒ méthode `metadonnee_officielle` ou `correction_manuelle`.
- Toute catégorie `indetermine` a `a_verifier = vrai` et méthode `aucune`.
- Sur les données réelles, aucun titre ne déclenche deux règles de catégories différentes (testé sur le corpus).
- Deux évaluations identiques donnent des résultats identiques.

## Questions à trancher avant de coder
1. **« À vérifier » et garantie 10.** Telle qu'écrite, la garantie 10 impose `a_verifier = vrai` pour toute catégorie déduite d'un titre : cette fiche l'applique, mais cela concerne 8 854 scrutins sur 8 877 (99,7 %, tout sauf les 23 motions de censure). Un badge « à vérifier » presque partout perdrait son sens. Je propose de **garder la donnée telle quelle** (`a_verifier` et `classification_confidence`) et de décider côté affichage : une mention générale sur le filtre (« catégories déduites des titres officiels ») plutôt qu'un badge par scrutin, et un badge réservé aux `indetermine` et aux incohérences. La garantie 10 devrait alors être reformulée. D'accord ?
2. **Sous-amendements** : classés `amendement` (vocabulaire fermé du cahier). Veux-tu une catégorie `sous_amendement` (654 scrutins) ? Cela modifierait le vocabulaire du cahier.
3. **Stockage** : la catégorie n'est pas stockée en base, elle est recalculée à l'export. Veux-tu des colonnes dans `scrutins` pour la consulter en SQL ?
4. **Les six corrections** : je les propose d'après le texte des titres (fautes de frappe évidentes). Elles doivent être validées par une personne.
5. **`autre`** regroupe pour l'instant les déclarations du Gouvernement et les parties de loi de finances ; veux-tu séparer ces deux cas ?

## Sources et constats
Cahier technique §6, `docs/methodology.md` (garantie 10), `.agents/CONVENTIONS.md` (« Règles de neutralité », dernier point), `.agents/DECISIONS.md` (2026-10-22 « Sujets et résumés ... »), `docs/analyse-donnees-sources.md` (point 6), mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction, règles établies à partir des 8 877 titres réels.
