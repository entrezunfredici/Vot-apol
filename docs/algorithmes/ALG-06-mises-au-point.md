# ALG-06 — Mises au point : rattachement au groupe et à la position initiale, effectifs corrigés
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Pour chaque rectification de vote déclarée après le scrutin (`miseAuPoint`) : retrouver, dans les votes nominatifs du même scrutin, le groupe du député et sa position enregistrée ; puis, pour l'affichage, calculer les effectifs corrigés d'un groupe et dire si la position majoritaire change. Les chiffres officiels ne sont jamais modifiés, et un député introuvable n'est jamais rattaché par déduction.

## Périmètre
Inclus : rattachement, qualification de l'effet, effectifs corrigés par groupe, signalement d'un changement de position majoritaire.
Exclus : lecture et normalisation des mises au point (ALG-02), création des lignes (ALG-04), position majoritaire (ALG-03, appelée telle quelle), mise en page de l'encart (front).
Deux temps : **A. rattachement** (à l'import, avant écriture) ; **B. effectifs corrigés** (à l'export, ALG-11, sans stockage).

## Constats (mesurés le 2026-11-03 sur les 8 877 fichiers)
- 3 243 lignes de mises au point dans 1 534 scrutins ; 163 lignes de dysfonctionnement.
- Mises au point : **2 389 rattachables** (député présent dans les votes nominatifs du scrutin), **854 introuvables** (26 %). Sur les rattachables, 2 déclarent la position déjà enregistrée (sans effet).
- Dysfonctionnements : **148 introuvables sur 163** (91 %). Ces députés n'ont en général pas de vote enregistré, ce qui est cohérent avec un boîtier défaillant.
- Aucun député n'a deux lignes dans le même scrutin, et aucun n'est à la fois dans une mise au point et un dysfonctionnement.
- En appliquant la règle de l'étape 7 à toutes les mises au point rattachables : **171 couples (groupe, scrutin) sur 106 524** changent de position majoritaire, y compris les passages à « aucune position » ou depuis « aucune position ». Sur l'échantillon de 600 scrutins de `docs/methodology.md`, 7 cas sur 7 189 : même ordre de grandeur (attendu : environ 11 sur ce sous-ensemble). **Cette mesure est un premier calcul, non un résultat vérifié** : elle sera refaite par l'implémentation.

## Entrées / Sorties
- Entrées : `LotScrutin` (ALG-04) d'un scrutin, avec ses lignes `scrutin_group_votes`, `scrutin_individual_votes`, `scrutin_mises_au_point`.
- Sorties :
  - A : le même lot dont les lignes `scrutin_mises_au_point` ont `groupe_rang`, `groupe_id` et `position_initiale` renseignés lorsque le député est retrouvé, plus un `statut_rattachement` calculé (`rattachee` | `introuvable`) et un `effet` (`sans_effet` | `modifie_position`) ;
  - B : liste `CorrectionGroupe` = `{rang, groupe_id, pour_corrige, contre_corrige, abstentions_corrigees, position_officielle, position_corrigee, raison_absence_corrigee, change_resultat, nb_mises_au_point}`, pour les seuls groupes identifiés qui ont au moins une mise au point rattachée à effet.

