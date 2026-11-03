# ALG-04 — Extraction d'un scrutin (totaux, groupes, votes nominatifs)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Projeter un `ScrutinNormalise` (sortie d'ALG-02) en lignes prêtes à être écrites dans les tables du cahier §4 (`scrutins`, `scrutin_totals`, `scrutin_group_votes`, `scrutin_individual_votes`, `scrutin_mises_au_point`), avec les comptages nécessaires aux contrôles d'ALG-05, sans écrire en base et sans rien calculer d'interprétatif.

## Périmètre
Inclus : choix des champs stockés, construction des lignes, clés, ordre, identifiants vus, comptages de contrôle.
Exclus : lecture de l'archive (ALG-01), conversion des valeurs (ALG-02), position majoritaire (ALG-03, calculée à l'export, jamais stockée ici), rattachement des mises au point à un groupe (ALG-06), contrôles (ALG-05), écriture (ALG-07).

## Constats (mesurés le 2026-11-03 sur les 8 877 fichiers)
- `titre` est identique à `objet.libelle` dans 8 877 scrutins sur 8 877 : la colonne `objet` du cahier ne porte aucune information en plus de `titre`.
- 146 groupes (14 scrutins) ont la référence `PO0` : plusieurs groupes d'un même scrutin n'ont alors **pas de clé** (voir ALG-02, constat 9). La clé `(scrutin_id, groupe_id)` du cahier ne tient donc pas ; il faut le rang.
- Aucun député n'apparaît deux fois dans les mises au point d'un scrutin, et aucun député n'est à la fois dans `miseAuPoint` et dans `dysfonctionnement` : la clé `(scrutin_id, depute_id)` du cahier est utilisable pour les deux origines réunies.

## Entrées / Sorties
- Entrées :
  - `scrutin` : `ScrutinNormalise` valide (sans erreur) ;
  - `entree` : `{nom, sha256_fichier}` de la sortie d'ALG-01 ;
  - `source_url` : URL de l'archive (provenance fournie par ALG-13, ou `null` en local) ;
  - `importe_le` : horodatage UTC **fourni par l'appelant** (l'algorithme ne lit jamais l'horloge, pour rester déterministe) ;
  - `version_etl` : identifiant de version des règles (ALG-02, ALG-04), pour la détection de changement d'ALG-07.
- Sortie : `LotScrutin` =

