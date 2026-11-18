# ALG-10 — Indicateurs de groupe (participation au vote enregistrée, part de la position majoritaire) et comparaison de deux groupes
Statut : Validé    Version : 3    Date : 2026-11-18

## But
Calculer, pour un groupe et une sélection de scrutins, les seuls indicateurs autorisés par la décision du 2026-10-22 : la participation au vote enregistrée (`E` sur effectif) et la part de la position majoritaire (`m` sur `E`), toujours sous forme d'effectifs avec leur dénominateur ; et décrire, pour deux groupes, sur quels scrutins ils ont la même position majoritaire. Aucun score, aucun classement, aucune moyenne présentée comme une note.

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
- `PO872880` (5 824 scrutins) et `PO847173` (3 041 scrutins) ne sont jamais présents dans le même scrutin : une comparaison de ces deux groupes n'a aucun scrutin commun. Le référentiel officiel (inspecté le 2026-11-14, voir ALG-09) les décrit comme deux organes distincts, de même sigle `UDR` : `PO847173` « UDR » du 2024-09-12 au 2025-09-04, puis `PO872880` « Union des droites pour la République » depuis le 2025-09-05. Aucun champ ne les relie explicitement : ils restent deux groupes distincts, sans indicateur combiné.
- Effectif et participation varient d'un scrutin à l'autre (la source donne `nombreMembresGroupe` à la date de chaque scrutin) : on additionne les effectifs de chaque scrutin, on ne prend jamais « l'effectif actuel ».

