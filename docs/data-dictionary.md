# Dictionnaire de données — contrat ETL → site (`/data/v1/`)

Version du schéma : `v1` (2026-11-18). Source de vérité exécutable : `etl/src/etl/algos/alg11_schemas.py` ; chaque fichier produit par l'ETL est validé contre son schéma avant publication (ALG-11.10), et un fichier non conforme n'est jamais publié. Spécification de la production : [ALG-11](algorithmes/ALG-11-export-statique.md).

## Règles communes
- JSON, UTF-8 sans BOM, clés triées, sans espace de mise en forme, un saut de ligne final. Aucun `NaN` ni infini.
- Mêmes entrées, mêmes octets : aucune heure issue de l'horloge d'exécution ; `donnees_du` est lue dans la base.
- Un objet a exactement les clés listées (une clé en trop ou manquante est une erreur). `null` n'est admis que là où le type est « ou nul ».
- Les groupes et les députés sont désignés par leur identifiant (`PO…`, `PA…`) ; leurs noms ne sont écrits que dans `groupes.json` et `deputes.json`. Un nom non résolu vaut `null` : le site affiche « libellé non résolu » avec l'identifiant.
- Positions de vote : `pour`, `contre`, `abstention`, `non_votant`. Position majoritaire : `pour`, `contre`, `abstention`, `aucune` (avec `raison_absence` : `aucun_vote_exprime` ou `egalite`).
- Les chiffres officiels ne sont jamais modifiés. Une mise au point ne produit qu'une **correction affichée à côté** (`correction_mise_au_point`).
- Aucun champ ne porte une couleur, un rang de groupe, un score ou une note.

## Fichiers

| Fichier | Nombre | Contenu |
|---------|--------|---------|
| `meta.json` | 1 | Provenance et comptes |
| `scrutins-index.json` | 1 | Liste des fragments d'index |
| `scrutins-index/AAAA-MM.json` | un par mois ayant des scrutins | Une ligne compacte par scrutin du mois |
| `scrutins/<id>.json` | un par scrutin | Détail complet, votes individuels inclus |
| `groupes.json` | 1 | Liste des groupes |
| `groupes/<id>.json` | un par groupe identifié | Une ligne par scrutin du groupe |
| `deputes.json` | 1 | Noms des députés présents dans les votes |
| `stats.json` | 1 | Indicateurs d'ALG-10 |
| `qualite.json` | 1 | Page « Qualité des données » |
| `manifeste.json` | 1 | Empreintes pour le garde-fou de déploiement et l'audit |

Limites de l'hébergement : moins de 20 000 fichiers au total (alerte à 15 000, échec de l'export à 19 000), aucun fichier au-delà de 20 Mio (alerte à 1 Mio pour les fichiers chargés par le navigateur ; `manifeste.json`, lu seulement par le garde-fou de déploiement, en est exclu).

### `meta.json`
`schema` (`"v1"`), `nombre_scrutins` (entier ≥ 1), `nombre_groupes`, `premiere_date`, `derniere_date` (AAAA-MM-JJ), `donnees_du` (date du dernier import terminé, lue dans la base), `version_donnees` (16 premiers caractères de `donnees_sha256`), `archive_sha256`, `type_empreinte` (`fichier`, `manifeste` ou `non_renseigne`), `version_etl`, `version_regles_classification`.

### `scrutins-index.json`
`fragments` : liste de `{mois (AAAA-MM), nombre_scrutins (≥ 1), fichier}`, triée par mois.

### `scrutins-index/AAAA-MM.json`
`mois`, `scrutins` : lignes triées par numéro de `{id, numero, date, titre, categorie {valeur, methode, a_verifier}, resultat, totaux {pour, contre, abstentions, non_votants, suffrages_exprimes, nombre_votants}}`.

