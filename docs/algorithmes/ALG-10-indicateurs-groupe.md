# ALG-10 — Indicateurs de groupe (présence, part de la position majoritaire) et comparaison de deux groupes
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Calculer, pour un groupe et une sélection de scrutins, les seuls indicateurs autorisés par la décision du 2026-10-22 : la présence au scrutin (`E` sur effectif) et la part de la position majoritaire (`m` sur `E`), toujours sous forme d'effectifs avec leur dénominateur ; et décrire, pour deux groupes, sur quels scrutins ils ont la même position majoritaire. Aucun score, aucun classement, aucune moyenne présentée comme une note.

## Périmètre
Inclus : indicateurs par ligne (groupe, scrutin), agrégation sur une sélection, répartition de la part majoritaire, comparaison de deux groupes.
Exclus : calcul de la position majoritaire (ALG-03), mises au point (n'entrent dans aucun indicateur agrégé, voir étape 12), choix des sélections précalculées et écriture des fichiers (ALG-11), affichage et libellés (front).

## Règles de neutralité appliquées
- Toute valeur est un effectif suivi de son dénominateur (« n sur N ») ; les pourcentages, s'il y en a, sont calculés à l'affichage seulement.
- Pas de moyenne, pas de rang, pas de seuil qualifiant : aucun libellé du type « forte » ou « faible ». Les seuils d'une répartition sont des bornes numériques affichées telles quelles.
- Ordre des groupes : alphabétique (libellé, puis identifiant) ; jamais selon un indicateur.
- Les scrutins ne sont pas additionnés comme des lois distinctes : l'unité s'appelle « scrutin » (cahier §7).
- Les effectifs de plusieurs scrutins s'additionnent en **membres-scrutins** : un député présent à 10 scrutins compte 10 fois ; ce n'est pas un nombre de personnes.

## Constats (mesurés le 2026-11-03, 106 524 groupes-scrutins)
- 9 547 groupes-scrutins n'ont aucun vote exprimé ; 2 035 ont une égalité en tête (donc pas de position majoritaire) : cas fréquents, à afficher comme tels.
- 146 groupes-scrutins ont une référence non résolue : exclus de tous les indicateurs (ALG-02, question 1).
- `PO872880` (5 824 scrutins) et `PO847173` (3 041 scrutins) ne sont jamais présents dans le même scrutin (déduit des comptes : chaque scrutin a 12 groupes et les 11 autres références sont présentes partout, à confirmer par le test) : une comparaison de ces deux groupes n'a aucun scrutin commun (voir ALG-09).
- Effectif et participation varient d'un scrutin à l'autre (la source donne `nombreMembresGroupe` à la date de chaque scrutin) : on additionne les effectifs de chaque scrutin, on ne prend jamais « l'effectif actuel ».

## Entrées / Sorties
- Entrées : lignes `LigneGroupeScrutin` = `{scrutin_id, date_scrutin, categorie, resultat_code, type_vote_code, groupe_id, membres, pour, contre, abstentions, non_votants}` ; la sélection (liste d'identifiants de scrutins, ou filtres déjà appliqués, avec leur description lisible) ; sorties d'ALG-03 pour chaque ligne.
- Sortie, par groupe : `IndicateursGroupe` =

| Champ | Contenu |
|-------|---------|
| `groupe_id`, `filtres` | groupe et description de la sélection |
| `nb_scrutins` | nombre de scrutins retenus où le groupe est identifié |
| `nb_scrutins_exclus_groupe_non_identifie` | scrutins de la sélection écartés pour cette raison |
| `membres_scrutins` | Σ membres |
| `positions` | Σ pour, Σ contre, Σ abstentions, Σ non-votants, Σ sans vote enregistré |
| `exprimes` | Σ E (positions exprimées) |
| `scrutins_par_position_majoritaire` | nombre de scrutins : `pour`, `contre`, `abstention`, `egalite`, `aucun_vote_exprime` |
| `repartition_part_majoritaire` | nombre de scrutins dans chaque tranche B1 à B5 (voir ci-dessous) |

- Sortie, par couple de groupes : `ComparaisonGroupes` = `{groupe_a, groupe_b, filtres, scrutins_communs, meme_position, positions_differentes, au_moins_une_sans_position (avec détail par raison), scrutins_un_seul_present}` et la liste des scrutins de chaque classe avec les effectifs.

## Définitions
Pour une ligne (groupe, scrutin) : `p, c, a, n`, `membres`.
- `E = p + c + a` ; `N = n` ; `S = membres − (E + N)` : **sans vote enregistré** (méthodologie). `S ≥ 0` par ALG-05 R10.
- Présence : « `E` sur `membres` ». Les non-votants sont affichés à part.
- `m`, position majoritaire, raison d'absence : ALG-03.
- Part de la position majoritaire : « `m` sur `E` », définie seulement si une position majoritaire existe.

**Tranches de la part majoritaire** (comparaisons en entiers, jamais en flottants), pour les lignes qui ont une position majoritaire :

| Tranche | Condition |
|---------|-----------|
| B1 | `m = E` |
| B2 | `100·m ≥ 90·E` et `m < E` |
| B3 | `100·m ≥ 75·E` et `100·m < 90·E` |
| B4 | `2·m > E` et `100·m < 75·E` |
| B5 | `2·m ≤ E` (majorité relative sans majorité absolue) |

Les tranches B1 à B4 correspondent à `majorite_absolue` (ALG-03) ; B5 au cas contraire. Elles sont disjointes et couvrent toutes les lignes avec position majoritaire. Les seuils 90 et 75 sont des propositions (question 1).

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Retirer de la sélection les lignes dont `groupe_id` est nul ; les compter dans `nb_scrutins_exclus_groupe_non_identifie` | Un groupe non identifié ne peut pas être attribué à un groupe réel (aucune inférence) |
| 2 | Regrouper les lignes restantes par `groupe_id` | Un indicateur = un groupe |
| 3 | Pour chaque ligne : refuser (erreur de donnée) si `membres ≤ 0`, ou si un compteur est négatif, ou si `E + N > membres` | Indicateur absurde = on ne calcule pas (ALG-03 étape 2, ALG-05 R10) |
| 4 | Pour chaque ligne : calculer `E`, `S`, puis appeler ALG-03 sur `(p, c, a)` pour obtenir position, raison d'absence et `m` | Une seule définition de la position majoritaire dans tout le projet |
| 5 | `nb_scrutins` ← nombre de lignes du groupe | Dénominateur affiché partout |
| 6 | Sommer `membres`, `p`, `c`, `a`, `n`, `S`, `E` sur les lignes | Effectifs bruts : « n sur N » ; la somme est en membres-scrutins |
| 7 | Compter les lignes par position majoritaire : `pour`, `contre`, `abstention`, et pour « aucune » séparément `egalite` et `aucun_vote_exprime` | Cahier §7 : nombre de scrutins par position, calculé séparément de la répartition des positions individuelles |
| 8 | Pour chaque ligne ayant une position majoritaire : l'affecter à la tranche B1 à B5 | Répartition brute de la part majoritaire, jamais une moyenne (méthodologie) |
| 9 | Retourner `IndicateursGroupe`, groupes triés par libellé puis identifiant | Ordre non évaluatif |
| 10 | **Comparaison** de `a` et `b` : retenir les scrutins où les deux ont une ligne (groupes identifiés) ; le reste est compté dans `scrutins_un_seul_present` | On ne compare que ce qui est comparable |
| 11 | Classer chaque scrutin commun : `meme_position` si les deux ont une position et qu'elle est identique ; `positions_differentes` si les deux ont une position et qu'elles diffèrent ; `au_moins_une_sans_position` sinon, avec la raison de chaque groupe | La raison de l'absence de position (égalité ou aucun vote) est toujours donnée (revue de maquette, écart n° 4) |
| 12 | Les mises au point n'entrent dans aucun calcul de cette fiche ; seules les valeurs officielles sont utilisées | Les chiffres officiels ne sont jamais modifiés (méthodologie, règle 5) |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Sélection vide | `nb_scrutins = 0`, sommes à 0, tranches à 0 ; l'interface affiche « aucun scrutin retenu » | pas de division |
| Un seul scrutin | indicateurs sur ce scrutin | cas normal |
| Groupe sans aucun vote exprimé sur tous les scrutins | `exprimes = 0`, tous les scrutins en `aucun_vote_exprime`, tranches à 0 | aucune part à calculer |
| `membres = 0` | erreur de donnée | étape 3 |
| Ligne avec groupe non identifié | exclue, comptée | étape 1 |
| Deux groupes sans scrutin commun (`PO872880` et `PO847173`) | `scrutins_communs = 0`, `scrutins_un_seul_present = 8 865` | étape 10 |
| Égalité d'un côté, position de l'autre | `au_moins_une_sans_position`, raison `egalite` | étape 11 |
| Sélection qui contient des scrutins de catégories ou de types différents | acceptée ; les filtres sont recopiés dans le résultat | transparence (cahier §7) |

## Exemples chiffrés (arithmétique construite, à reproduire en test)
Cinq lignes d'un groupe (cas construits pour tester l'arithmétique, pas des résultats parlementaires) :

| Scrutin | p | c | a | n | membres | E | S | Position majoritaire | Tranche |
|---------|---|---|---|---|---------|---|---|----------------------|---------|
| s1 | 12 | 2 | 0 | 1 | 20 | 14 | 5 | pour (m = 12) | B3 (1 200 ≥ 1 050 ; 1 200 < 1 260) |
| s2 | 5 | 6 | 49 | 0 | 70 | 60 | 10 | abstention (m = 49) | B3 (4 900 ≥ 4 500 ; 4 900 < 5 400) |
| s3 | 6 | 6 | 1 | 0 | 15 | 13 | 2 | aucune (égalité) | — |
| s4 | 3 | 2 | 2 | 0 | 8 | 7 | 1 | pour (m = 3) | B5 (2·3 = 6 ≤ 7) |
| s5 | 0 | 0 | 0 | 2 | 10 | 0 | 8 | aucune (aucun vote exprimé) | — |

Agrégat attendu : `nb_scrutins = 5` ; `membres_scrutins = 123` ; Σ pour 26, Σ contre 16, Σ abstentions 52, Σ non-votants 3, Σ sans vote enregistré 26 ; `exprimes = 94` ; vérification : 94 + 3 + 26 = 123. Par position : pour 2, contre 0, abstention 1, égalité 1, aucun vote exprimé 1 (total 5). Tranches : B1 0, B2 0, B3 2, B4 0, B5 1 (3 lignes avec position).

Comparaison de deux groupes sur 4 scrutins communs : positions de A (pour, abstention, égalité, pour) ; positions de B (pour, contre, pour, aucun vote exprimé) → `meme_position` 1 (scrutin 1) ; `positions_differentes` 1 (scrutin 2) ; `au_moins_une_sans_position` 2 (scrutin 3 : A égalité ; scrutin 4 : B aucun vote exprimé) ; total 4.

Sur l'archive réelle : valeurs à établir par le test d'intégration, par exemple pour chaque groupe `nb_scrutins` doit égaler le nombre de scrutins où il est identifié ; pour tous groupes identifiés confondus, la somme des `nb_scrutins` est inférieure ou égale à 106 378 (106 524 − 146) ; toute différence doit s'expliquer par la sélection.

## Invariants vérifiés
- `Σ pour + Σ contre + Σ abstentions = exprimes`.
- `exprimes + Σ non-votants + Σ sans vote enregistré = membres_scrutins`.
- Somme des `scrutins_par_position_majoritaire` (5 valeurs) = `nb_scrutins`.
- Somme des tranches B1 à B5 = `pour + contre + abstention` des `scrutins_par_position_majoritaire` (lignes avec position).
- `meme_position + positions_differentes + au_moins_une_sans_position = scrutins_communs`.
- Aucun indicateur ne dépend de l'ordre d'entrée des lignes.
- **Conformité inter-langages** : la comparaison de groupes est recalculée dans le navigateur (cahier §8). Un jeu de vecteurs de test (entrées et sorties, dont les exemples ci-dessus) est généré par l'ETL et rejoué par les tests du front (Vitest) pour garantir que les deux implémentations donnent les mêmes valeurs.

## Questions à trancher avant de coder
1. **Seuils des tranches** (90 % et 75 %) : propositions fondées sur l'exemple de la méthodologie (« au moins 90 % »). D'autres bornes ? Elles ne doivent être associées à aucun qualificatif.
2. **Unité « membres-scrutins »** : acceptable pour l'affichage (« 94 positions exprimées sur 123 présences possibles sur 5 scrutins ») ? Le nombre de personnes distinctes n'est pas calculé.
3. **Sélections précalculées** pour `stats.json` : toutes les sélections, ou aussi par catégorie et par année ? Voir ALG-11.
4. **Groupe renommé ou remplacé** (`PO872880` et `PO847173`) : aucun indicateur combiné ; deux groupes distincts. D'accord ?

## Sources et constats
`.agents/DECISIONS.md` (2026-10-22 « Indicateurs sur les groupes »), `docs/methodology.md` (indicateurs, présence, sans vote enregistré), cahier technique §7 et §8, `docs/revue-maquette.md` (écarts n° 1 et 4), fiches ALG-02, 03, 05, mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction.