## Entrées / Sorties
- Entrées : lignes `LigneGroupeScrutin` = `{scrutin_id, date_scrutin, categorie, resultat_code, type_vote_code, groupe_id, membres, pour, contre, abstentions, non_votants}` ; lignes de vote `{scrutin_id, groupe_id, depute_id, position}` de la sélection (pour les personnes distinctes) ; paramètre `bornes` (défaut `[20, 40, 60, 80]`) ; la sélection (liste d'identifiants de scrutins, ou filtres déjà appliqués, avec leur description lisible) ; sorties d'ALG-03 pour chaque ligne.
- Sortie, par groupe : `IndicateursGroupe` =

| Champ | Contenu |
|-------|---------|
| `groupe_id`, `filtres` | groupe et description de la sélection |
| `nb_scrutins` | nombre de scrutins retenus où le groupe est identifié |
| `nb_scrutins_exclus_groupe_non_identifie` | scrutins de la sélection écartés pour cette raison |
| `membres_scrutins` | Σ membres |
| `personnes_exprimees`, `personnes_avec_vote` | nombres de personnes distinctes (voir Définitions) ; calculés à partir des lignes de vote nominatif de la sélection |
| `positions` | Σ pour, Σ contre, Σ abstentions, Σ non-votants, Σ sans vote enregistré |
| `exprimes` | Σ E (positions exprimées) |
| `scrutins_par_position_majoritaire` | nombre de scrutins : `pour`, `contre`, `abstention`, `egalite`, `aucun_vote_exprime` |
| `repartition_part_majoritaire` | nombre de scrutins dans chaque tranche P1 à P`k+2` (voir ci-dessous) ; `bornes` utilisées recopiées |

- Sortie, par couple de groupes : `ComparaisonGroupes` = `{groupe_a, groupe_b, filtres, scrutins_communs, meme_position, positions_differentes, au_moins_une_sans_position (avec détail par raison), scrutins_un_seul_present}` et la liste des scrutins de chaque classe avec les effectifs.

## Définitions
Pour une ligne (groupe, scrutin) : `p, c, a, n`, `membres`.
- `E = p + c + a` ; `N = n` ; `S = membres − (E + N)` : **sans vote enregistré** (méthodologie). `S ≥ 0` par ALG-05 R10.
- Personnes distinctes (sur une sélection de scrutins, pour un groupe) : `personnes_exprimees` = nombre de `depute_id` distincts ayant au moins une ligne de vote `pour`, `contre` ou `abstention` ; `personnes_avec_vote` = nombre de `depute_id` distincts ayant au moins une ligne de vote, quelle que soit la position. Un député qui a voté dans deux groupes est compté dans chacun (l'affiliation est celle du scrutin). Les députés « sans vote enregistré » ne figurent dans aucune liste : leur nombre de personnes n'est pas calculable, seulement leur nombre de membres-scrutins `S`.
- Participation au vote enregistrée : « `E` sur `membres` ». **Ce n'est pas une présence physique** : `E` inclut les votes par délégation (`parDelegation = vrai`, 55 lignes sur 1 244 dans les six fixtures). Le libellé affiché doit le dire. Les non-votants sont affichés à part.
- `m`, position majoritaire, raison d'absence : ALG-03.
- Part de la position majoritaire : « `m` sur `E` », définie seulement si une position majoritaire existe.

**Tranches de la part majoritaire** (décision du 2026-11-14). Elles sont **réglables** par un paramètre `bornes` : liste strictement croissante d'entiers de pourcentage, comprise entre 1 et 99. Valeur par défaut : `bornes = [20, 40, 60, 80]`. Comparaisons en entiers, jamais en flottants ; pour les lignes qui ont une position majoritaire (`E > 0`) :

| Tranche | Condition (défaut) | Libellé affiché (bornes numériques seules) |
|---------|--------------------|--------------------------------------------|
| P1 | `100·m < 20·E` | moins de 20 % |
| P2 | `20·E ≤ 100·m < 40·E` | de 20 % à moins de 40 % |
| P3 | `40·E ≤ 100·m < 60·E` | de 40 % à moins de 60 % |
| P4 | `60·E ≤ 100·m < 80·E` | de 60 % à moins de 80 % |
| P5 | `80·E ≤ 100·m` et `m < E` | de 80 % à moins de 100 % |
| P6 | `m = E` | 100 % (unanime) |

Avec `k` bornes il y a `k + 2` tranches : une tranche inférieure, `k - 1` tranches intermédiaires, une tranche « de `bk` % à moins de 100 % » et la tranche « 100 % ». Les bornes sont des entiers ; chaque borne appartient à la tranche qui commence à cette borne (intervalles semi-ouverts, choix à confirmer). Les tranches sont disjointes et couvrent toutes les lignes avec position majoritaire.

**Neutralité** : les libellés sont les bornes, **sans qualificatif** (« très faible », « élevé »…) ; la décision du 2026-10-22 est maintenue. Les bornes utilisées sont recopiées dans le résultat.

**Remarque d'arithmétique (à connaître avant d'afficher)** : une position majoritaire est stricte (ALG-03), donc `m > E/3` : une part inférieure à 33,4 % est **impossible**. Avec les bornes par défaut, **P1 (moins de 20 %) est toujours vide** et P2 ne contient que les parts entre 33,4 % et 40 %. C'est un fait de la définition, pas une anomalie : l'interface peut masquer les tranches structurellement vides, ou le responsable peut régler `bornes` (par exemple `[40, 50, 60, 80]`).

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Aucun score, aucun classement : seulement des effectifs avec leur dénominateur.

```text
# Notations
lignes = Data[x]          # lignes (groupe, scrutin) de la sélection : membres, p, c, a, n
exclus = lignes dont groupe_id est null                                            [1]
lignes = lignes \ exclus   # compteur : nb_scrutins_exclus_groupe_non_identifie
par_groupe = regrouper lignes par groupe_id                                        [2]

pour chaque groupe g (trié par libellé, puis identifiant):                         [9]
    pour chaque ligne l de g:
        si l.membres ≤ 0 ou un compteur < 0 ou E + n > l.membres: erreur de donnée    [3]
        E = l.p + l.c + l.a                      # positions exprimées
        S = l.membres − (E + l.n)                # sans vote enregistré, S ≥ 0
        (position, raison, m) = ALG-03(l.p, l.c, l.a)                              [4]
        si position existe:
            tranche = P6 si m = E
                      sinon la tranche i telle que bornes[i-1]·E ≤ 100·m < bornes[i]·E
                            (P1 : 100·m < bornes[0]·E ; P5 : 100·m ≥ bornes[-1]·E, m < E)   [8]
    nb_scrutins   = |lignes de g|                                                  [5]
    Σ membres, Σ p, Σ c, Σ a, Σ n, Σ S, Σ E                                        [6]
    personnes_exprimees = |{depute_id des lignes pour/contre/abstention du groupe}|   [6b]
    personnes_avec_vote = |{depute_id de toutes les lignes de vote du groupe}|
    scrutins_par_position = compter par (pour, contre, abstention, egalite, aucun_vote_exprime)   [7]
    afficher "participation au vote enregistrée (délégations incluses) : " + ΣE + " sur " + Σmembres + " (" + nb_scrutins + " scrutins, " + personnes_exprimees + " personnes distinctes)"
    afficher "position majoritaire : pour " + n_pour + " scrutins, contre " + n_contre + " …"

# Comparaison de deux groupes a et b                                               [10]
communs = { scrutins où a ET b ont une ligne }
un_seul = scrutins où un seul des deux est présent                                  # compté à part
pour chaque scrutin s de communs:                                                   [11]
    si pos_a(s) et pos_b(s) existent:
        si pos_a(s) = pos_b(s):  classe = "meme_position"
        sinon:                   classe = "positions_differentes"
    sinon:
        classe = "au_moins_une_sans_position"  avec raison_a(s), raison_b(s)
    # exemple : A = égalité, B = pour → au_moins_une_sans_position (raison "egalite")
# les mises au point n'interviennent jamais ici                                     [12]
```

Relations (entiers) : `Σ p + Σ c + Σ a = exprimes` ; `exprimes + Σ n + Σ S = Σ membres` ; la somme des 5 valeurs de `scrutins_par_position` = `nb_scrutins` ; `meme_position + positions_differentes + au_moins_une_sans_position = scrutins_communs`. Les membres-scrutins s'additionnent (un député présent à 10 scrutins compte 10 fois) ; `personnes_exprimees ≤ exprimes`, `personnes_avec_vote ≤ membres_scrutins`, et `personnes_exprimees ≥ 1` dès que `exprimes ≥ 1`. Exemple de la fiche : 5 scrutins, 123 membres-scrutins, 94 exprimés, 3 non-votants, 26 sans vote enregistré (94 + 3 + 26 = 123).

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Retirer de la sélection les lignes dont `groupe_id` est nul ; les compter dans `nb_scrutins_exclus_groupe_non_identifie` | Un groupe non identifié ne peut pas être attribué à un groupe réel (aucune inférence) |
| 2 | Regrouper les lignes restantes par `groupe_id` | Un indicateur = un groupe |
| 3 | Pour chaque ligne : refuser (erreur de donnée) si `membres ≤ 0`, ou si un compteur est négatif, ou si `E + N > membres` | Indicateur absurde = on ne calcule pas (ALG-03 étape 2, ALG-05 R10) |
| 4 | Pour chaque ligne : calculer `E`, `S`, puis appeler ALG-03 sur `(p, c, a)` pour obtenir position, raison d'absence et `m` | Une seule définition de la position majoritaire dans tout le projet |
| 5 | `nb_scrutins` ← nombre de lignes du groupe | Dénominateur affiché partout |
| 6 | Sommer `membres`, `p`, `c`, `a`, `n`, `S`, `E` sur les lignes ; compter les personnes distinctes (`personnes_exprimees`, `personnes_avec_vote`) sur les lignes de vote du groupe | Effectifs bruts : « n sur N » ; la somme est en membres-scrutins, complétée par un nombre de personnes (décision du 2026-11-14) |
| 7 | Compter les lignes par position majoritaire : `pour`, `contre`, `abstention`, et pour « aucune » séparément `egalite` et `aucun_vote_exprime` | Cahier §7 : nombre de scrutins par position, calculé séparément de la répartition des positions individuelles |
| 8 | Pour chaque ligne ayant une position majoritaire : l'affecter à la tranche P1 à P`k+2` selon `bornes` (entiers : `bornes[i]·E` comparé à `100·m`) | Répartition brute de la part majoritaire, jamais une moyenne (méthodologie) ; bornes réglables, libellés sans qualificatif |
| 9 | Retourner `IndicateursGroupe`, groupes triés par libellé puis identifiant | Ordre non évaluatif |
| 10 | **Comparaison** de `a` et `b` : retenir les scrutins où les deux ont une ligne (groupes identifiés) ; le reste est compté dans `scrutins_un_seul_present` | On ne compare que ce qui est comparable |
| 11 | Classer chaque scrutin commun : `meme_position` si les deux ont une position et qu'elle est identique ; `positions_differentes` si les deux ont une position et qu'elles diffèrent ; `au_moins_une_sans_position` sinon, avec la raison de chaque groupe | La raison de l'absence de position (égalité ou aucun vote) est toujours donnée (revue de maquette, écart n° 4) |
| 12 | Les mises au point n'entrent dans aucun calcul de cette fiche ; seules les valeurs officielles sont utilisées | Les chiffres officiels ne sont jamais modifiés (méthodologie, règle 5) |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Sélection vide | `nb_scrutins = 0`, sommes à 0, personnes à 0, tranches à 0 ; l'interface affiche « aucun scrutin retenu » | pas de division |
| Un seul scrutin | indicateurs sur ce scrutin | cas normal |
| Groupe sans aucun vote exprimé sur tous les scrutins | `exprimes = 0`, tous les scrutins en `aucun_vote_exprime`, tranches à 0 | aucune part à calculer |
| `membres = 0` | erreur de donnée | étape 3 |
| Ligne avec groupe non identifié | exclue, comptée | étape 1 |
| Deux groupes sans scrutin commun (`PO872880` et `PO847173`) | `scrutins_communs = 0`, `scrutins_un_seul_present = 8 865` | étape 10 |
| Égalité d'un côté, position de l'autre | `au_moins_une_sans_position`, raison `egalite` | étape 11 |
| `bornes` invalides (non croissantes, hors 1-99, doublon, vide) | erreur de paramètre, aucun calcul | étape 8 |
| Sélection qui contient des scrutins de catégories ou de types différents | acceptée ; les filtres sont recopiés dans le résultat | transparence (cahier §7) |

## Exemples chiffrés (arithmétique construite, à reproduire en test)
Cinq lignes d'un groupe (cas construits pour tester l'arithmétique, pas des résultats parlementaires) :

