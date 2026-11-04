# ALG-05 — Contrôles de réconciliation (totaux, groupes, nominatif)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Vérifier, scrutin par scrutin, que les chiffres de la source se recoupent entre eux (totaux, groupes, votes nominatifs, résultat), consigner chaque écart sans jamais le corriger ni le masquer, et distinguer les écarts **connus et validés** des écarts **nouveaux**, qui bloquent la publication (garantie 2).

## Périmètre
Inclus : liste des contrôles, deux niveaux d'exécution (avant écriture, sur la base), mécanisme des écarts connus, rapport.
Exclus : décision de publier ou de bloquer (ALG-12, qui consomme le rapport), vérification indépendante sur fichiers bruts tirés au hasard (garantie 3 : script distinct du pipeline, voir question 4), calcul de la position majoritaire (ALG-03).

## Constats (mesurés le 2026-11-03 sur les 8 877 fichiers, 106 524 groupes)
- Les identités de ALG-02, constat 11, tiennent sur la totalité, **sauf une** : la somme des `nonVotants` des groupes diffère du total dans le scrutin n° 1 (**21 dans les groupes, 10 au total**).
- Aucun groupe n'a pour + contre + abstentions + non-votants supérieur à `nombreMembresGroupe` (0 sur 106 524).
- `nonVotantsVolontaires` d'un groupe est égal à `abstentions` dans **les 106 524 groupes** (0 écart ; l'échantillon de 700 scrutins d'ALG-02 est donc confirmé sur la totalité). Le total du scrutin, lui, vaut toujours 0.
- Le résultat est cohérent avec le seuil : `sort.code = adopté` ⇔ `pour ≥ nbrSuffragesRequis`, sur 8 877 scrutins (0 écart). Et `nbrSuffragesRequis = ⌊suffrages exprimés / 2⌋ + 1` pour tous les scrutins hors motions de censure (0 écart sur 8 854). Une motion de censure est adoptée dans 1 cas sur 23.
- 9 547 groupes n'ont aucun vote exprimé ; 2 035 ont une égalité en tête (ALG-03) : ce sont des cas normaux, pas des écarts.

