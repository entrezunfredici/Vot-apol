# ALG-09 — Résolution des noms (référentiels des groupes et des députés)
Statut : Brouillon    Version : 1    Date : 2026-11-03

> **Réserve : les référentiels officiels n'ont pas encore été inspectés.** Aucun fichier de référentiel n'est dans le dépôt. Cette fiche fixe les règles (appariement par identifiant exact, jamais par ressemblance) et le déroulement, mais **les noms de champs, la structure des fichiers et les chiffres attendus restent à établir** par une inspection comparable à celle des scrutins. Elle ne peut pas être validée avant cela (voir « Constats à établir »).

## But
Associer un libellé et un sigle à chaque groupe, un nom et un prénom à chaque député, uniquement par correspondance exacte d'identifiant (`PO…`, `PA…`) avec les référentiels officiels, et signaler ce qui n'est pas résolu au lieu de l'inventer.

## Périmètre
Inclus : lecture des référentiels, validation, appariement par identifiant, mise à jour de `groupes` et `deputes`, rapport des identifiants non résolus.
Exclus : lecture sécurisée de l'archive (réutilise ALG-01, voir question 2), téléchargement des référentiels (ALG-13), affichage (front : « libellé non résolu »), historique d'appartenance d'un député à un groupe (il vient des votes, jamais du référentiel).

## Constats sur les scrutins (mesurés le 2026-11-03)
- **652 députés distincts** apparaissent dans les votes nominatifs ; tous ceux des mises au point y figurent aussi (aucun identifiant supplémentaire à résoudre).
- **13 groupes réels** (références `PO…`) et la référence non résolue `PO0` (146 occurrences). Onze références sont présentes dans presque tous les scrutins ; deux autres se partagent à elles deux les 8 865 scrutins hors `PO0` : `PO872880` (5 824 scrutins) et `PO847173` (3 041 scrutins). La source ne dit pas s'il s'agit d'un même groupe renommé ; **on ne les fusionne pas**.
- **25 députés ont voté sous plus d'un groupe** (hors `PO0`) : le groupe d'un député est celui enregistré dans le scrutin, jamais un attribut de la personne.
- 681 mandats distincts (`PM…`) ; aucun référentiel de mandats n'est nécessaire, `mandat_id` est conservé tel quel.

