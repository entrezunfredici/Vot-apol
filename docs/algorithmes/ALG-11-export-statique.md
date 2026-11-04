# ALG-11 — Export statique (fichiers JSON, déterminisme, limites Cloudflare)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Produire, à partir de la base de travail, l'ensemble des fichiers JSON publics (`/data/v1/…`) : contenu exact et vérifiable, octets identiques à entrée identique, limites de l'hébergement respectées, aucune écriture partielle. Ces fichiers sont l'unique interface entre l'ETL et le site.

## Périmètre
Inclus : liste et contenu des fichiers, ordre, sérialisation, découpage, contrôles avant publication, rapport d'export.
Exclus : calcul de la position majoritaire (ALG-03), des mises au point corrigées (ALG-06 B), des indicateurs (ALG-10), de la catégorie (ALG-08) : ils sont appelés ici, pas redéfinis ; décision de publier (ALG-12) ; déploiement ; code du front.

## Constats (mesurés le 2026-11-03 ; la taille repose sur un format compact de démonstration, non figé)
- Votes enregistrés : **149 par scrutin en moyenne, 574 au maximum** (1 323 978 au total). La valeur « environ 577 votants » de `.agents/DECISIONS.md` (décisions en suspens) est l'effectif de l'Assemblée, pas le nombre de votes enregistrés par scrutin.
- Taille d'un fichier de scrutin avec ses votes (identité, groupes, votes ; sans mises au point) : 3,7 Ko en moyenne, **12,6 Ko au maximum**, 31,5 Mio pour les 8 877 fichiers (9,0 Mio compressés en gzip, plus gros fichier : 2,9 Ko compressé). Les limites de 25 Mo par fichier sont sans rapport avec ces tailles.
- Ligne d'index compacte (id, numéro, date, titre, totaux) : 260 octets en moyenne, **2,2 Mio pour l'ensemble** : trop lourd pour un chargement unique sur mobile.
- Rythme : 8 877 scrutins pour 25 mois (octobre 2024 à octobre 2026), soit environ 360 scrutins par mois.
- **Limite de 20 000 fichiers (Cloudflare, gratuit) : le nombre de fichiers est la contrainte, pas la taille.** À ce rythme et avec un fichier par scrutin, la limite serait atteinte au printemps 2029 (fin normale de la législature : l'extrapolation est approximative, le rythme dépend du calendrier parlementaire). Avec en plus un fichier de votes par scrutin, elle serait atteinte dans environ 3 mois.

## Fichiers produits
Sous `/data/v1/` (le contrat du cahier §8, complété).

| Fichier | Contenu | Nombre |
|---------|---------|--------|
| `meta.json` | nombre de scrutins et de groupes, première et dernière date de scrutin, `donnees_du` (date de synchronisation, issue de la base), `version_donnees`, `archive_sha256`, `type_empreinte`, `version_etl`, `version_regles_classification`, `schema` | 1 |
| `scrutins-index.json` | liste des fragments : mois, nombre de scrutins, nom de fichier | 1 |
| `scrutins-index/AAAA-MM.json` | une ligne compacte par scrutin du mois : id, numéro, date, titre, catégorie (valeur, méthode, `a_verifier`), résultat, totaux | au plus 25 |
| `scrutins/<id>.json` | détail complet d'un scrutin (voir ci-dessous), **votes individuels inclus** | 8 877 |
| `groupes.json` | groupes (identifiant, libellé, sigle, ou « libellé non résolu »), nombre de scrutins où chacun apparaît | 1 |
| `groupes/<id>.json` | une ligne par scrutin du groupe : effectifs, position majoritaire (ALG-03), catégorie, date | 13 |
| `deputes.json` | identifiant, nom, prénom des députés présents dans les votes | 1 |
| `stats.json` | indicateurs d'ALG-10 pour les sélections précalculées | 1 |
| `qualite.json` | page « Qualité des données » : version, date, empreinte, écarts connus (ALG-05), scrutins modifiés depuis la publication précédente (ALG-12) | 1 |
| `manifeste.json` | pour chaque scrutin : `source_hash` et `empreinte_chiffres` (définie dans ALG-12) ; sert à ALG-12 et à l'audit | 1 |

Soit **8 922 fichiers au plus** pour les données actuelles, à comparer à la limite de 20 000 qui inclut aussi les fichiers du site lui-même.

### Contenu de `scrutins/<id>.json`
- Identité et provenance : `id`, `numero`, `date`, `titre`, `type_vote` (code, libellé), `resultat`, `categorie` (valeur, méthode, confiance, `a_verifier`), `source` (nom du fichier source, `sha256`, `archive_sha256`, lien officiel).
- `totaux` : `pour`, `contre`, `abstentions`, `non_votants`, `suffrages_exprimes`, `nombre_votants`, `sans_vote_enregistre` (somme de celui des groupes identifiés ; `null` si un groupe n'est pas identifié).
- `groupes` (tableau) : `rang`, `groupe_id` (ou `null`), `ventilation_disponible` (faux si `groupe_id` nul), `membres`, `pour`, `contre`, `abstentions`, `non_votants`, `sans_vote_enregistre`, `position_majoritaire` (position, raison d'absence, `exprimes`, `m`, `majorite_absolue`), `correction_mise_au_point` (ALG-06 B, ou `null`). **Non exporté** : `position_majoritaire_source` (audit, reste en base).
- `votes` (tableau compact) : `[depute_id, groupe_rang, position, par_delegation, cause]`.
- `mises_au_point` : lignes avec statut `rattachee` ou `introuvable` ; `dysfonctionnements` séparément.

## Entrées / Sorties
- Entrées : base de travail (après ALG-07, ALG-09, ALG-05 niveau base) ; `repertoire_sortie` ; modèle d'URL officielle ; paramètres de limites.
- Sorties : répertoire de fichiers complet ; `RapportExport` = `{fichiers_par_type, nombre_fichiers, octets_total, plus_gros_fichier (nom, octets), avertissements, statut}` avec `statut` ∈ `ok` | `echec`.

## Paramètres
| Paramètre | Valeur proposée | Justification |
|-----------|-----------------|---------------|
| `MAX_FICHIERS_ECHEC` | 19 000 | La limite est de 20 000 pour tout le déploiement ; il faut laisser de la place aux fichiers du site |
| `MAX_FICHIERS_AVERTISSEMENT` | 15 000 | Alerte précoce, sachant qu'environ 360 scrutins s'ajoutent par mois |
| `MAX_OCTETS_FICHIER_ECHEC` | 20 Mio | La limite est de 25 Mo par fichier ; 20 Mio laisse une marge |
| `MAX_OCTETS_FICHIER_AVERTISSEMENT` | 1 Mio | Les plus gros fichiers attendus (`groupes/<id>.json`, un fragment d'index) font quelques centaines de Ko : un fichier d'un Mio signale une dérive |

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Rien n'est publié tant que tout n'est pas valide.

```text
# Notations
base    = Entrée[base de travail]
sortie  = Entrée[répertoire_sortie]
tmp     = répertoire temporaire frère de sortie, vidé                              [2]

si ALG-05(niveau base).statut ∉ {"ok", "ecarts_connus"}: refuser d'exporter        [1]
si base n'a aucun scrutin: statut = "echec" ; arrêt

pour chaque scrutin s (numéro croissant):                                           [5]
    categorie  = ALG-08(s)
    groupes    = pour chaque groupe de s: ALG-03(p, c, a) ; ALG-06 B (correction)   [3]
    document   = { identité, source, totaux, groupes, votes, mises_au_point }
    écrire tmp/scrutins/<s.id>.json = sérialiser(document)                          [9]

écrire tmp/scrutins-index/AAAA-MM.json  pour chaque mois ayant des scrutins        [6]
écrire tmp/scrutins-index.json (liste des fragments)
écrire tmp/groupes.json, tmp/groupes/<id>.json, tmp/deputes.json                   [4, 5]
écrire tmp/stats.json = ALG-10 pour chaque groupe et sélection précalculée         [7]
écrire tmp/manifeste.json, puis tmp/qualite.json et tmp/meta.json                  [8]
        # aucune heure d'horloge : valeurs lues dans la base

sérialiser(x) = JSON, clés triées, séparateurs ",", ":", UTF-8 sans BOM, "\n" final   [9]

pour chaque fichier f de tmp:                                                       [10]
    f doit se relire en JSON ET respecter son schéma (docs/data-dictionary.md)
si nombre de fichiers > 19 000 ou un fichier > 20 Mio: statut = "echec"            [11]
    # avertissements à 15 000 fichiers ou 1 Mio
si une ligne d'index n'a pas de fichier, ou un groupe_id / depute_id est inconnu    [12]
   ou meta ≠ comptes de la base: statut = "echec"
comparer un échantillon de fichiers aux lignes de la base                           [13]

si statut ≠ "echec":                                                                [14]
    remplacer sortie par tmp (renommage)
sinon:
    supprimer tmp ; conserver l'ancien sortie intact
retourner RapportExport (nombre de fichiers, octets, plus gros fichier)             [15]
```

Propriétés : mêmes entrées → mêmes octets ; un échec laisse la version précédente intacte ; au plus 8 922 fichiers aujourd'hui pour 20 000 autorisés ; aucun champ de couleur, de rang de groupe ou de score. Exemple : `VTANR5L17V489` produit 12 groupes avec `groupe_id = null`, `ventilation_disponible = faux` et `sans_vote_enregistre = null`.

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Vérifier que `etl validate` (ALG-05 niveau base) vient de rendre `ok` ou `ecarts_connus` sur cette base ; sinon refuser d'exporter | On n'exporte jamais une base dont les totaux ne se recoupent pas |
| 2 | Écrire dans un répertoire temporaire frère de `repertoire_sortie`, vidé au départ | Aucune écriture partielle dans le répertoire final ; aucun fichier périmé conservé d'une exécution précédente |
| 3 | Pour chaque scrutin : lire ses lignes, appeler ALG-08 (catégorie), ALG-03 (position par groupe), ALG-06 B (corrections), construire le document ci-dessus | Chaque valeur dérivée vient de sa fiche, une seule fois |
| 4 | Remplacer l'identifiant d'un groupe ou d'un député par une référence (pas par un nom recopié) : les noms viennent de `groupes.json` et `deputes.json` | Un nom change à un seul endroit |
| 5 | Ordonner : scrutins par numéro croissant ; groupes d'un scrutin par effectif décroissant puis identifiant puis rang (ordre annoncé dans l'interface) ; votes par rang du groupe, position (`pour`, `contre`, `abstention`, `non_votant`), identifiant du député ; groupes dans `groupes.json` par libellé puis identifiant (non résolus : par identifiant, à la fin) | Aucun classement fondé sur un indicateur ; sortie déterministe |
| 6 | Découper l'index par mois de `date_scrutin` ; écrire `scrutins-index.json` (liste des fragments, un par mois ayant des scrutins) | 2,2 Mio d'index ne se chargent pas d'un seul bloc sur mobile |
| 7 | `stats.json` : appeler ALG-10 pour chaque groupe et chaque sélection précalculée (voir question 3) | Les sélections libres sont calculées dans le navigateur à partir de `groupes/<id>.json` |
| 8 | Construire `manifeste.json` à partir des documents en mémoire, calculer la différence avec le manifeste publié (ALG-12, étape 3), puis écrire `qualite.json` et `meta.json` : valeurs lues dans la base (`imports`, rapport ALG-05) et dans cette différence ; **aucune heure lue sur l'horloge système** | Mêmes entrées → mêmes octets ; `qualite.json` dépend de la différence |
| 9 | Sérialiser chaque fichier : JSON, clés triées (`sort_keys`), séparateurs `,` et `:` sans espace, `ensure_ascii = faux`, `allow_nan = faux`, UTF-8 sans BOM, un saut de ligne `\n` final | Octets reproductibles ; les diffs et l'empreinte sont exploitables |
| 10 | Valider chaque fichier : se relit comme du JSON ; conforme à son schéma documenté dans `docs/data-dictionary.md` | Le contrat est une interface publique : un fichier non conforme n'est jamais publié |
| 11 | Vérifier : nombre de fichiers ≤ `MAX_FICHIERS_ECHEC` (avertissement au-delà de `MAX_FICHIERS_AVERTISSEMENT`) ; aucun fichier au-delà de `MAX_OCTETS_FICHIER_ECHEC` (avertissement au-delà de `MAX_OCTETS_FICHIER_AVERTISSEMENT`) | Contraintes de l'hébergement (cahier §8 et §10) : l'export échoue plutôt que de produire un déploiement refusé |
| 12 | Vérifier l'intégrité des références : chaque ligne d'index a un fichier de scrutin ; chaque `groupe_id` et `depute_id` d'un scrutin figure dans `groupes.json` ou `deputes.json` ; `meta.json` égal aux comptes de la base | Aucun lien mort dans le site |
| 13 | Relire un échantillon de fichiers produits et comparer chaque chiffre aux lignes de la base (relecture indépendante de l'écriture) | Détecte un défaut de l'étape 3 avant publication (la vérification contre les fichiers bruts est ALG-14, voir question 6) |
| 14 | En cas de succès uniquement : remplacer `repertoire_sortie` par le répertoire temporaire (renommage) ; sinon supprimer le temporaire, conserver l'ancien répertoire, `statut = echec` | Un échec ne casse pas la version précédente (cahier §10, point 6) |
| 15 | Retourner le `RapportExport`, journalisé en entier | Traçabilité |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Groupe non identifié dans un scrutin | `groupe_id = null`, `ventilation_disponible = faux`, ses votes présents avec `groupe_rang`, aucun indicateur | ALG-02, question 1 |
| Nom de groupe ou de député non résolu | champ `libelle`/`nom` à `null` ; le front affiche « libellé non résolu » | garantie 1 |
| Mois sans scrutin | pas de fragment d'index pour ce mois | pas de fichier vide |
| Scrutin avec mise au point rattachée changeant la position majoritaire | `correction_mise_au_point` renseignée, chiffres officiels inchangés | ALG-06 |
| Nombre de fichiers : 15 500 | avertissement | alerte précoce |
| Nombre de fichiers : 19 500 | `echec`, répertoire final intact | étape 11 |
| Fichier de 21 Mio | `echec` | étape 11 |
| Base vide | `echec` (0 scrutin) | on ne publie jamais un site vide |
| Valeur `NaN` ou non finie | `echec` | étape 9 |
| Même base exportée deux fois | octets identiques, fichier par fichier | étape 9 |

## Exemples chiffrés (à reproduire en test)
- Archive réelle : `meta.nombre_scrutins = 8 877`, `meta.nombre_groupes = 13`, 8 877 fichiers `scrutins/<id>.json`, 13 fichiers `groupes/<id>.json`, `deputes.json` : 652 entrées, au plus 25 fragments d'index, total au plus 8 922 fichiers. Somme des lignes d'index = 8 877. Total des votes de tous les fichiers de scrutin = 1 323 978.
- `scrutins/VTANR5L17V489.json` : 12 groupes avec `groupe_id = null`, `ventilation_disponible = faux`, `sans_vote_enregistre = null` au niveau du scrutin.
- Deux exports successifs du même état de base : somme de contrôle de chaque fichier identique.

## Invariants vérifiés
- Mêmes entrées, mêmes octets.
- `nombre_fichiers ≤ MAX_FICHIERS_ECHEC` et aucun fichier au-delà de `MAX_OCTETS_FICHIER_ECHEC`, sinon aucun répertoire n'est remplacé.
- Aucune valeur des fichiers n'est calculée par le front sauf les sélections libres d'ALG-10 (conformité vérifiée par jeu de vecteurs).
- Aucun fichier ne contient d'heure issue de l'horloge d'exécution ni de secret.
- Aucun champ n'indique une couleur, un rang de groupe ou un score.

## Questions à trancher avant de coder
1. **Votes individuels** (décision en suspens du 2026-10-22) : je recommande **dans `scrutins/<id>.json`**. Raison chiffrée : un fichier voisin double le nombre de fichiers et dépasserait 20 000 d'ici environ trois mois ; inclus, un fichier fait 3,7 Ko en moyenne et 12,6 Ko au maximum. D'accord ?
2. **Passage à l'échelle** : même avec les votes inclus, un fichier par scrutin atteint le seuil d'échec de 19 000 fichiers début 2029. Je propose de **garder un fichier par scrutin** (simple, adressable) et de fixer l'alerte à 15 000 fichiers ; si nécessaire, passage à `/data/v2/` avec un regroupement par centaine de numéros. Une alternative est de regrouper dès maintenant ; elle alourdit chaque ouverture de scrutin. Ton avis ?
3. **Sélections précalculées de `stats.json`** : toutes les sélections (tous les scrutins), et par catégorie ? Par année ? Plus il y en a, plus le fichier grossit (13 groupes seulement, donc modeste).
4. **Nouveaux fichiers** : `deputes.json` (noms), `qualite.json` (garantie 6), `manifeste.json` (ALG-12), `scrutins-index.json` (liste de fragments). Ils modifient le contrat du cahier §8 : à valider avant tout code.
5. **Validation des schémas** : la bibliothèque `jsonschema` n'est pas dans la bibliothèque standard ; elle ajouterait une dépendance de développement. Alternative : validateurs écrits à la main dans les tests. Laquelle ?
6. **Lien officiel d'un scrutin** : je n'ai pas vérifié le modèle d'URL des pages officielles de scrutin ; il doit être confirmé avant d'écrire `source.lien_officiel`. Quel modèle ?
7. **ALG-14** (vérification indépendante sur fichiers bruts tirés au hasard, garantie 3) : voir ALG-05, question 4.

## Sources et constats
Cahier technique §3, §8, §10 ; `.agents/CONVENTIONS.md` (« Règles spécifiques export statique et déploiement ») ; `.agents/DECISIONS.md` (2026-10-22 « Site statique », décisions en suspens) ; `docs/methodology.md` (garanties 4 et 6, couleurs, ordre) ; fiches ALG-03, 05, 06, 08, 09, 10 ; mesures du 2026-11-03.

## Historique
- v1 (2026-11-03) : première rédaction.