### `scrutins/<id>.json`
- `id`, `numero`, `date`, `titre`, `type_vote {code, libelle}`, `resultat` (`adopte` ou `rejete`).
- `categorie {valeur, methode, confiance, a_verifier}` : catégorie d'ALG-08, avec la manière dont elle a été obtenue ; `a_verifier` est vrai pour toute catégorie déduite d'un titre.
- `source {fichier, sha256, archive_sha256, lien_officiel}` : `lien_officiel` = `https://www.assemblee-nationale.fr/dyn/17/scrutins/<numéro>`.
- `totaux {pour, contre, abstentions, non_votants, suffrages_exprimes, nombre_votants, sans_vote_enregistre}` : chiffres officiels ; `sans_vote_enregistre` est la somme de celui des groupes, `null` si un groupe n'est pas identifié.
- `groupes` : liste triée par effectif décroissant, puis identifiant, puis rang, de `{rang, groupe_id (ou null), ventilation_disponible, membres, pour, contre, abstentions, non_votants, sans_vote_enregistre (ou null), position_majoritaire (ou null), correction_mise_au_point (ou null)}`.
  - `rang` : rang du groupe dans le fichier source (clé du groupe dans le scrutin ; un groupe non identifié n'a pas d'identifiant).
  - `ventilation_disponible` : faux si `groupe_id` est nul ; la position majoritaire et le « sans vote enregistré » sont alors `null` (aucun indicateur n'est inventé).
  - `position_majoritaire {position, raison_absence, exprimes, m, majorite_absolue}` : calculée par ALG-03, jamais lue dans la source ; `exprimes` = pour + contre + abstentions ; `m` = effectif de la position la plus fréquente.
  - `correction_mise_au_point {pour_corrige, contre_corrige, abstentions_corrigees, position_officielle, position_corrigee, raison_absence_corrigee, change_position_majoritaire, nb_mises_au_point}` (ALG-06) : `null` s'il n'y a pas de mise au point à effet.
- `votes` : liste de `[depute_id, groupe_rang, position, par_delegation (0 ou 1), cause (ou null)]`, triée par rang du groupe, position, identifiant du député. `cause` (`MG`, `PSE`, `PAN`) n'existe que pour un non-votant.
- `mises_au_point`, `dysfonctionnements` : listes de `{depute_id, groupe_rang, groupe_id, position_initiale, position_declaree, par_delegation, statut (rattachee ou introuvable), effet (sans_effet, modifie_position ou null)}`. Les dysfonctionnements ne sont jamais appliqués aux effectifs corrigés.

### `groupes.json`
`groupes` : liste de `{id, libelle (ou null), sigle (ou null), nombre_scrutins}`, triée par libellé puis identifiant (non résolus à la fin, par identifiant). Deux identifiants peuvent porter le même sigle (groupe renommé) : ils restent deux groupes.

### `groupes/<id>.json`
`groupe_id`, `libelle`, `sigle`, `colonnes`, `scrutins`. **Format compact** (décision du 2026-11-18) : `colonnes` nomme une seule fois les colonnes, et `scrutins` est une liste de tableaux triée par numéro de scrutin, dans l'ordre de `colonnes` : `[scrutin_id, numero, date, categorie, membres, pour, contre, abstentions, non_votants, sans_vote_enregistre, position, raison_absence, exprimes, m, majorite_absolue]`. Les valeurs sont exactement celles d'un objet par ligne : la position majoritaire (`position`, `raison_absence`, `exprimes`, `m`, `majorite_absolue`) est simplement mise à plat. `colonnes` doit être égale à cette liste (le validateur la vérifie) ; un changement de colonnes passe par une nouvelle version du schéma.

### `deputes.json`
`deputes` : liste triée par identifiant de `{id, nom, prenom, civilite}` (chaque champ peut être `null` si le député n'est pas résolu).

### `stats.json`
`bornes` (défaut `[20, 40, 60, 80]`), `libelles_tranches` (bornes numériques seules, sans qualificatif), `selections` : liste de `{id, filtres, nombre_scrutins, groupes}` pour `toutes`, `categorie:<c>` et `annee:<aaaa>`. Chaque groupe : `groupe_id`, `nb_scrutins`, `nb_scrutins_exclus_groupe_non_identifie`, `membres_scrutins`, `personnes_exprimees`, `personnes_avec_vote`, `pour`, `contre`, `abstentions`, `non_votants`, `sans_vote_enregistre`, `exprimes`, `scrutins_par_position_majoritaire {pour, contre, abstention, egalite, aucun_vote_exprime}`, `repartition_part_majoritaire` (un nombre de scrutins par tranche). Les groupes sont triés par libellé, jamais selon un indicateur. Les effectifs de plusieurs scrutins sont des **membres-scrutins** ; `personnes_*` sont des nombres de personnes distinctes.

### `qualite.json`
`schema`, `statut_reconciliation` (`ok` ou `ecarts_connus`), `nombre_scrutins`, `archive_sha256`, `donnees_du`, `ecarts_connus` (liste de `{controle, scrutin_id, detail, attendu, obtenu, motif, valide_le}`), `classification {par_categorie, a_verifier, indetermine}`, `noms_non_resolus {groupes, deputes}`, `modifications` (`null` s'il n'y a pas de version publiée précédente, sinon `{nouveaux, supprimes, nombre_supprimes, modifies_chiffres, nombre_modifies_chiffres, modifies_autres, nombre_modifies_autres}` ; les listes sont limitées à 200 identifiants, les nombres sont exacts).

### `manifeste.json`
`schema`, `entrees` (archive, versions des algorithmes, version des règles de classification : ce qui peut changer le résultat), `empreinte_entrees` (SHA-256 de `entrees`, sérialisé comme les autres fichiers), `donnees_sha256` (SHA-256 de la liste `chemin<TAB>sha256` de tous les fichiers sauf `manifeste.json` et `meta.json`), `scrutins` : `{<id>: {source_hash, empreinte_chiffres}}`. `empreinte_chiffres` couvre le résultat, les totaux, les compteurs de chaque groupe et la liste complète des votes : son changement signale qu'un chiffre officiel publié a changé.

## Historique
- 2026-11-18 : première version, écrite avec le code d'ALG-11.
