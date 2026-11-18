# ALG-14 — Vérification indépendante sur fichiers bruts tirés au hasard
Statut : Validé    Version : 2    Date : 2026-11-18

## But
Contrôler, sur un échantillon de scrutins tiré de façon reproductible, que chaque chiffre du fichier publié `scrutins/<id>.json` est identique à celui du fichier source officiel, **sans réutiliser le code du pipeline** (garantie 3). Un défaut commun à ALG-02, 04 ou 11 qui passerait les contrôles de cohérence interne d'ALG-05 doit être détecté ici.

## Périmètre
Inclus : tirage de l'échantillon, relecture des fichiers bruts par un lecteur indépendant, comparaison champ par champ, rapport.
Exclus : lecture sécurisée de l'archive (déjà faite par ALG-01 ; ce script réutilise seulement le ZIP, jamais les fonctions du pipeline), cohérence interne des chiffres (ALG-05), décision de publier (ALG-12, règle G06).

## Principe d'indépendance
- Script distinct (`scripts/verifier_echantillon.py`), bibliothèque standard seule (`zipfile`, `json`, `hashlib`, `random`), **aucun import du paquet `etl`**.
- Il relit le **ZIP téléchargé** (celui dont l'empreinte est dans `provenance.json`) et les **fichiers exportés** (`dist-data/data/v1/scrutins/<id>.json`), et ne partage avec le pipeline que les fiches (les noms de champs de la source et du contrat d'export).
- Les valeurs sont extraites par une implémentation volontairement simple et séparée ; une divergence est un défaut d'un des deux côtés, à examiner, jamais corrigée automatiquement.