## Définitions
- Position initiale d'un député : sa position dans `scrutin_individual_votes` du même scrutin (`pour`, `contre`, `abstention`, `non_votant`).
- Position déclarée : `position_declaree` de la mise au point (`pour`, `contre`, `abstention`, `non_votant`, `non_votant_volontaire`).
- Position exprimée : `pour`, `contre` ou `abstention`. `non_votant` et `non_votant_volontaire` ne sont **pas** des positions exprimées (règle du projet : un non-vote n'est pas une abstention).
- Mise au point **à effet** : rattachée, d'origine `mise_au_point`, et dont la position déclarée diffère de la position initiale.
- Effectifs corrigés d'un groupe : `p' = p − (nombre de mises au point à effet dont la position initiale est pour) + (nombre dont la position déclarée est pour)` ; même formule pour `c'` et `a'`.
- `change_resultat` ⇔ `position_corrigee ≠ position_officielle` (le passage de « aucune » à une position, ou l'inverse, compte).

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | **A.** Construire l'index `depute_id → (groupe_rang, groupe_id, position)` à partir des lignes `scrutin_individual_votes` du scrutin | Le groupe et la position initiale se lisent dans le scrutin, jamais dans l'affiliation actuelle (cahier §2) |
| 2 | **A.** Pour chaque ligne de `scrutin_mises_au_point` : si le député est dans l'index, copier `groupe_rang`, `groupe_id`, `position_initiale` ; sinon laisser `NULL` | Aucun rattachement par inférence ; l'absence est une information |
| 3 | **A.** `statut_rattachement` = `rattachee` si le député est trouvé, sinon `introuvable` | Les introuvables sont listés à part sur le site (méthodologie, règle 4) |
| 4 | **A.** Pour une ligne rattachée : `effet` = `sans_effet` si `position_declaree = position_initiale`, sinon `modifie_position` | Une mise au point qui redit la position enregistrée ne change rien et ne doit pas être comptée comme une rectification |
| 5 | **A.** Pour une ligne d'origine `dysfonctionnement` : mêmes étapes 2 à 4, mais elle est **exclue** de l'étape 7 | Un dysfonctionnement n'est pas une rectification d'un vote enregistré ; la méthodologie le tient pour une information distincte (voir question 2) |
| 6 | **B.** Regrouper les lignes à effet d'origine `mise_au_point` par `groupe_rang` ; ignorer les groupes dont `groupe_id` est `NULL` | La ventilation d'un groupe non identifié est « indisponible » (ALG-02, question 1) : on n'en tire aucun indicateur |
| 7 | **B.** Pour chaque groupe retenu, partir de `p, c, a` (compteurs officiels du groupe) ; pour chaque mise au point à effet : retirer 1 à l'effectif de la position initiale si elle est exprimée ; ajouter 1 à l'effectif de la position déclarée si elle est exprimée | La position non exprimée n'a pas d'effectif à ajuster ; une personne ne change d'effectif que si elle est ou devient « exprimée » |
| 8 | **B.** Calculer `position_corrigee` en appliquant ALG-03 à `(p', c', a')` ; `position_officielle` en l'appliquant à `(p, c, a)` | Une seule règle de calcul pour les deux cas, donc comparable |
| 9 | **B.** `change_resultat` ← `position_corrigee ≠ position_officielle` (comparaison de la position, pas des effectifs) | Le signalement « Une mise au point modifie ce résultat » ne s'affiche que si la position majoritaire change |
| 10 | **B.** Vérifier `p', c', a' ≥ 0` ; sinon erreur de donnée (ne devrait jamais arriver si ALG-05 R09 est satisfait) | Un effectif négatif signalerait un défaut de rattachement ou de réconciliation |
| 11 | Retourner les lignes complétées (A) et la liste des corrections (B, triée par `rang`) ; aucune écriture, aucune modification des compteurs officiels | Garantie : les chiffres officiels ne sont pas modifiés ; les effectifs corrigés ne sont jamais présentés comme officiels (méthodologie, règle 5) |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Député absent des votes nominatifs | `introuvable`, `NULL` partout, listé à part | étape 3 |
| `position_declaree = position_initiale` | `sans_effet`, ignorée pour les effectifs corrigés | étape 4 |
| Position initiale `non_votant` (cause `MG`, `PSE`, `PAN`) et déclarée exprimée | on ajoute 1 à la position déclarée, rien à retirer | étape 7 |
| Position déclarée `non_votant` ou `non_votant_volontaire`, initiale exprimée | on retire 1 à la position initiale, rien à ajouter | étape 7 |
| Groupe `PO0` (non identifié) | lignes rattachées au rang, aucune correction produite | étape 6 |
| Plusieurs mises au point dans un même groupe | cumulées dans le même groupe | étape 7 |
| Dysfonctionnement rattaché | complété (groupe, position initiale), jamais appliqué aux effectifs | étape 5 |
| Scrutin sans mise au point | lot inchangé, liste de corrections vide | cas normal (7 343 scrutins) |

## Exemples chiffrés (arithmétique construite, à reproduire en test)
Ces cas sont des cas **construits** qui testent l'arithmétique de l'étape 7, pas des résultats parlementaires. Des cas réels seront ajoutés après examen des 171 cas mesurés.

| Groupe officiel (p, c, a) | Mises au point à effet | Corrigé (p', c', a') | Position officielle → corrigée | `change_resultat` |
|---------------------------|------------------------|----------------------|--------------------------------|-------------------|
| (5, 5, 0) | 1 député `contre` → `pour` | (6, 4, 0) | aucune (égalité) → pour | vrai |
| (12, 2, 0) | 1 député `contre` → `pour` | (13, 1, 0) | pour → pour | faux |
| (3, 2, 0) | 1 député `pour` → `non_votant_volontaire` | (2, 2, 0) | pour → aucune (égalité) | vrai |
| (3, 2, 2) | 1 député `non_votant` (cause `MG`) → `contre` | (3, 3, 2) | pour → aucune (égalité) | vrai |
| (1, 0, 0) | 1 député `pour` → `contre` | (0, 1, 0) | pour → contre | vrai |
| (4, 0, 0) | 1 député `pour` → `pour` | (4, 0, 0) | `sans_effet` | faux |

Mesures sur l'archive réelle (à confirmer par le test d'intégration) : 2 389 lignes rattachées, 854 introuvables, dont 2 sans effet ; dysfonctionnements : 15 rattachés, 148 introuvables.

## Invariants vérifiés
- Les compteurs officiels (`p, c, a, n` et totaux) ne sont jamais modifiés.
- Après correction, `p', c', a' ≥ 0` ; `p' + c' + a' = (p + c + a) − (nombre de mises au point à effet dont l'initiale est exprimée) + (nombre de celles dont la déclarée est exprimée)`.
- `rattachee + introuvable` = nombre de lignes de `scrutin_mises_au_point`.
- Une ligne `introuvable` n'a jamais de groupe ni de position initiale.

## Questions à trancher avant de coder
1. **Position `non_votant_volontaire` déclarée** : je la traite comme « n'a pas pris part au vote », donc retirée des positions exprimées sans être ajoutée ailleurs. Autre lecture possible : à écarter. Cette lecture engage l'affichage. D'accord ?
2. **Dysfonctionnements** : stockés et affichés dans un bloc distinct, non appliqués aux effectifs corrigés (décision du 2026-10-22 : « à étudier »). Sur les données : 148 sur 163 sont introuvables. D'accord pour ne jamais les appliquer ?
3. **Colonne `groupe_rang`** à ajouter à `scrutin_mises_au_point` : un groupe `PO0` ne peut pas être désigné par `groupe_id` (ALG-04). D'accord ?
4. **Mises au point d'un député « sans vote enregistré »** (854 introuvables) : elles restent hors de tout groupe. On ne cherche pas à les rattacher par l'affiliation actuelle, par décision du projet. Confirmes-tu ?
5. **Effectifs de non-votants (n)** : non recalculés après correction. Le site n'affiche les effectifs corrigés que pour pour, contre, abstention. D'accord ?

## Sources et constats
`docs/methodology.md` (« Mises au point »), `.agents/DECISIONS.md` (2026-10-22 « Mises au point »), cahier technique §4 (`scrutin_mises_au_point`), `docs/algorithmes/ALG-02-normalisation.md` (étapes 21 et 22), `docs/algorithmes/ALG-03-position-majoritaire.md`, mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction.