| Scrutin | p | c | a | n | membres | E | S | Position majoritaire | Tranche |
|---------|---|---|---|---|---------|---|---|----------------------|---------|
| s1 | 12 | 2 | 0 | 1 | 20 | 14 | 5 | pour (m = 12) | P5 (1 200 ≥ 80·14 = 1 120 ; m < E) |
| s2 | 5 | 6 | 49 | 0 | 70 | 60 | 10 | abstention (m = 49) | P5 (4 900 ≥ 80·60 = 4 800 ; m < E) |
| s3 | 6 | 6 | 1 | 0 | 15 | 13 | 2 | aucune (égalité) | — |
| s4 | 3 | 2 | 2 | 0 | 8 | 7 | 1 | pour (m = 3) | P3 (40·7 = 280 ≤ 300 < 60·7 = 420) |
| s5 | 0 | 0 | 0 | 2 | 10 | 0 | 8 | aucune (aucun vote exprimé) | — |

Agrégat attendu : `nb_scrutins = 5` ; `membres_scrutins = 123` ; Σ pour 26, Σ contre 16, Σ abstentions 52, Σ non-votants 3, Σ sans vote enregistré 26 ; `exprimes = 94` ; vérification : 94 + 3 + 26 = 123. Par position : pour 2, contre 0, abstention 1, égalité 1, aucun vote exprimé 1 (total 5). Tranches (défaut) : P1 0, P2 0, P3 1, P4 0, P5 2, P6 0 (3 lignes avec position). Un cas unanime (p = 1, c = 0, a = 0) tombe en P6 ; avec `bornes = [50]` (trois tranches : P1 moins de 50 %, P2 de 50 % à moins de 100 %, P3 100 %), s1 et s2 donnent P2 et s4 donne P1.