## Constats à établir avant validation (inspection des référentiels)
1. Quels fichiers publient les organes et les acteurs, sous quelle forme (archive, taille, encodage, structure) ?
2. Quel champ distingue un groupe parlementaire des autres organes (commissions, délégations…) ?
3. Quels champs donnent le libellé, le sigle (ou « libellé abrégé »), le nom et le prénom ? Peuvent-ils être vides, multiples ou variables dans le temps ?
4. Les 13 identifiants de groupe et les 652 identifiants de députés y figurent-ils tous ?
5. Les libellés de groupe changent-ils au cours de la législature (renommage) ? Un identifiant peut-il changer de libellé ?
6. Des identifiants dupliqués, des homonymes, des caractères particuliers (traits d'union, particules, majuscules) ?
7. Les 146 occurrences de `PO0` correspondent-elles à un organe réel, supprimé depuis ?

## Entrées / Sorties
- Entrées : archive(s) de référentiel (organes, acteurs), base de travail avec les identifiants `groupes_vus` et `deputes_vus` déjà importés (ALG-07), identifiants référencés lus dans `scrutin_group_votes`, `scrutin_individual_votes`, `scrutin_mises_au_point`.
- Sorties : mise à jour de `groupes(id, libelle, sigle)` et `deputes(id, nom, prenom)` ; `RapportResolution` : `groupes_references`, `groupes_resolus`, `groupes_non_resolus` (liste), `deputes_references`, `deputes_resolus`, `deputes_non_resolus` (liste), `noms_modifies` (liste `{id, ancien, nouveau}`), `avertissements`.

## Définitions
- **Identifiant référencé** : identifiant effectivement utilisé dans une table de votes ou de mises au point. On ne charge que ceux-là (minimisation : un référentiel contient des personnes et organes qui n'ont aucun rapport avec les scrutins).
- **Résolu** : l'identifiant exact figure dans le référentiel avec les champs requis non vides.
- **Non résolu** : toute autre situation ; le libellé reste `NULL`, le front affiche « libellé non résolu » avec l'identifiant (`.agents/CONVENTIONS.md`).

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Le référentiel n'est pas encore inspecté : les noms de champs sont à établir.

```text
# Notations
organes  = lire_sécurisé(référentiel organes)      # même lecture qu'ALG-01          [1]
acteurs  = lire_sécurisé(référentiel acteurs)
refs_g   = { groupe_id ≠ NULL dans les tables de votes }       # identifiants utilisés   [5]
refs_d   = { depute_id dans les votes et mises au point }
rapport  = RapportResolution vide

# Groupes
pour chaque id dans refs_g:
    si id = "PO0": ignorer                                     # ne désigne aucun organe [11]
    o = organes[id]
    si o absent:                                    non résolu                          [9]
    sinon si plusieurs contenus différents pour id: non résolu, "identifiant_ambigu"    [4]
    sinon si o n'est pas un groupe parlementaire:   non résolu, "organe_pas_un_groupe"  [6]
    sinon:
        libelle = texte(o.libelle) ; sigle = texte(o.sigle)    # NFC, trim, vide → null [2]
        si libelle vide: non résolu
        sinon:
            si groupes[id].libelle existe et ≠ libelle: rapport.noms_modifies += {id, ancien, nouveau}  [8]
            UPDATE groupes SET libelle, sigle WHERE id = ?                              [7]

# Députés (même schéma)
pour chaque id dans refs_d:
    a = acteurs[id]
    si a présent, unique et nom non vide:
        UPDATE deputes SET nom = texte(a.nom), prenom = texte(a.prenom) WHERE id = ?    [3, 7]
    sinon: non résolu                                           # nom = NULL

# Règles absolues
jamais d'appariement par nom, sigle ou ressemblance ; jamais de création de ligne      [10, 7]

rapport.groupes_resolus + groupes_non_resolus = |refs_g|   ;   idem pour les députés
journaliser le rapport en entier                                                        [12]
affichage d'un non résolu : "libellé non résolu (" + id + ")"
```

Propriété : un nom n'est écrit que si l'identifiant exact (`PO…` ou `PA…`) figure dans le référentiel ; sinon la valeur reste `NULL` et le front l'indique. Cibles connues : 13 groupes et 652 députés référencés.

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Lire les archives de référentiel avec la même lecture sécurisée qu'ALG-01 (liste blanche de noms, limites de taille, UTF-8 strict, JSON sans clé dupliquée) | Un référentiel est une entrée externe comme les scrutins ; les mêmes risques s'appliquent |
| 2 | Pour chaque organe : valider l'identifiant (`^PO[1-9][0-9]*$`), normaliser le libellé et le sigle (NFC, espaces de début et de fin retirés, chaîne vide → `null`), relever le champ qui distingue les groupes parlementaires (à établir) | Mêmes règles de texte que ALG-02 (N5) ; le texte intérieur n'est jamais réécrit |
| 3 | Pour chaque acteur : valider l'identifiant (`^PA[1-9][0-9]*$`), normaliser nom et prénom comme à l'étape 2 | Idem |
| 4 | Si un identifiant apparaît plusieurs fois avec des contenus différents : erreur `identifiant_ambigu` pour cet identifiant (non résolu) ; avec un contenu identique : avertissement | Deux contenus pour un identifiant empêchent de choisir sans deviner |
| 5 | Ne retenir que les identifiants référencés (groupes : valeurs non nulles de `groupe_id` ; députés : `depute_id` des votes et des mises au point) | Minimisation ; borne la taille des données publiées |
| 6 | Un identifiant référencé comme groupe qui existe dans le référentiel mais n'est **pas** un groupe parlementaire : non résolu, avertissement `organe_pas_un_groupe` | On ne présente jamais comme « groupe » un organe d'un autre type |
| 7 | Écrire `libelle`, `sigle`, `nom`, `prenom` pour les identifiants résolus, par `UPDATE … WHERE id = ?` (requêtes paramétrées) ; ne jamais créer de ligne ici | La création des lignes est faite par ALG-07 ; ALG-09 ne fait que nommer |
| 8 | Si la base contient déjà un nom différent pour le même identifiant : remplacer et ajouter `{id, ancien, nouveau}` à `noms_modifies` | Un changement de nom à la source est une information à examiner, jamais appliquée en silence |
| 9 | Les identifiants non résolus gardent `NULL` ; les lister dans le rapport avec leur nombre d'occurrences (scrutins ou votes) | Aucun nom inventé ; l'ampleur du manque est visible |
| 10 | Ne **jamais** apparier par nom, par sigle ou par proximité de texte ; ne jamais copier le groupe actuel d'un député vers un scrutin | Garantie 1 et règle du cahier §2 : seuls les identifiants officiels font foi |
| 11 | Ne jamais insérer `PO0` dans `groupes` (valeur de référence non résolue, déjà `NULL` côté `scrutin_group_votes`) | `PO0` ne désigne aucun organe |
| 12 | Retourner le rapport, journalisé en entier | Traçabilité |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Identifiant de groupe absent du référentiel | `libelle = NULL`, listé non résolu | étape 9 |
| Identifiant de député absent | `nom = NULL`, `prenom = NULL`, listé non résolu | étape 9 |
| Deux acteurs homonymes, identifiants différents | deux lignes distinctes, aucun regroupement | étape 10 |
| Identifiant présent deux fois, contenus différents | non résolu, erreur `identifiant_ambigu` | étape 4 |
| Libellé vide dans le référentiel | `null` : non résolu | étape 2 |
| Organe référencé comme groupe mais d'un autre type | non résolu, avertissement | étape 6 |
| Libellé modifié depuis le dernier import | mise à jour + entrée dans `noms_modifies` | étape 8 |
| `PO0` | jamais dans `groupes` ; rien à résoudre | étape 11 |
| Les deux références `PO872880` et `PO847173` ont le même libellé | deux lignes `groupes` distinctes conservées ; aucune fusion | constat ; voir question 3 |
| Référentiel absent ou illisible | l'import des scrutins reste valide, tous les noms restent `NULL` ; `echec` du traitement des noms journalisé | le site reste utilisable avec « libellé non résolu » |

## Exemples chiffrés (à reproduire en test)
À établir après l'inspection des référentiels. Cibles déjà connues : `groupes_references = 13`, `deputes_references = 652` sur l'archive réelle ; `PO0` jamais résolu ; `groupes_non_resolus` et `deputes_non_resolus` : à mesurer. Les tests utiliseront des extraits **réels** des référentiels.

## Invariants vérifiés
- Aucun nom n'est écrit sans correspondance exacte d'identifiant.
- Aucune ligne `groupes` ne porte l'identifiant `PO0`.
- Le nombre de lignes de `groupes` et de `deputes` n'est pas modifié par ALG-09.
- `groupes_resolus + groupes_non_resolus = groupes_references` ; idem pour les députés.
- Deux résolutions des mêmes entrées produisent la même base.

## Questions à trancher avant de coder
1. **Source des référentiels** : quels fichiers, quelle URL ? Je ne l'ai pas vérifié. Peux-tu fournir les fichiers, ou m'autoriser à les chercher et les inspecter ?
2. **Réutiliser ALG-01** avec un « profil » (motif de nom, limites) propre aux référentiels : modification d'ALG-01 (motif de nom actuellement propre aux scrutins). D'accord pour ajouter un paramètre de profil ?
3. **Groupe renommé ou remplacé** (`PO872880` et `PO847173`) : je ne fusionne pas. La fiche de groupe affichera deux entrées, chacune avec le nombre de scrutins concernés. Veux-tu une présentation reliant les deux, uniquement si le référentiel l'indique officiellement ?
4. **Noms de députés affichés** : nom et prénom seuls, sans autre donnée personnelle du référentiel. D'accord ?
5. **Libellé de groupe daté** : si le référentiel révèle des libellés variant dans le temps, la table `groupes` (un seul libellé) ne suffira plus ; décision à reprendre après l'inspection.

## Sources et constats
Cahier technique §2 (référentiels, affiliation du scrutin), §4 (`groupes`, `deputes`) ; `.agents/DECISIONS.md` (2026-10-22 « Priorité à l'ETL, noms résolus dès la phase A » et « Source : open data officiel ») ; `.agents/CONVENTIONS.md` ; `docs/methodology.md` (garantie 1) ; mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction, structure et règles seulement ; référentiels à inspecter.