| Élément | Contenu |
|---------|---------|
| `scrutins` (1 ligne) | `id`, `numero`, `legislature`, `date_scrutin`, `titre`, `objet`, `type_vote_code`, `type_vote_libelle`, `resultat_code`, `source_url`, `source_hash`, `imported_at`, `etl_version` |
| `scrutin_totals` (1 ligne) | `scrutin_id`, `pour`, `contre`, `abstentions`, `non_votants`, `suffrages_exprimes`, `nombre_votants` |
| `scrutin_group_votes` (n lignes) | `scrutin_id`, `rang`, `groupe_id` (nullable), `membres`, `pour`, `contre`, `abstentions`, `non_votants`, `position_majoritaire_source` |
| `scrutin_individual_votes` (lignes) | `scrutin_id`, `depute_id`, `groupe_rang`, `groupe_id` (nullable), `mandat_id`, `position`, `par_delegation` (0/1), `cause` (nullable : `MG`, `PSE`, `PAN`) |
| `scrutin_mises_au_point` (lignes) | `scrutin_id`, `depute_id`, `origine` (`mise_au_point` \| `dysfonctionnement`), `position_declaree`, `par_delegation`, `groupe_rang` = `NULL`, `groupe_id` = `NULL`, `position_initiale` = `NULL` (renseignés par ALG-06) |
| `groupes_vus`, `deputes_vus` | identifiants distincts rencontrés (groupes non nuls ; députés des votes **et** des mises au point), pour ALG-07 et ALG-09 |
| `comptages` | par groupe et par position : nombre de lignes de votes produites ; pour le scrutin : même chose par position (sert d'entrée à ALG-05, calculé à partir des lignes produites, pas des compteurs source) |

### Écarts avec le schéma du cahier §4 (modification d'interface : à valider avant tout code)
1. `scrutin_group_votes` : clé `(scrutin_id, rang)` au lieu de `(scrutin_id, groupe_id)`, `groupe_id` nullable. Sans cela les 146 groupes `PO0` ne peuvent pas être stockés sans être inventés ou perdus.
2. `scrutin_individual_votes` : ajout de `groupe_rang` (lien vers la ligne de groupe) et de `cause`. `groupe_id` devient nullable. La cause (`MG`, `PSE`, `PAN`) est exigée par l'affichage des non-votants (méthodologie, présence au scrutin).
3. `scrutin_mises_au_point` : ajout de `origine`, pour ne pas confondre mise au point et dysfonctionnement (ALG-02, étape 22), et de `groupe_rang`, pour désigner un groupe `PO0` (ALG-06).
4. `scrutins` : ajout de `etl_version` (voir ALG-07, étape 9).

### Champs normalisés non stockés (MVP)
`type_majorite`, `nbr_suffrages_requis`, `session_ref`, `seance_ref`, `organe_ref` du scrutin, `quantieme_jour_seance`, `lieu_vote`, `demandeur_texte`, `dossier_ref`, `dossier_libelle`, `mode_publication`, `non_votants_volontaires` (toujours 0), `abstentions_doublon_source` (copie de `abstentions`). Tous restent retrouvables dans le fichier source grâce à `source_hash` et au nom du fichier. Voir question 3.

## Définitions
- Une « ligne de vote » est un votant nominatif unique du scrutin (ALG-02 garantit qu'aucun `acteur_ref` n'est en double).
- `groupe_rang` est le rang 1..n du groupe dans le fichier source (ALG-02, étape 12).
- `par_delegation` est stocké en 0/1 (le cahier prévoit un entier).

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Vérifier que `entree.nom` sans extension est égal à `scrutin.id` ; sinon erreur `identite` | Un lot ne doit jamais associer le contenu d'un scrutin à l'empreinte d'un autre |
| 2 | `scrutins` ← `id`, `numero`, `legislature`, `date_scrutin`, `titre`, `objet` (= `objet_libelle`), `type_vote_code`, `type_vote_libelle`, `resultat_code` (= `sort_code`) ; `source_url`, `source_hash` (= `entree.sha256_fichier`), `imported_at` (= `importe_le`), `etl_version` | Une seule ligne par scrutin ; la provenance exigée par la garantie 4 est écrite avec la donnée |
| 3 | `scrutin_totals` ← `pour`, `contre`, `abstentions`, `non_votants`, `suffrages_exprimes`, `nombre_votants` du scrutin, tels quels | Totaux officiels, jamais recalculés à partir des groupes (c'est le rôle d'ALG-05 de les comparer) |
| 4 | Pour chaque groupe dans l'ordre du fichier : une ligne `scrutin_group_votes` avec `rang`, `groupe_id` (= `organe_ref`, éventuellement `null`), `membres`, `pour`, `contre`, `abstentions`, `non_votants` (issus de `decompteVoix`), `position_majoritaire_source` | La clé est le rang ; une référence non résolue reste `null`, jamais devinée |
| 5 | Pour chaque groupe, pour chaque votant (ordre déjà fixé par ALG-02) : une ligne `scrutin_individual_votes` avec `depute_id` (= `acteur_ref`), `groupe_rang`, `groupe_id` du groupe, `mandat_id`, `position`, `par_delegation` (0/1), `cause` | L'affiliation est celle du scrutin, jamais l'affiliation actuelle (cahier §2) |
| 6 | Pour chaque ligne de mise au point puis de dysfonctionnement : une ligne `scrutin_mises_au_point` avec `origine`, `position_declaree`, `par_delegation`, `groupe_id` et `position_initiale` à `NULL` | Le rattachement exige la recherche dans les votes nominatifs : c'est la fiche ALG-06, pas ici |
| 7 | Vérifier l'unicité des clés : `(rang)` dans le scrutin, `depute_id` dans les votes, `depute_id` dans les mises au point (origines réunies) ; doublon → erreur `cle_dupliquee` | Une clé primaire violée se détecte ici avec un message clair plutôt qu'à l'écriture |
| 8 | Collecter `groupes_vus` (valeurs non nulles, sans doublon, triées) et `deputes_vus` (votes et mises au point, sans doublon, triés) | ALG-07 doit créer les lignes `groupes` et `deputes` manquantes (sans nom) avant d'insérer, pour respecter les clés étrangères ; ALG-09 renseigne les noms |
| 9 | Calculer `comptages` en dénombrant les **lignes produites** à l'étape 5 (par groupe et par position, puis pour le scrutin) | Les contrôles d'ALG-05 comparent deux sources indépendantes : les compteurs de la source (étapes 3 et 4) et le nombre de lignes réellement produites |
| 10 | Trier chaque table par clé primaire ; retourner le `LotScrutin` sans aucune écriture | Sortie déterministe (garantie nécessaire à ALG-11) ; la fonction est pure et testable seule |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Groupe avec `organe_ref = null` | ligne de groupe avec `groupe_id = NULL`, ses votes avec `groupe_id = NULL` et `groupe_rang` renseigné, aucune ligne dans `groupes_vus` | étapes 4, 5, 8 |
| 12 groupes `PO0` dans un scrutin | 12 lignes de groupe de rangs 1 à 12, pas de collision de clé | étape 4 |
| Groupe sans aucun vote nominatif | une ligne de groupe, zéro ligne de vote | cas normal (9 547 groupes sans position exprimée) |
| Scrutin sans mise au point | zéro ligne `scrutin_mises_au_point` | cas normal (7 343 scrutins sur 8 877 n'ont aucune ligne de mise au point, dysfonctionnements non comptés) |
| `entree.nom` ≠ `scrutin.id` | erreur `identite` | étape 1 |
| Même député dans deux mises au point du scrutin | erreur `cle_dupliquee` (0 cas observé) | étape 7 ; signalerait un changement de la source |
| `importe_le` absent | erreur de programmation, pas de valeur par défaut | pas d'horloge cachée |

## Exemples chiffrés (à reproduire en test)
Sur l'ensemble des 8 877 fichiers (mesures du 2026-11-03, à confirmer par le test d'intégration) :

| Mesure | Valeur attendue |
|--------|-----------------|
| Lignes `scrutins` / `scrutin_totals` | 8 877 / 8 877 |
| Lignes `scrutin_group_votes` | 106 524, dont 146 avec `groupe_id = NULL` |
| Lignes `scrutin_individual_votes` | 1 323 978 (pour 580 652 ; contre 643 533 ; abstention 75 754 ; non-votant 24 039) |
| Lignes `scrutin_mises_au_point` | 3 406 (3 243 mises au point + 163 dysfonctionnements), dans 1 534 scrutins pour les mises au point |

Sur fichiers réels : `VTANR5L17V489` → 12 lignes de groupe avec `groupe_id = NULL`, rangs 1 à 12 ; `VTANR5L17V1017`, groupe `PO845407` → un vote `non_votant` avec `cause = PAN`.

## Invariants vérifiés
- Pour chaque groupe et chaque position, nombre de lignes de vote = compteur correspondant de `scrutin_group_votes` (le contrôle est dans ALG-05 ; ALG-04 fournit les deux grandeurs).
- Aucune clé primaire en double dans le lot.
- Chaque `groupe_id` non nul de `scrutin_group_votes` et de `scrutin_individual_votes` figure dans `groupes_vus` ; chaque `depute_id` figure dans `deputes_vus`.
- Deux extractions du même `ScrutinNormalise` produisent exactement le même lot.

## Questions à trancher avant de coder
1. **Clé de `scrutin_group_votes`** : rang plutôt qu'identifiant, avec `groupe_id` nullable (écart 1). Alternative écartée : générer un identifiant fictif (`PO0#3`), qui introduirait une valeur inventée dans les tables. D'accord ?
2. **Colonnes ajoutées** (`groupe_rang` dans deux tables, `cause`, `origine`, `etl_version`) : modification d'interface du schéma du cahier. D'accord ?
3. **Champs non stockés** : veux-tu conserver `type_majorite` (utile pour afficher « majorité requise »), `nbr_suffrages_requis`, `dossier_ref` (utile pour regrouper les votes d'un même texte, cahier §6) ? Je propose de ne rien ajouter tant qu'une page ne les affiche pas.
4. **Colonne `objet`** : identique à `titre` dans 100 % des scrutins. On la supprime, ou on la garde par fidélité au cahier ?

## Sources et constats
Cahier technique §2, §4, §5.2 (règles 3 et 4) et §5.3 ; `docs/algorithmes/ALG-02-normalisation.md` (constats 9 et 10, sortie `ScrutinNormalise`) ; `docs/methodology.md` (garantie 4, présence au scrutin) ; `.agents/CONVENTIONS.md` (affiliation du scrutin).

## Historique
- v1 (2026-11-03) : première rédaction.