Personnes distinctes (exemple construit, un groupe, 3 scrutins, députés d1 à d4) : s1 : d1 pour, d2 pour, d3 contre ; s2 : d1 contre, d4 abstention ; s3 : d2 non-votant. Attendu : `exprimes = 5` (membres-scrutins), `personnes_exprimees = 4` (d1, d2, d3, d4), `personnes_avec_vote = 4`.

Comparaison de deux groupes sur 4 scrutins communs : positions de A (pour, abstention, égalité, pour) ; positions de B (pour, contre, pour, aucun vote exprimé) → `meme_position` 1 (scrutin 1) ; `positions_differentes` 1 (scrutin 2) ; `au_moins_une_sans_position` 2 (scrutin 3 : A égalité ; scrutin 4 : B aucun vote exprimé) ; total 4.

Sur l'archive réelle : valeurs à établir par le test d'intégration, par exemple pour chaque groupe `nb_scrutins` doit égaler le nombre de scrutins où il est identifié ; pour tous groupes identifiés confondus, la somme des `nb_scrutins` est inférieure ou égale à 106 378 (106 524 − 146) ; toute différence doit s'expliquer par la sélection.

## Invariants vérifiés
- `Σ pour + Σ contre + Σ abstentions = exprimes`.
- `exprimes + Σ non-votants + Σ sans vote enregistré = membres_scrutins`.
- Somme des `scrutins_par_position_majoritaire` (5 valeurs) = `nb_scrutins`.
- Somme des tranches P1 à P`k+2` = `pour + contre + abstention` des `scrutins_par_position_majoritaire` (lignes avec position) ; P1 est vide quand `bornes[0] ≤ 33` (part minimale 33,4 %).
- `personnes_exprimees ≤ exprimes` ; `personnes_avec_vote ≤ membres_scrutins`.
- `meme_position + positions_differentes + au_moins_une_sans_position = scrutins_communs`.
- Aucun indicateur ne dépend de l'ordre d'entrée des lignes.
- **Conformité inter-langages** : la comparaison de groupes est recalculée dans le navigateur (cahier §8). Un jeu de vecteurs de test (entrées et sorties, dont les exemples ci-dessus) est généré par l'ETL et rejoué par les tests du front (Vitest) pour garantir que les deux implémentations donnent les mêmes valeurs.

