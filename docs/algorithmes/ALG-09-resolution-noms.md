# ALG-09 — Résolution des noms (référentiels des groupes et des députés)
Statut : Brouillon    Version : 2    Date : 2026-11-14

> **Référentiels inspectés le 2026-11-14** (voir « Constats sur les référentiels »). Les noms de champs, la structure et les chiffres de cette fiche viennent de cette inspection.

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

## Constats sur les référentiels (inspection du 2026-11-14)
Source : fichier officiel « Acteurs, mandats et organes, historique » (AMO30), `https://data.assemblee-nationale.fr/static/openData/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip`. Publié sur data.assemblee-nationale.fr avec une date de mise à jour (2026-11-14 02:34) et une empreinte **MD5** affichée sur la page (`2f43c427…`) ; le fichier téléchargé a la même empreinte. Licence : Licence Ouverte / Open Licence (mention de la paternité obligatoire).
- **Archive** : ZIP de 13 736 513 octets, 14 059 entrées, 96 081 594 octets décompressés ; plus gros fichier 364 530 octets, rapport de compression maximal 26,2 ; trois dossiers : `json/organe/PO<n>.json` (10 824), `json/acteur/PA<n>.json` (3 176), `json/deport/…` (59). Un fichier par identifiant ; UTF-8. Les limites d'ALG-01 (50 000 entrées, 5 Mio par entrée, 1 Gio au total, ratio 100) conviennent ; **le motif de nom d'ALG-01 ne convient pas** (question 2).
- **Groupes** : un organe est un groupe parlementaire si `organe.codeType = "GP"` (type `GroupePolitique_type`). Champs : `organe.uid` (identique au nom de fichier), `organe.libelle` (libellé complet), `organe.libelleAbrege` (sigle), `organe.libelleAbrev` (variante en capitales, non utilisée), `organe.viMoDe.dateDebut` et `dateFin` (période d'existence), `organe.legislature = "17"`.
- **Députés** : `acteur.uid` est un objet `{"#text": "PA…"}` ; nom et prénom dans `acteur.etatCivil.ident.nom` et `.prenom` (civilité `civ` disponible, non utilisée). Le fichier contient aussi, pour chaque acteur, la date et le lieu de naissance, des adresses postales et électroniques, des numéros de téléphone, la profession, les mandats : **aucune de ces données n'est lue ni publiée** (minimisation).
- **Couverture** : les 13 groupes réels de l'archive des scrutins sont tous présents (type `GP`) ; `PO0` est **absent** du référentiel, comme prévu (il ne désigne aucun organe). Les 652 députés des votes sont tous présents.
- **Qualité** : aucun nom ou prénom vide ; aucun libellé ou sigle de groupe vide ; aucun texte hors NFC ni avec espaces de début, de fin ou doubles ; aucun homonyme complet (nom + prénom) parmi les 652 ; caractères non alphabétiques dans les noms : apostrophe (2), parenthèses (2 + 2), barre oblique (1).
- **Libellés datés** : chaque identifiant de groupe a **un seul** libellé. Le renommage du groupe UDR est représenté par **deux organes** de même sigle `UDR` : `PO847173` « UDR » (2024-09-12 → 2025-09-04), puis `PO872880` « Union des droites pour la République » (depuis 2025-09-05), même couleur et même numéro de préséance. Aucun champ ne les relie : ils restent deux groupes distincts (décision du 2026-11-14), la table `groupes` (un libellé par identifiant) suffit.
- Aucune donnée n'a été écrite dans le dépôt ; les fichiers téléchargés sont dans `data/` (ignoré par Git).

## Entrées / Sorties
- Entrées : archive(s) de référentiel (organes, acteurs), base de travail avec les identifiants `groupes_vus` et `deputes_vus` déjà importés (ALG-07), identifiants référencés lus dans `scrutin_group_votes`, `scrutin_individual_votes`, `scrutin_mises_au_point`.
- Sorties : mise à jour de `groupes(id, libelle, sigle)` et `deputes(id, nom, prenom)` ; `RapportResolution` : `groupes_references`, `groupes_resolus`, `groupes_non_resolus` (liste), `deputes_references`, `deputes_resolus`, `deputes_non_resolus` (liste), `noms_modifies` (liste `{id, ancien, nouveau}`), `avertissements`.

## Définitions
- **Identifiant référencé** : identifiant effectivement utilisé dans une table de votes ou de mises au point. On ne charge que ceux-là (minimisation : un référentiel contient des personnes et organes qui n'ont aucun rapport avec les scrutins).
- **Résolu** : l'identifiant exact figure dans le référentiel avec les champs requis non vides.
- **Non résolu** : toute autre situation ; le libellé reste `NULL`, le front affiche « libellé non résolu » avec l'identifiant (`.agents/CONVENTIONS.md`).

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Les noms de champs sont ceux de l'inspection du 2026-11-14.

```text
# Notations
organes  = lire_sécurisé(AMO30, json/organe/)      # même lecture qu'ALG-01          [1]
acteurs  = lire_sécurisé(AMO30, json/acteur/)
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
| 2 | Pour chaque organe : valider l'identifiant (`^PO[1-9][0-9]*$`), normaliser le libellé et le sigle (NFC, espaces de début et de fin retirés, chaîne vide → `null`), relever `codeType` (groupe parlementaire si `GP`) ; libellé = `libelle`, sigle = `libelleAbrege` | Mêmes règles de texte que ALG-02 (N5) ; le texte intérieur n'est jamais réécrit |
| 3 | Pour chaque acteur : valider l'identifiant (`^PA[1-9][0-9]*$`, lu dans `uid.#text`, égal au nom du fichier), normaliser `etatCivil.ident.nom` et `.prenom` comme à l'étape 2 | Idem ; seules ces deux valeurs sont lues |
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
Sur l'archive de 8 877 scrutins et le référentiel AMO30 du 2026-11-14 : `groupes_references = 13` (hors `PO0`), `groupes_resolus = 13`, `groupes_non_resolus = 0` ; `deputes_references = 652`, `deputes_resolus = 652`, `deputes_non_resolus = 0` ; `PO0` jamais résolu ni inséré. Cas réels : `PO847173` → libellé « UDR », sigle `UDR` ; `PO872880` → « Union des droites pour la République », sigle `UDR` ; deux lignes `groupes` distinctes. Les tests utiliseront des **extraits réels** du référentiel (quelques fichiers `organe` et `acteur`, sans les données personnelles non lues) et des cas construits pour les erreurs (identifiant absent, doublon, organe qui n'est pas un groupe).

## Invariants vérifiés
- Aucun nom n'est écrit sans correspondance exacte d'identifiant.
- Aucune ligne `groupes` ne porte l'identifiant `PO0`.
- Le nombre de lignes de `groupes` et de `deputes` n'est pas modifié par ALG-09.
- `groupes_resolus + groupes_non_resolus = groupes_references` ; idem pour les députés.
- Deux résolutions des mêmes entrées produisent la même base.

## Décisions du 2026-11-14 et questions restantes
Tranché :
1. Source des référentiels : AMO30 (voir « Constats sur les référentiels »), téléchargé par ALG-13 avec une adresse et des seuils propres.
3. `PO872880` et `PO847173` : deux groupes distincts, aucun lien affiché ; le référentiel ne les relie pas (même sigle `UDR`, périodes successives).
5. Libellé de groupe daté : sans objet, un seul libellé par identifiant ; la table `groupes` suffit.

Restant ouvert :
2. **Profil de lecture d'ALG-01** : les entrées du référentiel ont un autre motif de nom (`json/organe/PO<n>.json`, `json/acteur/PA<n>.json`, `json/deport/…`) que les scrutins. Proposition : ajouter à ALG-01 un paramètre de profil (motif de nom, identité contenu/nom, limites), le profil « scrutins » restant la valeur par défaut. D'accord ?
4. **Noms de députés affichés** : nom et prénom seuls, sans civilité ni autre donnée personnelle du référentiel. D'accord ?

## Sources et constats
Cahier technique §2 (référentiels, affiliation du scrutin), §4 (`groupes`, `deputes`) ; `.agents/DECISIONS.md` (2026-10-22 « Priorité à l'ETL, noms résolus dès la phase A » et « Source : open data officiel ») ; `.agents/CONVENTIONS.md` ; `docs/methodology.md` (garantie 1) ; mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction, structure et règles seulement ; référentiels à inspecter.
- v2 (2026-11-14) : référentiel AMO30 téléchargé et inspecté ; champs, structure, couverture (13/13 groupes, 652/652 députés) et qualité établis ; constats UDR.
