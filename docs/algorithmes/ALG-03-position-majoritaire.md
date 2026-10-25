# ALG-03 — Position majoritaire d'un groupe sur un scrutin
Statut : Brouillon    Version : 1    Date : 2026-10-25

## But
Déterminer, pour un groupe et un scrutin, la position la plus fréquente parmi les positions exprimées, ou constater qu'il n'y en a pas, sans jamais utiliser le champ `positionMajoritaire` de la source.

## Entrées / Sorties
- Entrées (lues dans `ventilationVotes.organe.groupes.groupe[i].vote.decompteVoix`, après ALG-02) : `pour`, `contre`, `abstentions` (entiers ≥ 0) ; `nonVotants` et `nonVotantsVolontaires` (entiers ≥ 0, non utilisés dans le calcul) ; `nombreMembresGroupe` (entier > 0).
- Sorties : `position_majoritaire` ∈ {`pour`, `contre`, `abstention`, `aucune`} ; `raison_absence` ∈ {`aucun_vote_exprime`, `egalite`, `null`} ; `exprimes` (E) ; `effectif_majoritaire` (m) ; `majorite_absolue` (booléen) ; `participation_num` = E, `participation_den` = `nombreMembresGroupe`.

## Définitions et formules
- P, C, A = `pour`, `contre`, `abstentions`.
- E = P + C + A : positions exprimées. Les non-votants sont exclus parce qu'une absence n'est pas une position (règle de neutralité).
- m = max(P, C, A).
- majorité absolue ⇔ 2·m > E. Calcul en entiers pour éviter tout arrondi flottant.

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Lire P, C, A depuis `decompteVoix` (jamais depuis `positionMajoritaire`) | `decompteVoix` est cohérent avec les listes nominatives (600/600 scrutins) ; `positionMajoritaire` contredit les décomptes dans 226 cas sur ~7 100 |
| 2 | Si P, C ou A est absent, négatif ou non entier : lever une erreur de donnée (ALG-05), ne pas calculer | Mieux vaut ne rien afficher qu'un chiffre faux |
| 3 | E ← P + C + A | Définition de l'ensemble des positions exprimées |
| 4 | Si E = 0 : retourner `aucune` avec `raison_absence = aucun_vote_exprime`, m = 0 | Sans vote exprimé, parler de « majorité » serait inventer une position (la source met « pour » dans ce cas) |
| 5 | m ← max(P, C, A) | Effectif de la position la plus fréquente |
| 6 | N ← nombre de positions dont l'effectif vaut m | Détecter l'égalité |
| 7 | Si N > 1 : retourner `aucune` avec `raison_absence = egalite` | Désigner une position parmi des positions à égalité serait arbitraire |
| 8 | Sinon retourner la seule position dont l'effectif vaut m | Majorité relative stricte |
| 9 | `majorite_absolue` ← (2·m > E) | Permet d'écrire « majorité relative » quand elle ne dépasse pas la moitié des exprimés |
| 10 | Conserver `positionMajoritaire` de la source dans `position_majoritaire_source`, sans la modifier ni l'afficher | Audit et traçabilité de l'écart avec la source |

## Cas limites et erreurs
| Cas | Résultat | Pourquoi |
|-----|----------|----------|
| P=12, C=2, A=0 | pour, m=12, E=14, absolue | cas nominal |
| P=5, C=6, A=49 | abstention, m=49, E=60, absolue | l'abstention peut être majoritaire |
| P=6, C=6, A=1 | aucune, `egalite` | égalité en tête |
| P=0, C=0, A=0 | aucune, `aucun_vote_exprime` | pas de position exprimée |
| P=3, C=2, A=2 | pour, m=3, E=7, non absolue | majorité relative |
| P=4, C=4, A=4 | aucune, `egalite` | égalité à trois |
| P=1, C=0, A=0 | pour, m=1, E=1, absolue | un seul votant (cf. cahier §5.3) |
| valeur négative ou absente | erreur de donnée | ALG-05 |

## Exemples chiffrés
Ceux du tableau ci-dessus, plus (vérifié sur les fichiers réels) `VTANR5L17V2066`, groupe `PO845407` : P=12, C=2, A=0 → pour, 12 sur 14 ; la source indique « contre ».

## Invariants vérifiés
- E ≤ nombreMembresGroupe ; sinon alerte de réconciliation (ALG-05).
- m ≤ E ; m = 0 ⇔ E = 0.
- `position_majoritaire = aucune` ⇔ (E = 0 ou égalité).

## Sources et constats
`docs/analyse-donnees-sources.md` (écart de la source), `docs/methodology.md` (« Position majoritaire d'un groupe »), `.agents/DECISIONS.md` (« Position majoritaire d'un groupe : calcul ETL »).

## Historique
- v1 (2026-10-25) : première rédaction.