## Entrées / Sorties
- Entrées, selon le niveau :
  - niveau `lot` (avant écriture, dans l'import) : `LotScrutin` (ALG-04) et `ScrutinNormalise` (ALG-02), pour les contrôles qui ont besoin de champs non stockés ;
  - niveau `base` (commande `etl validate`) : la base SQLite, **relue uniquement par requêtes**, sans réutiliser d'objet en mémoire de l'import.
  - dans les deux cas : le fichier des écarts connus `ecarts_connus.json` (ci-dessous).
- Sortie : `RapportReconciliation` : `niveau`, `scrutins_controles`, `controles` (pour chaque identifiant : `nb_verifies`, `nb_ecarts`), `ecarts` (liste `{controle, scrutin_id, groupe_rang, attendu, obtenu, connu}`), `statut` ∈ {`ok`, `ecarts_connus`, `ecarts_nouveaux`}.

### Fichier des écarts connus
Fichier versionné dans le dépôt, une entrée par écart validé à la main : `{controle, scrutin_id, groupe_rang (ou null), attendu, obtenu, motif, valide_le, valide_par}`. Un écart relevé est « connu » **seulement si** contrôle, scrutin, rang, valeur attendue **et valeur obtenue** sont identiques à une entrée. Si la source change la valeur de l'écart, il redevient nouveau.

## Définitions
Pour un scrutin : `P, C, A, N` = totaux `pour`, `contre`, `abstentions`, `non_votants` ; `X` = `suffrages_exprimes` ; `V` = `nombre_votants` ; `R` = `nbr_suffrages_requis`.
Pour un groupe : `p, c, a, n` = ses compteurs ; `membres` ; `l_p, l_c, l_a, l_n` = nombre de lignes de vote nominatif de chaque position (comptées sur les lignes, pas lues dans un compteur).

## Contrôles
Sévérité : **B** = un écart nouveau bloque ; **I** = écart consigné et affiché, ne bloque pas.

| ID | Contrôle | Niveau | Sév. | Résultat attendu sur les données réelles |
|----|----------|--------|------|------------------------------------------|
| R01 | `numero` = entier du suffixe de `id` | lot, base | B | 0 écart |
| R02 | `P + C = X` | lot, base | B | 0 écart |
| R03 | `P + C + A = V` | lot, base | B | 0 écart |
| R04 | `Σ p = P` sur les groupes | lot, base | B | 0 écart |
| R05 | `Σ c = C` | lot, base | B | 0 écart |
| R06 | `Σ a = A` | lot, base | B | 0 écart |
| R07 | `Σ n = N` | lot, base | B | **1 écart connu** : scrutin n° 1 (21 ≠ 10) |
| R08 | Pour chaque position, nombre de lignes de vote du scrutin = total (`P`, `C`, `A`, `N`) | lot, base | B | 0 écart |
| R09 | Pour chaque groupe et position : `l_p = p`, `l_c = c`, `l_a = a`, `l_n = n` | lot, base | B | 0 écart (106 524 × 4 comparaisons) |
| R10 | Pour chaque groupe : `p + c + a + n ≤ membres` | lot, base | B | 0 écart |
| R11 | `adopté` ⇔ `P ≥ R` | lot, base | B | 0 écart |
| R12 | Hors motion de censure : `R = ⌊X / 2⌋ + 1` | lot, base | I | 0 écart |
| R13 | Total `non_votants_volontaires` du scrutin = 0 | lot | I | 0 écart |
| R14 | `abstentions_doublon_source` d'un groupe = `a` | lot | B | 0 écart (106 524 groupes) |
| R15 | Chaque `groupe_id` et `depute_id` des tables de votes existe dans `groupes` et `deputes` | base | B | 0 écart |
| R16 | Nombre de lignes de `scrutins` = nombre de scrutins acceptés par l'import le plus récent, plus les scrutins antérieurs absents de l'archive (ALG-07) | base | B | égalité |
| R17 | Aucun scrutin sans groupe, aucun scrutin sans ligne `scrutin_totals` | base | B | 0 écart |

Remarques :
- R12 est informatif : la règle de majorité est une règle de droit constitutionnel ou réglementaire que le projet n'a pas à faire respecter ; un écart signalerait seulement une donnée à regarder.
- R13 et R14 ne s'exécutent qu'au niveau `lot` car `non_votants_volontaires` et le doublon ne sont pas stockés (ALG-04).
- R16 ne se calcule qu'à la fin d'un import complet (ALG-07).

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Le module ne fait que lire et comparer.

```text
# Notations
connus   = charger(ecarts_connus.json)         # sinon erreur, arrêt                [1]
ecarts   = liste vide

pour chaque scrutin s du niveau demandé (lot ou base):                              [2]
    P, C, A, N = totaux officiels ; X = suffrages exprimés ; V = votants ; R = requis
    pour chaque contrôle R01 … R17 applicable (tous, sans s'arrêter au premier écart):
        attendu, obtenu = évaluer(contrôle, s)          # entiers, égalité exacte   [3]
        si attendu ≠ obtenu:                            # (R10 : p+c+a+n ≤ membres)
            e = {contrôle, scrutin_id, groupe_rang, attendu, obtenu}                [4]
            e.connu = (une entrée de connus a le même contrôle, scrutin, rang,
                       attendu ET obtenu)                                           [5]
            ecarts.ajouter(e)

# Exemples de contrôles
R02 : attendu = X       obtenu = P + C
R03 : attendu = V       obtenu = P + C + A
R04 : attendu = P       obtenu = Σ p des groupes
R09 : pour chaque groupe g et position q ∈ {pour, contre, abstention, non_votant}:
          attendu = compteur(g, q)   obtenu = nombre de lignes de vote(g, q)
R11 : attendu = (sort = adopté)   obtenu = (P ≥ R)

pour chaque entrée de connus jamais rencontrée:
    avertissement "ecart_connu_disparu"                                             [6]

# Statut global
si ∃ écart de sévérité B avec connu = faux:   statut = "ecarts_nouveaux"            [7]
sinon si ∃ écart (connu):                     statut = "ecarts_connus"
sinon:                                        statut = "ok"
journaliser le rapport complet ; ne rien modifier                                   [8]
```

Relations contrôlées (tout en entiers) : `P + C = X` ; `P + C + A = V` ; `Σ p = P`, `Σ c = C`, `Σ a = A`, `Σ n = N` ; `l_q = compteur_q` pour chaque groupe et position ; `p + c + a + n ≤ membres` ; `adopté ⇔ P ≥ R`. Un défaut unique (un `pour` modifié) fait apparaître plusieurs écarts distincts (R02, R04, R08), ce qui aide à le localiser. Une base vide n'est jamais `ok`.

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Charger `ecarts_connus.json` ; si une entrée est mal formée (champ manquant, contrôle inconnu) : erreur, arrêt | Un fichier d'exceptions illisible ne doit jamais devenir « aucune exception » ni « tout est permis » |
| 2 | Pour chaque scrutin du niveau demandé, évaluer les contrôles R01 à R17 applicables, **tous**, sans s'arrêter au premier écart | Un rapport complet en un seul passage (au plus 1 000 écarts détaillés par contrôle, le compte exact est toujours donné) |
| 3 | Tous les calculs sont faits en entiers ; comparer par égalité exacte (ou par inégalité large pour R10) | Aucun arrondi ni flottant, donc aucun écart fantôme |
| 4 | Un écart enregistre `attendu` et `obtenu` (pas seulement « différent ») | Permet d'identifier un écart connu et de le revoir sans relancer |
| 5 | Pour chaque écart, chercher une entrée identique dans les écarts connus ; positionner `connu = vrai` si trouvée | Seul l'écart exactement validé est toléré |
| 6 | Entrée du fichier des écarts connus jamais rencontrée : avertissement `ecart_connu_disparu` (ne bloque pas) | Un écart a pu être corrigé à la source : il faut alors retirer l'entrée plutôt que garder une exception morte |
| 7 | `statut` : `ecarts_nouveaux` si au moins un écart de sévérité B avec `connu = faux` ; sinon `ecarts_connus` s'il reste des écarts connus ; sinon `ok` | Garantie 2 : un écart nouveau interrompt le déploiement |
| 8 | Écrire le rapport en entier dans le journal ; ne jamais modifier la base ni les données | « Jamais corrigé en silence » (cahier §5.2, règle 7) |
| 9 | Niveau `base` : les requêtes SQL sont paramétrées et n'utilisent aucune donnée issue de l'import en cours (relecture indépendante) | Un défaut d'ALG-04 ou d'ALG-07 doit être détectable : le contrôle ne doit pas partager le code qui a produit les lignes |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Scrutin n° 1 : `Σ n = 21`, `N = 10` | écart R07 `connu = vrai`, statut global `ecarts_connus` | constat |
| Même scrutin, mais `N = 11` | écart R07 `connu = faux` : statut `ecarts_nouveaux` | la valeur obtenue a changé, la validation ne vaut plus |
| Nouveau scrutin avec `P + C ≠ X` | R02 bloquant | étape 7 |
| Groupe `PO0` | contrôlé comme les autres (les contrôles utilisent le rang, pas l'identifiant) | un groupe non identifié a des totaux exacts |
| `P + C + A + N > membres` pour un groupe | R10 bloquant | effectif incohérent |
| Entrée du fichier d'écarts jamais rencontrée | avertissement | étape 6 |
| Base vide | `scrutins_controles = 0`, statut `ecarts_nouveaux` avec R16 et R17 | une base vide n'est jamais « ok » |
| Plus de 1 000 écarts du même contrôle | les 1 000 premiers détaillés, le total exact conservé | rapport lisible, sans perte du compte |

## Exemples chiffrés (à reproduire en test)
- Archive réelle complète : `scrutins_controles = 8 877`, R07 : 1 écart connu (scrutin 1), tous les autres contrôles : 0 écart, statut `ecarts_connus`.
- Scrutin construit en test à partir d'un vrai fichier dont on modifie `pour` de 1 : R02, R04 et R08 en écart (trois contrôles distincts pour un même défaut) ; `connu = faux`.

## Invariants vérifiés
- `nb_ecarts ≤ nb_verifies` pour chaque contrôle ; la somme des écarts détaillés est inférieure ou égale au total.
- Le rapport ne dépend ni de l'ordre de lecture ni de l'horloge.
- Le module ne comporte aucune opération d'écriture sur la base.

## Questions à trancher avant de coder
1. **Écart du scrutin n° 1** (21 non-votants dans les groupes pour 10 au total) : on l'inscrit dans les écarts connus après examen du fichier. Je propose d'ouvrir le fichier avec toi avant de le valider ; je n'ai pas cherché d'explication.
2. **R12 informatif ou bloquant ?** Je le propose informatif (règle de droit, hors périmètre du projet).
3. **R14 bloquant ?** Le doublon `nonVotantsVolontaires` = `abstentions` est sans écart sur 106 524 groupes. Un changement de la source modifierait le sens d'un champ lu ; je le propose bloquant.
4. **Vérification indépendante** (garantie 3) : elle n'a pas de fiche. Je propose de créer **ALG-14** (script distinct relisant des fichiers bruts tirés au hasard et comparant chaque chiffre de `scrutins/<id>.json`). Veux-tu que je la rédige ?
5. **Plafond de 1 000 écarts détaillés** par contrôle : valeur arbitraire, à ajuster.

## Sources et constats
`docs/methodology.md` (garanties 2 et 3), `docs/algorithmes/ALG-02-normalisation.md` (constats 8 à 11), cahier technique §5.2 règle 7 et §5.3 (dernier test), mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction.
