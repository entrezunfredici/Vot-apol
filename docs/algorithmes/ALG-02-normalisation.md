# ALG-02 — Normalisation d'un scrutin (valeurs, collections, positions)
Statut : Brouillon    Version : 1    Date : 2026-10-25

## But
Transformer le document JSON brut d'un scrutin (sortie d'ALG-01) en une structure typée et sans ambiguïté : nombres en entiers, booléens, dates ISO, collections toujours en listes, positions dans un vocabulaire fermé, références validées. Toute valeur inattendue est signalée, jamais devinée.

## Périmètre
Inclus : conversion et validation champ par champ, aplatissement des collections, vocabulaire des positions, repérage des références non résolues, champs ignorés ou inconnus.
Exclus : contrôles de cohérence entre totaux (ALG-05), calcul de la position majoritaire (ALG-03), rattachement d'une mise au point à un groupe (ALG-06), écriture en base (ALG-07).

## Constats (balayage des 8 877 fichiers, champ par champ)
Source : `scan_types` et `scan_identities` exécutés le 2026-10-25 sur la totalité du dossier. Les points marqués ⚠ corrigent ou complètent l'analyse faite sur l'échantillon de 600 fichiers.

1. **Formats des nombres.** Tous les compteurs (`decompte`, `decompteVoix`, `nombreMembresGroupe`, `numero`, `legislature`, `quantiemeJourSeance`, `nombreVotants`, `suffragesExprimes`, `nbrSuffragesRequis`) sont des chaînes d'entiers canoniques (`0` ou sans zéro initial), jamais vides, jamais décimaux. `numPlace` fait exception : chaînes avec zéros initiaux (`"066"`) et quelques `null`.
2. **Booléens.** `parDelegation` ne vaut que `"true"` ou `"false"` (en minuscules, en chaîne).
3. **Dates.** `dateScrutin` est au format `AAAA-MM-JJ`, toujours valide, de `2024-10-08` à `2026-10-16`.
4. **Collections.** Dans `decompteNominatif`, `pours`/`contres`/`abstentions`/`nonVotants` valent `null` ou `{"votant": objet | liste}`. ⚠ Dans `miseAuPoint`, `abstentions`, `nonVotants`, `nonVotantsVolontaires` sont des **listes** dont les éléments valent `null` ou `{"votant": objet | liste}` (le plus souvent `[null, null]`), alors que `pours` et `contres` sont `null` ou `{"votant": …}`. Dans `miseAuPoint.dysfonctionnement`, les clés sont au singulier (`pour`, `contre`) et valent `null` ou `{"votant": …}`.
5. **Types de scrutin.** ⚠ `codeTypeVote` vaut `SPO` (8 780), `SPS` scrutin public solennel (74) ou `MOC` motion de censure (23). L'échantillon de 600 ne contenait que des `SPO`.
6. **Résultat.** `sort.code` vaut `adopté` (3 031) ou `rejeté` (5 846). `sort.libelle` et `syntheseVote.annonce` ont la même valeur, avec une casse différente (« l'Assemblée nationale a adopté » / « L'Assemblée nationale n'a pas adopté »).
7. **Non-votants.** `causePositionVote` vaut `MG` (membre du gouvernement), `PSE` (président de séance) ou `PAN` (président de l'Assemblée nationale), et est présent sur **tous** les non-votants nominatifs, sur aucun autre votant. `nonVotantsVolontaires` du total vaut toujours `0`.
8. ⚠ **Les absents ne figurent pas dans les données.** Sur un échantillon aléatoire de 700 scrutins (8 400 groupes), la somme pour + contre + abstentions + non-votants est toujours inférieure ou égale à `nombreMembresGroupe` et, dans la quasi-totalité des cas, strictement inférieure (exemple : scrutin 1, `PO845401`, aucune position pour 125 membres). Les députés sans vote enregistré n'apparaissent dans aucune liste. Les « non-votants » de la source sont donc uniquement les personnes dont la fonction empêche de voter. L'écart `membres − (pour + contre + abstentions + non-votants)` est un **nombre de députés sans vote enregistré**, à ne jamais appeler « absents » ni « abstentions ». La vérification sur les 106 524 groupes revient à ALG-05.
9. ⚠ **Références de groupe non résolues.** 14 scrutins ont un `organeRef` de groupe valant `PO0` : les 12 groupes pour les scrutins 489 à 501 (sur 13 numéros, dont 12 concernés), et un seul groupe pour les scrutins 1302 et 6256. Plusieurs groupes d'un même scrutin portent alors la même référence : elle ne peut pas servir de clé. Chaque scrutin a 12 groupes, mais 14 références de groupe distinctes apparaissent au total sur la législature (changements de groupes).
10. ⚠ **`nonVotantsVolontaires` d'un groupe est un doublon de `abstentions`.** Dans `decompteVoix`, le champ est égal à `abstentions` pour tous les groupes de l'échantillon de 700 scrutins (8 400 groupes, zéros compris) et il est non nul dans 14 625 groupes sur 106 524, soit exactement le nombre de groupes dont la liste nominative des abstentions n'est pas vide. Le total du scrutin, lui, vaut toujours `0` : 6 531 scrutins ont une somme par groupe différente du total pour ce champ. Additionner `nonVotantsVolontaires` aux autres positions compterait donc deux fois les abstentions. Le champ est lu et validé comme entier, comparé à `abstentions` (contrôle d'ALG-05) et **non stocké**.
11. **Identités vérifiées sur les 8 877 scrutins** : `numero` = numéro du fichier ; pour + contre = suffrages exprimés ; pour + contre + abstentions = votants ; nombre de votants nominatifs = `decompteVoix` pour chaque position et chaque groupe ; aucun député listé deux fois dans un même scrutin ; somme des groupes = total du scrutin pour pour, contre, abstentions (et non-votants sauf un scrutin, à examiner en ALG-05).
12. **Valeurs nulles.** `demandeur.texte` est `null` dans 30 scrutins ; `objet.dossierLegislatif` est `null` dans 5 826 scrutins sur 8 877 ; `demandeur.referenceLegislative` et `objet.referenceLegislative` sont toujours `null`.

## Entrées / Sorties
- Entrée : `document` (objet JSON `{"scrutin": {...}}`, déjà validé par ALG-01).
- Sortie : `ScrutinNormalise` ou une liste d'erreurs (scrutin refusé) ; dans les deux cas une liste d'avertissements.

`ScrutinNormalise` :

| Bloc | Champs |
|------|--------|
| Identité | `id` (`uid`), `numero` (entier), `legislature` (entier), `date_scrutin` (texte `AAAA-MM-JJ`), `session_ref`, `seance_ref`, `organe_ref`, `quantieme_jour_seance` (entier), `lieu_vote` |
| Nature | `type_vote_code`, `type_vote_libelle`, `type_majorite`, `titre`, `objet_libelle`, `dossier_ref` et `dossier_libelle` (ou `null`), `demandeur_texte` (ou `null`), `mode_publication` |
| Résultat | `sort_code` (`adopte` \| `rejete`), `sort_libelle` |
| Totaux | `nombre_votants`, `suffrages_exprimes`, `nbr_suffrages_requis`, `pour`, `contre`, `abstentions`, `non_votants`, `non_votants_volontaires` (tous entiers ; ce dernier vaut `0` dans les 8 877 scrutins) |
| Groupes (liste, ordre du fichier) | `rang` (1 à n), `organe_ref` (ou `null` si non résolue), `membres`, `pour`, `contre`, `abstentions`, `non_votants`, `position_majoritaire_source`, `votants` ; plus `abstentions_doublon_source` (copie de `nonVotantsVolontaires`, réservée au contrôle d'ALG-05) |
| Votant | `acteur_ref`, `mandat_ref`, `position` (`pour` \| `contre` \| `abstention` \| `non_votant`), `par_delegation` (booléen), `cause` (`MG` \| `PSE` \| `PAN` ou `null`) |
| Mises au point | liste de `{acteur_ref, mandat_ref, position_declaree, par_delegation}` avec `position_declaree` ∈ `pour`, `contre`, `abstention`, `non_votant`, `non_votant_volontaire` |
| Dysfonctionnements | même forme que les mises au point, `origine = dysfonctionnement` |

Champs volontairement **ignorés** (documentés, non stockés) : `@xmlns`, `@xmlns:xsi` (métadonnées XML, seulement comparées à leurs valeurs attendues), `numPlace` (numéro de place dans l'hémicycle, sans usage), `syntheseVote.annonce` (doublon de `sort.libelle`), `demandeur.referenceLegislative` et `objet.referenceLegislative` (toujours `null`), `sessionRef`/`seanceRef` sont conservés pour la provenance.

## Fonctions de base
| # | Fonction | Règle | Justification |
|---|----------|-------|---------------|
| N1 | `entier(v)` | `v` est une chaîne qui correspond exactement à `^(0\|[1-9][0-9]*)$`, ou un entier JSON ≥ 0 (hors booléen) → l'entier ; toute autre valeur (`null`, vide, signe, décimal, espace, zéro initial) → erreur de format | Tous les compteurs observés sont canoniques ; accepter autre chose masquerait une dérive de la source |
| N2 | `entier_optionnel(v)` | `null` → `null`, sinon N1 | Distingue « absent » de « zéro » |
| N3 | `booleen(v)` | `"true"` → vrai, `"false"` → faux, sinon erreur | Seules ces deux valeurs existent ; `"True"` ou `1` seraient une anomalie |
| N4 | `date_iso(v)` | chaîne `^\d{4}-\d{2}-\d{2}$` qui est une date du calendrier valide → la chaîne inchangée, sinon erreur | La date est stockée telle quelle (pas de fuseau, pas d'heure) ; les 8 877 dates observées sont valides |
| N5 | `texte(v, requis)` | chaîne → normalisation Unicode NFC ; espaces de début et de fin retirés avec avertissement ; chaîne vide → `null` ; `null` → `null` ; si `requis` et résultat `null` → erreur ; non-chaîne → erreur | NFC rend les comparaisons fiables ; on ne modifie jamais le texte intérieur (un titre officiel n'est pas réécrit) |
| N6 | `reference(v, préfixe)` | doit correspondre à `^<préfixe>[1-9][0-9]*$` (préfixes `PA`, `PM`, `PO`) ; la valeur `PO0` donne l'état « non résolue » (pas une erreur de format) ; toute autre valeur → erreur | `PO0` existe dans 14 scrutins et ne désigne aucun organe : elle ne doit jamais devenir une clé |
| N7 | `enum_ferme(v, table)` | `v` doit être une clé de `table` → sa valeur normalisée ; sinon erreur `valeur_inconnue` | Une valeur nouvelle (nouveau type de vote, nouvelle cause) doit bloquer la publication jusqu'à ce que la spécification soit étendue |
| N8 | `objet(d, requises, optionnelles)` | `d` doit être un dictionnaire ; toute clé requise absente → erreur ; toute clé hors des listes → avertissement `champ_inconnu` (chemin et nom), conservée dans le fichier source (ALG-01) | Une dérive du schéma doit être visible sans bloquer ce qui est connu |
| N9 | `aplatir_votants(nœud)` | `null` → liste vide ; liste → concaténation de `aplatir_votants` de chaque élément ; dictionnaire → doit être exactement de la forme `{"votant": x}` (sinon erreur), avec `x` dictionnaire → 1 élément, `x` liste → ses éléments (chacun un dictionnaire, sinon erreur) | Une seule fonction couvre les deux formes observées (nominatif : `null` ou `{votant}` ; mises au point : listes de `null` ou `{votant}`) |

Tables de vocabulaire (fermées) :

| Contexte | Clé source → position normalisée |
|----------|----------------------------------|
| `decompteNominatif` d'un groupe | `pours` → `pour`, `contres` → `contre`, `abstentions` → `abstention`, `nonVotants` → `non_votant` |
| `miseAuPoint` | `pours` → `pour`, `contres` → `contre`, `abstentions` → `abstention`, `nonVotants` → `non_votant`, `nonVotantsVolontaires` → `non_votant_volontaire` |
| `miseAuPoint.dysfonctionnement` | `pour` → `pour`, `contre` → `contre`, `abstentions` → `abstention`, `nonVotants` → `non_votant`, `nonVotantsVolontaires` → `non_votant_volontaire` |
| `sort.code` | `adopté` → `adopte`, `rejeté` → `rejete` |
| `typeVote.codeTypeVote` | `SPO`, `SPS`, `MOC` (conservés tels quels) |
| `causePositionVote` | `MG`, `PSE`, `PAN` (conservés tels quels) |
| `positionMajoritaire` (audit uniquement) | `pour`, `contre`, `abstention` ; autre valeur → conservée telle quelle avec avertissement (le champ n'est jamais affiché) |

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie à l'étape du tableau « assemblage », `N1`…`N9` aux fonctions de base. Le tableau fait foi.

```text
# Notations
doc        = Entrée[document]                # {"scrutin": {...}} issu d'ALG-01
s          = doc["scrutin"]
erreurs    = liste vide ; avertissements = liste vide

# 1. Identité et nature
id, numero, legislature  = N5(s.uid), N1(s.numero), N1(s.legislature)
date_scrutin             = N4(s.dateScrutin)
organe_ref               = N6(s.organeRef, "PO")
type_vote_code           = N7(s.typeVote.codeTypeVote, {SPO, SPS, MOC})
sort_code                = N7(s.sort.code, {"adopté": "adopte", "rejeté": "rejete"})
si s.modePublicationDesVotes ≠ "DecompteNominatif":
    erreur "mode_publication_non_gere"                                      [9]

# 2. Totaux officiels (aucun calcul)
pour, contre, abstentions, non_votants = N1(s.syntheseVote.decompte.*)      [10]

# 3. Groupes
groupes = mettre_en_liste(s.ventilationVotes.organe.groupes.groupe)         [11]
si groupes est vide: erreur "aucun_groupe"
pour chaque groupe g, de rang r = 1, 2, … (ordre du fichier):
    ref = N6(g.organeRef, "PO")
    si ref = "PO0": g.organe_ref = null ; avertissement "groupe_non_identifie"  [13]
    membres = N1(g.nombreMembresGroupe)
    compteurs = N1(g.vote.decompteVoix.{pour, contre, abstentions, nonVotants})
    # nonVotantsVolontaires est lu et validé, jamais stocké (doublon d'abstentions)

    # 4. Votes nominatifs du groupe
    pour chaque (clé_source, position) de la table « decompteNominatif »:
        pour chaque votant v dans N9(g.vote.decompteNominatif[clé_source]):
            acteur_ref = N6(v.acteurRef, "PA") ; mandat_ref = N6(v.mandatRef, "PM")
            par_delegation = N3(v.parDelegation)
            si position = "non_votant":
                cause = N7(v.causePositionVote, {MG, PSE, PAN})             [18]
            sinon si v.causePositionVote existe: erreur "cause_incoherente"
    trier les votants par (position, acteur_ref)                            [19]

si un acteur_ref apparaît deux fois dans le scrutin: erreur "depute_en_double"   [20]

# 5. Mises au point et dysfonctionnements
pour chaque clé de miseAuPoint (pours, contres, abstentions, nonVotants, nonVotantsVolontaires):
    lignes += N9(...) avec la position de la table « miseAuPoint »          [21]
pour chaque clé de miseAuPoint.dysfonctionnement:
    lignes += N9(...) avec origine = "dysfonctionnement"                    [22]

# 6. Bilan
si erreurs non vide: retourner (erreurs, avertissements)   # jamais de scrutin à moitié normalisé   [23]
sinon:               retourner (ScrutinNormalise, avertissements)           [24]
```

Relations à retenir :
- Après normalisation, `|votants listés du groupe pour une position| = compteur de decompteVoix` : ALG-02 produit les deux grandeurs, ALG-05 les compare.
- `sans_vote_enregistre(groupe) = membres − (pour + contre + abstentions + non_votants) ≥ 0` : jamais appelé « absents ».
- Deux normalisations du même document donnent la même sortie (ordre fixé).

## Algorithme (assemblage d'un scrutin)
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Vérifier que `document` est un dictionnaire dont la seule clé est `scrutin` (dictionnaire) ; sinon erreur | ALG-01 le garantit déjà ; vérifié à nouveau pour que ALG-02 soit utilisable seul et testable seul |
| 2 | Appliquer N8 à `scrutin` : requises = `uid`, `numero`, `organeRef`, `legislature`, `sessionRef`, `seanceRef`, `dateScrutin`, `quantiemeJourSeance`, `typeVote`, `sort`, `titre`, `demandeur`, `objet`, `modePublicationDesVotes`, `syntheseVote`, `ventilationVotes`, `miseAuPoint`, `lieuVote` ; optionnelles = `@xmlns`, `@xmlns:xsi` | Ces dix-huit clés sont présentes dans 100 % des fichiers ; une absence signale un fichier dégradé |
| 3 | Comparer `@xmlns` et `@xmlns:xsi` à leurs valeurs observées ; différence → avertissement `schema_modifie` | Un changement d'espace de noms annonce une évolution du format |
| 4 | `id` ← N5(`uid`, requis) ; `numero`, `legislature`, `quantieme_jour_seance` ← N1 ; `date_scrutin` ← N4 ; `session_ref`, `seance_ref`, `lieu_vote` ← N5 requis ; `organe_ref` ← N6(`PO`) | Identité et provenance de la séance |
| 5 | `typeVote` : N8 (`codeTypeVote`, `libelleTypeVote`, `typeMajorite` requis) ; code ← N7 ; libellé et majorité ← N5 requis | Le type de vote conditionne l'affichage (motion de censure) ; une valeur inconnue bloque |
| 6 | `sort` : N8 (`code`, `libelle`) ; `sort_code` ← N7 ; `sort_libelle` ← N5 requis | Le résultat est une donnée centrale : valeur fermée |
| 7 | `titre` ← N5 requis ; `objet` : N8 (`libelle` requis ; `dossierLegislatif`, `referenceLegislative` optionnelles) ; `objet_libelle` ← N5 requis ; `dossierLegislatif` `null` → `dossier_ref` et `dossier_libelle` nuls, sinon N8 (`dossierRef`, `libelle`) puis N5 requis | 5 826 scrutins n'ont pas de dossier législatif : cas normal, non signalé |
| 8 | `demandeur` : N8 (`texte`, `referenceLegislative` optionnelles) ; `demandeur_texte` ← N5 non requis | `texte` est `null` dans 30 scrutins : cas normal |
| 9 | `modePublicationDesVotes` ← N5 requis ; si différent de `DecompteNominatif` : erreur `mode_publication_non_gere` | Les autres modes n'ont jamais été observés et n'ont pas de liste nominative |
| 10 | `syntheseVote` : N8 (`nombreVotants`, `suffragesExprimes`, `nbrSuffragesRequis`, `decompte` requis ; `annonce` optionnelle) ; `decompte` : N8 (`pour`, `contre`, `abstentions`, `nonVotants`, `nonVotantsVolontaires`) ; tous ← N1 | Totaux officiels, sans arrondi ni calcul |
| 11 | `ventilationVotes.organe.groupes.groupe` : suivre le chemin avec N8 à chaque niveau ; le nœud `groupe` est mis en liste (`null` → erreur ; dictionnaire → 1 élément ; liste → ses éléments) ; liste vide → erreur `aucun_groupe` | Cas à un seul groupe prévu par le cahier §5.3 ; un scrutin sans groupe n'est pas exploitable |
| 12 | Pour chaque groupe, `rang` ← sa position (1, 2, …) dans le fichier ; N8 (`organeRef`, `nombreMembresGroupe`, `vote`) ; `membres` ← N1 | `rang` permet d'identifier un groupe de référence non résolue sans l'inventer |
| 13 | `organeRef` du groupe ← N6(`PO`) ; si « non résolue » : `organe_ref = null`, avertissement `groupe_non_identifie` (numéro de scrutin, rang) | On ne devine jamais un groupe à partir de sa taille ou de son rang |
| 14 | `vote` : N8 (`positionMajoritaire`, `decompteVoix`, `decompteNominatif` requis) ; `positionMajoritaire` ← N5 en minuscules, hors liste → conservée avec avertissement | Valeur d'audit uniquement (ALG-03) |
| 15 | `decompteVoix` : N8 (cinq clés) ; tous ← N1 | Source des effectifs par groupe |
| 16 | `decompteNominatif` : N8 (`pours`, `contres`, `abstentions`, `nonVotants` requises, valeur `null` admise) | Les quatre clés sont présentes dans 100 % des groupes |
| 17 | Pour chaque clé de la table « decompteNominatif », `aplatir_votants` (N9) puis, pour chaque votant, N8 (`acteurRef`, `mandatRef`, `parDelegation` requis ; `numPlace`, `causePositionVote` optionnels) ; `acteur_ref` ← N6(`PA`) ; `mandat_ref` ← N6(`PM`) ; `par_delegation` ← N3 ; `position` ← table | Une ligne par vote individuel |
| 18 | `causePositionVote` : si la position est `non_votant`, la valeur est N7(`MG`, `PSE`, `PAN`) ; si absente, avertissement `non_votant_sans_cause` ; si présente avec une autre position : erreur `cause_incoherente` | Observé : cause présente sur tous les non-votants, sur aucun autre votant |
| 19 | Trier les votants du groupe par (ordre `pour`, `contre`, `abstention`, `non_votant`), puis `acteur_ref` croissant | Sortie déterministe (garantie nécessaire à ALG-11) |
| 20 | Vérifier qu'aucun `acteur_ref` n'apparaît deux fois dans l'ensemble du scrutin ; sinon erreur `depute_en_double` | Un député a un seul vote par scrutin ; la clé (scrutin, député) en dépend ; 0 cas observé |
| 21 | `miseAuPoint` : N8 avec les clés `pours`, `contres`, `abstentions`, `nonVotants`, `nonVotantsVolontaires`, `dysfonctionnement` ; pour chacune des cinq premières, N9 puis N8 sur chaque votant (mêmes règles que l'étape 17 sans cause) et position selon la table « miseAuPoint » | Les mises au point sont conservées intégralement pour ALG-06 |
| 22 | `miseAuPoint.dysfonctionnement` : N8 avec les cinq clés au singulier ; même traitement avec la table « dysfonctionnement » ; `origine = dysfonctionnement` | Information distincte d'une mise au point, à ne pas fusionner |
| 23 | Collecter les avertissements et les erreurs (au plus 50 erreurs par scrutin, toutes rapportées avec leur chemin) ; s'il y a au moins une erreur : retourner les erreurs, pas de `ScrutinNormalise` | Un scrutin à moitié normalisé ne doit jamais atteindre la base ; le rapport doit être exploitable d'un seul coup |
| 24 | Sinon retourner le `ScrutinNormalise` et les avertissements | Les avertissements ne bloquent pas, mais sont journalisés et comptés dans le rapport d'import |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| `pours: null` | liste de votants vide | N9 |
| `contres: {"votant": {…}}` (un seul votant, objet) | liste d'un élément | N9, cas imposé par le cahier §5.3 |
| `abstentions: {"votant": [ … ]}` | la liste | N9 |
| `miseAuPoint.abstentions: [null, null]` | liste vide | N9 |
| `miseAuPoint.abstentions: [null, {"votant": [a, b]}]` | 2 éléments | N9 |
| `groupe` en dictionnaire unique | liste d'un groupe | étape 11 |
| `"pour": "012"` ou `"pour": ""` ou `"pour": "1.0"` | erreur de format | N1 |
| `"pour": 12` (entier JSON) | accepté, vaut 12 | N1 |
| `"pour": true` | erreur | N1 exclut le booléen |
| `parDelegation: "True"` | erreur | N3 |
| `dateScrutin: "2026-02-30"` | erreur | N4 |
| `organeRef: "PO0"` sur un groupe | `organe_ref = null`, avertissement, scrutin accepté | étape 13 |
| `organeRef: "po845401"` ou `""` | erreur | N6 |
| `codeTypeVote: "XYZ"` | erreur `valeur_inconnue` | N7 |
| `sort.code` autre que `adopté`/`rejeté` | erreur | N7 |
| `causePositionVote: "ABC"` | erreur | N7 |
| non-votant sans cause | avertissement | étape 18 |
| `causePositionVote` sur un votant « pour » | erreur | étape 18 |
| même `acteurRef` dans deux groupes | erreur `depute_en_double` | étape 20 |
| clé nouvelle `foo` dans `scrutin` | avertissement `champ_inconnu`, scrutin accepté | N8 |
| clé requise absente (`titre`) | erreur | N8 |
| `numPlace: "066"` ou `null` ou absent | ignoré, sans avertissement | champ ignoré |
| `positionMajoritaire: "Pour"` | `pour` | étape 14 |
| `positionMajoritaire: "inconnue"` | conservée, avertissement | étape 14 |
| `modePublicationDesVotes` autre | erreur | étape 9 |

## Exemples chiffrés (à reproduire en test)
Sur les fichiers réels :
- `VTANR5L17V1017` : groupe `PO845407` : `pours` en liste (≥ 2 votants dont un par délégation), `contres` à `null` → liste vide, `nonVotants` en objet unique avec `causePositionVote` = `PAN` → 1 votant de position `non_votant`, cause `PAN`.
- `VTANR5L17V489` : les 12 groupes ont `organeRef = PO0` → 12 groupes avec `organe_ref = null`, rangs 1 à 12, 12 avertissements `groupe_non_identifie`, scrutin accepté.
- `VTANR5L17V1302` : un seul groupe non identifié (rang 1).

Sur l'ensemble des 8 877 fichiers (valeurs issues du balayage, à confirmer par le test d'intégration) :

| Mesure | Valeur attendue |
|--------|-----------------|
| Scrutins normalisés sans erreur | 8 877 |
| Groupes | 106 524 (12 par scrutin), dont 146 sans référence résolue |
| Votes nominatifs | 1 323 978 (pour 580 652 ; contre 643 533 ; abstention 75 754 ; non-votant 24 039) |
| Lignes de mises au point | 3 243 (pour 1 283 ; contre 1 224 ; abstention 281 ; non-votant 450 ; non-votant volontaire 5) |
| Lignes de dysfonctionnement | 163 (pour 82 ; contre 57 ; abstention 9 ; non-votant volontaire 15) |
| Types de vote | SPO 8 780 ; SPS 74 ; MOC 23 |
| Résultats | adopté 3 031 ; rejeté 5 846 |

## Invariants vérifiés
- Après normalisation : tous les compteurs sont des entiers ≥ 0 ; toutes les collections sont des listes ; aucun `acteur_ref` en double dans un scrutin.
- Pour chaque groupe et chaque position, nombre de votants listés = compteur de `decompteVoix` (le contrôle lui-même est dans ALG-05 ; ALG-02 fournit les deux grandeurs).
- Deux normalisations du même document produisent exactement la même sortie (ordre des votants et des clés fixé).
- Aucun champ n'est supprimé en silence : tout champ du fichier source est soit stocké, soit dans la liste des champs ignorés ci-dessus, soit signalé `champ_inconnu`.

## Questions à trancher avant de coder
1. **Groupes non identifiés (`PO0`).** Proposition : le scrutin est importé et ses totaux sont affichés, mais la ventilation par groupe est présentée comme « indisponible : référence du groupe absente dans la source » et les groupes concernés sont exclus de tous les indicateurs et comparaisons. Alternatives écartées : deviner le groupe d'après la taille ou l'ordre (inférence), ou exclure le scrutin entier. Les votes individuels de ces groupes restent enregistrés sans groupe. D'accord ?
2. **Absents.** Les députés sans vote enregistré ne sont pas dans la source. Proposition : afficher « sans vote enregistré » (= effectif − votes enregistrés), distinct de « non-votants » (fonction empêchant de voter) et de « abstention », et mettre à jour la méthodologie et la maquette. D'accord ?
3. **Valeur inconnue d'un champ fermé** (nouveau type de vote, nouvelle cause, nouveau résultat) : le scrutin est refusé et la publication bloquée jusqu'à extension de la fiche. Confirmes-tu cette rigueur ?
4. **`numPlace` ignoré.** Confirmes-tu qu'on ne le stocke pas ?
5. **Texte** : trim + NFC seulement, sans toucher aux mots. Les chaînes `titre` et `objet` sont conservées telles que publiées.

## Sources et constats
`docs/analyse-donnees-sources.md`, cahier technique §2, §4 (colonnes), §5.2 (règles 3 et 4) et §5.3 (cas imposés), `docs/methodology.md`, `.agents/DECISIONS.md`.

## Historique
- v1 (2026-10-25) : première rédaction, à partir du balayage des 8 877 fichiers.