## Décisions (2026-11-14 et 2026-11-18) : toutes les questions sont tranchées
1. Tranches de la part majoritaire : réglables, par défaut `[20, 40, 60, 80]` + 100 % (unanime), libellés en bornes numériques seules ; **bornes = limites inférieures incluses** (confirmé). La tranche « moins de 20 % » est toujours vide (part minimale 33,4 %) : confirmé, elle est masquée à l'affichage quand elle est structurellement vide.
2. Unité « membres-scrutins » complétée par le nombre de personnes distinctes (`personnes_exprimees`, `personnes_avec_vote`).
3. **Sélections précalculées de `stats.json`** : toutes les sélections, **et par catégorie et par année** (voir ALG-11).
4. `PO872880` et `PO847173` : deux groupes distincts (le référentiel les montre de même sigle `UDR`, sans lien explicite).

## Sources et constats
`.agents/DECISIONS.md` (2026-10-22 « Indicateurs sur les groupes »), `docs/methodology.md` (indicateurs, présence, sans vote enregistré), cahier technique §7 et §8, `docs/revue-maquette.md` (écarts n° 1 et 4), fiches ALG-02, 03, 05, mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction.
- v3 (2026-11-18) : sélections précalculées (toutes, par catégorie, par année) et bornes confirmées ; statut « Validé ».
- v2 (2026-11-14) : réécriture après les décisions du responsable : tranches réglables P1 à P`k+2` (remplacent B1 à B5), personnes distinctes, rappel de la part minimale 33,4 %, exemples recalculés, constat sur le renommage `UDR`.
- 2026-11-14 : décisions du responsable (voir « Décisions ») ; corps de la fiche à mettre à jour, statut inchangé.
- 2026-11-18 : code et tests écrits sans écart avec la fiche ; les constats de la fiche (9 547 groupes-scrutins sans vote exprimé, 2 035 égalités) sont reproduits exactement sur l'archive de 8 877 scrutins.