## Entrées / Sorties
- Entrées : `archive_zip` (chemin), `repertoire_export`, `graine` (par défaut : SHA-256 de l'archive, donc reproductible), `taille_echantillon` (voir paramètres), `ids_obligatoires` (scrutins imposés).
- Sortie : `RapportVerification` = `{graine, tires (liste d'identifiants), nb_verifies, nb_champs_compares, ecarts (liste {scrutin_id, champ, attendu_source, obtenu_export}), statut}` avec `statut` ∈ `ok` | `echec`. Écrit en `verification.json`.

## Paramètres (propositions, à recaler)
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `TAILLE_ECHANTILLON` | 200 | environ 2 % des 9 895 scrutins, quelques secondes de calcul ; borne le temps de CI |
| `IDS_OBLIGATOIRES` | `VTANR5L17V1` (écart connu d'ALG-05), `VTANR5L17V489` (groupes `PO0`), `VTANR5L17V1017` (non-votant avec cause), `VTANR5L17V1302` (un groupe `PO0`) | cas particuliers déjà identifiés, toujours testés |
| Scrutins récents | les 20 numéros les plus élevés | les nouveautés sont le plus susceptibles d'une dérive de format |

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi.

```text
graine  = SHA256(octets de l'archive) si non fournie                         [1]
ids     = ids_obligatoires ∪ 20 plus récents ∪ tirage(graine, reste, N)       [2]

pour chaque id de ids (trié):
    brut    = JSON du fichier source (ZIP)                                   [3]
    publie  = JSON du fichier exporté scrutins/<id>.json
    si publie absent: écart "fichier_absent" ; continuer                     [4]
    pour chaque champ de la liste des champs vérifiés:                       [5]
        attendu = extraire_brut(brut, champ)      # extraction indépendante
        obtenu  = lire_export(publie, champ)
        si attendu ≠ obtenu: écart {id, champ, attendu, obtenu}

statut = "echec" si au moins un écart, sinon "ok"                            [6]
écrire verification.json ; ne jamais corriger ni masquer un écart            [7]
```

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Graine = SHA-256 de l'archive (ou valeur fournie) | Tirage reproductible : même archive, même échantillon ; un échec se rejoue |
| 2 | Échantillon = scrutins obligatoires + 20 plus récents + tirage pseudo-aléatoire (`random.Random(graine)`) parmi les autres jusqu'à `TAILLE_ECHANTILLON` | Couvre les cas connus, les nouveautés et une part représentative |
| 3 | Lire le fichier brut dans le ZIP avec `zipfile` et `json` seuls | Aucun code du pipeline |
| 4 | Fichier exporté absent : écart `fichier_absent` | Un scrutin de l'archive doit être publié |
| 5 | Comparer, pour chaque scrutin tiré : date, titre, type de vote, résultat (`sort.code`), totaux (pour, contre, abstentions, non-votants, exprimés, votants), pour chaque groupe (**par rang**, pas par identifiant) : effectif, compteurs, et le **nombre de votants par position**, puis l'ensemble des couples (député, position, délégation, cause) | Toute valeur publiée doit se retrouver dans la source ; la comparaison par rang couvre les groupes `PO0` |
| 6 | `echec` au moindre écart ; aucun seuil de tolérance | Un chiffre parlementaire faux ne se tolère pas (garantie 3) |
| 7 | Écrire `verification.json` ; ne jamais modifier l'export ni les données | « Jamais corrigé en silence » |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Export identique à la source | `ok`, `nb_champs_compares` > 0 | cas nominal |
| Un `pour` modifié dans l'export | `echec`, écart sur ce champ | détection de la dérive |
| Scrutin n° 1 (21 non-votants nominatifs, 10 au total) | `ok` : l'export reproduit la source telle quelle, écart de la source inclus | on vérifie la fidélité, pas la cohérence (c'est ALG-05) |
| Fichier exporté absent | écart `fichier_absent`, `echec` | étape 4 |
| Archive ou export introuvable | erreur explicite, `echec`, jamais « ok » | pas de contrôle vide |
| `TAILLE_ECHANTILLON` supérieure au nombre de scrutins | tous les scrutins sont vérifiés | pas d'erreur |
| Deux exécutions, même archive | même échantillon | graine déterministe |

## Exemples chiffrés (à reproduire en test)
Sur les six fixtures réelles et leur export : `nb_verifies = 6`, `ecarts = []`. Même export dont un `pour` de groupe est modifié de 1 : exactement un écart `{champ: totaux/groupe pour}` et `statut = echec`. Archive complète : 200 scrutins tirés plus les obligatoires, tous `ok`.

## Invariants vérifiés
- Le script n'importe aucun module du paquet `etl`.
- Même archive et même graine : même échantillon et même rapport.
- Aucun écart n'est corrigé, masqué ni toléré.
- `nb_verifies` = nombre de scrutins de l'échantillon réellement comparés.

## Décisions (2026-11-18) : questions tranchées par le responsable du projet
1. **Échantillon** : 200 scrutins, dont les 4 obligatoires (n° 1, 489, 1017, 1302), les 20 plus récents et un tirage reproductible du reste (graine = SHA-256 de l'archive) ; à recaler selon la durée mesurée en CI. Si la taille demandée dépasse le nombre de scrutins, tous sont vérifiés.
2. **Champs comparés** (étape 5, fixés avec le schéma d'export d'ALG-11) : `id`, `numero`, `date`, `titre`, `type_vote` (code et libellé), `resultat` (`adopté` → `adopte`, `rejeté` → `rejete`), `source.sha256` (SHA-256 des octets du fichier brut), `source.archive_sha256` (SHA-256 du ZIP, quand l'archive est un fichier), `source.lien_officiel`, les six totaux, pour chaque groupe **par rang** (jamais par identifiant) `groupe_id` (`PO0` → `null`), `ventilation_disponible`, `membres`, `pour`, `contre`, `abstentions`, `non_votants`, le **nombre de votants par position**, et chaque vote `(député, rang du groupe, position, délégation, cause)`.
3. **Contrôle global** en plus de l'échantillon : mêmes identifiants de scrutin dans l'archive et dans l'export (fichier absent ou en trop) et `meta.nombre_scrutins` égal au nombre de scrutins de l'archive.
4. **Non couvert** : les mises au point et les dysfonctionnements, la catégorie, la position majoritaire et les corrections (valeurs dérivées par ALG-03, 06 et 08, qui ne sont pas des chiffres de la source), `groupes/`, `deputes.json`, `stats.json` (contrôlés par ALG-05, ALG-10 et les tests).
5. **Dossier extrait** accepté comme archive (usage local et tests) ; la graine est alors dérivée des identifiants.

## Sources et constats
`docs/methodology.md` (garantie 3), `docs/algorithmes/ALG-05-reconciliation.md` (question 4), `docs/algorithmes/ALG-11-export-statique.md` et `ALG-12-garde-fou-deploiement.md` (règle G06), `.agents/CONVENTIONS.md` (bibliothèque standard en priorité).

## Historique
- v1 (2026-11-18) : première rédaction, créée sur décision du responsable du projet.
- v2 (2026-11-18) : questions tranchées, champs comparés figés, contrôle global ajouté ; statut « Validé » ; script `scripts/verifier_echantillon.py` et tests écrits le même jour.
