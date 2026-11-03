# ALG-01 — Lecture sécurisée de l'archive des scrutins
Statut : Brouillon    Version : 1    Date : 2026-10-25

## But
Lire l'archive des scrutins (fichier ZIP ou dossier déjà extrait) en ne laissant passer que des fichiers JSON de scrutin conformes, sans jamais écrire sur le disque, et produire une empreinte de l'archive ainsi qu'un rapport de lecture exact (ce qui a été lu, refusé, ignoré, et pourquoi).

## Périmètre
Inclus : ouverture, empreinte, filtrage des noms, limites de taille, décodage UTF-8, parsing JSON, cohérence identité nom/contenu, complétude de la numérotation.
Exclus : le téléchargement (statut HTTP, taille, fraîcheur, URL : fiche à créer, ALG-13), le sens des champs d'un scrutin (ALG-02 et ALG-04), les contrôles de totaux (ALG-05), l'écriture en base (ALG-07).

## Constats sur les données réelles (dossier `Scrutins.json/json`, 8 877 fichiers, vérifiés sur la totalité)
- 8 877 fichiers, tous nommés `VTANR5L17V<n>.json`, `n` de 1 à 8877 sans trou ni doublon.
- Taille : minimum 7 442 octets, médiane 18 700, 99ᵉ centile 46 708, maximum 61 251 ; total décompressé 180 527 979 octets (environ 172 Mio). L'archive ZIP compressée fait environ 27 Mo.
- Aucun BOM, aucun octet hors ASCII (les accents sont en séquences `\uXXXX`), tous les fichiers sont du JSON valide, racine unique `scrutin`, `scrutin.uid` identique au nom de fichier, `legislature` valant `"17"` partout.
- Le dossier extrait n'a pas de fichier hors motif ; une archive ZIP téléchargée peut contenir des entrées de dossier (`json/`).

## Entrées / Sorties
- Entrées : `source` (chemin d'un `.zip` ou d'un dossier contenant `json/`), `legislature` attendue (entier, 17 par défaut), paramètres de limites (ci-dessous).
- Sorties :
  1. flux d'entrées acceptées, triées par numéro de scrutin croissant : `{nom, numero, sha256_fichier, octets_bruts, document_json}` ;
  2. `RapportLecture` : `type_source` (`zip` | `dossier`), `empreinte_archive`, `type_empreinte` (`fichier` | `manifeste`), `entrees_vues`, `acceptees`, `ignorees` (entrées de dossier), `refusees` (liste `{nom, motif}`), `octets_lus`, `numero_min`, `numero_max`, `trous` (numéros absents entre min et max), `avertissements`, `statut` (`complet` | `partiel` | `echec`).

## Paramètres (valeurs proposées et justification)
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `MAX_ENTREES` | 50 000 | 5,6 × le nombre observé (8 877) : laisse de la marge à la législature, bloque une archive truquée contenant des millions d'entrées |
| `MAX_OCTETS_ENTREE` | 5 Mio (5 242 880) | 85 × le plus gros fichier observé (61 251) : tolère de gros scrutins, bloque une bombe de décompression |
| `MAX_OCTETS_TOTAL` | 1 Gio | 5,8 × le total observé (172 Mio) : marge pour la législature, borne la mémoire et le temps |
| `MAX_RATIO` | 100 | rapport taille décompressée / taille compressée d'une entrée ; le JSON texte compresse typiquement entre 5 et 20, 100 est un seuil clairement anormal. À mesurer sur le vrai ZIP avant de figer |
| `PROFONDEUR_JSON` | limite d'interpréteur par défaut | la profondeur observée est faible ; un dépassement est un refus d'entrée |

## Définitions
- Motif de nom admis : `json/VTANR5L<L>V<n>.json`, avec `L` = législature attendue (sans zéro initial) et `n` entier ≥ 1 sans zéro initial. Pour un dossier, le chemin relatif depuis la source est testé avec le même motif. Le motif est comparé exactement (sensible à la casse).
- Empreinte d'une entrée : SHA-256 des octets bruts du fichier.
- Empreinte de l'archive : pour un ZIP, SHA-256 des octets du fichier ZIP ; pour un dossier, SHA-256 du manifeste (une ligne `nom<TAB>sha256_fichier` par entrée acceptée ou refusée dont le contenu a pu être lu, triée par nom, terminée par `\n`).

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Si `source` n'existe pas, n'est pas lisible, ou n'est ni un fichier ni un dossier : `statut = echec`, arrêt | Rien à lire ; l'échec doit être explicite, jamais un import vide |
| 2 | Si `source` est un fichier : ouvrir **une seule fois** le descripteur et le conserver pour les étapes 3 et 4 | L'empreinte doit correspondre exactement aux octets lus ; deux ouvertures permettraient un remplacement de fichier entre les deux (TOCTOU) |
| 3 | ZIP : calculer le SHA-256 en lisant le descripteur par blocs de 1 Mio, puis revenir au début | Empreinte de provenance (comparaison avec l'import précédent, audit) sans charger 27 Mo en mémoire |
| 4 | ZIP : ouvrir l'archive depuis ce descripteur ; en cas d'archive invalide : `echec` | Un ZIP illisible ne produit aucune donnée partielle |
| 5 | ZIP : lister les entrées ; si leur nombre dépasse `MAX_ENTREES` : `echec` | Borne le travail avant tout traitement |
| 6 | ZIP : si deux entrées portent le même nom : `echec` | Un nom en double rend ambigu le contenu faisant foi ; c'est aussi une technique de dissimulation |
| 7 | ZIP : si la somme des tailles déclarées dépasse `MAX_OCTETS_TOTAL` : `echec` | Contrôle a priori de la bombe de décompression ; les tailles déclarées sont revérifiées à l'étape 13 |
| 8 | Dossier : parcourir `source/json` en profondeur, sans suivre de lien symbolique ; ignorer (avec compteur) les liens symboliques, refuser avec le motif `lien_symbolique` ceux dont le nom correspond au motif | Un lien pourrait pointer hors de la source ; on ne lit que des fichiers réels sous la racine |
| 9 | Pour chaque entrée, dans l'ordre alphabétique des noms : si le nom est celui d'un dossier (se termine par `/`) → compteur `ignorees`, suivant | Les ZIP contiennent des entrées de dossier sans contenu |
| 10 | Si le nom contient `\`, `\0`, un caractère de contrôle, commence par `/`, contient un segment `..` ou une lettre de lecteur : refuser (`nom_dangereux`) | Protection contre le zip-slip et les chemins Windows ; vérifiée avant même le motif pour que le motif ne soit jamais le seul rempart |
| 11 | Si le nom ne correspond pas exactement au motif admis : refuser (`hors_motif`) ; si le motif correspond mais `L` ≠ législature attendue : refuser (`legislature_inattendue`) | Liste blanche stricte : tout ce qui n'est pas explicitement attendu est rejeté et visible dans le rapport |
| 12 | ZIP : refuser si l'entrée est chiffrée (`flag_bits & 1`), si la méthode n'est ni stockée (0) ni deflate (8), ou si ses attributs indiquent un lien symbolique (`nom_non_supporte`) | Contenu illisible ou détourné ; les méthodes exotiques ne sont pas nécessaires |
| 13 | Lire l'entrée **au plus** `MAX_OCTETS_ENTREE + 1` octets, et jamais plus que la taille déclarée + 1 ; si plus de `MAX_OCTETS_ENTREE` octets sont lus, ou si la taille lue diffère de la taille déclarée, ou si le ratio dépasse `MAX_RATIO` : refuser (`taille`) | L'en-tête ZIP peut mentir ; la borne s'applique à ce qui est réellement décompressé |
| 14 | ZIP : toute erreur de lecture (CRC invalide, flux corrompu) → refuser l'entrée (`corrompue`), poursuivre avec les autres | Un fichier corrompu au milieu de l'archive doit produire un rapport exploitable sans bloquer le reste (cahier §5.3) |
| 15 | Cumuler les octets lus ; si le total dépasse `MAX_OCTETS_TOTAL` : `echec` | Le contrôle de l'étape 7 repose sur des tailles déclarées, celui-ci sur les tailles réelles |
| 16 | Décoder en UTF-8 strict (sans accepter de BOM) ; erreur → refuser (`encodage`) | Aucun BOM ni octet invalide observé ; toute déviation doit être visible |
| 17 | Parser le JSON en refusant les clés dupliquées, `NaN`, `Infinity` et les dépassements de profondeur ; erreur → refuser (`json_invalide`) | Une clé dupliquée écrase silencieusement une valeur : risque de chiffre faux |
| 18 | Vérifier que la racine est un objet qui ne contient que la clé `scrutin`, elle-même un objet ; sinon refuser (`structure`) | Forme observée sur 8 877 fichiers ; toute autre forme n'a pas été analysée |
| 19 | Vérifier que `scrutin.uid` est égal au nom du fichier sans extension, et que `scrutin.legislature` est la chaîne de la législature attendue ; sinon refuser (`identite`) | Empêche qu'un contenu soit rattaché à un autre scrutin par erreur ou par substitution |
| 20 | Calculer le SHA-256 des octets bruts de l'entrée et émettre l'entrée acceptée | Empreinte par scrutin pour `source_hash` et pour la détection de changement (ALG-07) |
| 21 | Après le parcours : ordonner les entrées acceptées par numéro croissant ; calculer `numero_min`, `numero_max` et les `trous` | Ordre déterministe, indépendant de l'ordre dans l'archive |
| 22 | Dossier : calculer l'empreinte de l'archive = SHA-256 du manifeste défini plus haut | Un dossier n'a pas d'octets propres ; le manifeste est reproductible |
| 23 | Si au moins une entrée au motif admis a été refusée (étapes 12 à 19) : `statut = partiel` ; si aucune entrée n'est acceptée : `echec` ; sinon `complet` | Un scrutin refusé est un scrutin manquant : jamais passé sous silence, et bloquant pour la publication (ALG-12) |
| 24 | Si des `trous` existent ou si `numero_min` ≠ 1 : ajouter un avertissement (le statut ne change pas) | La numérotation observée est continue ; une rupture est une alerte sans présumer de sa cause |
| 25 | Retourner le rapport ; il est journalisé en entier, sans tronquer la liste des refus | Traçabilité (garantie 4) et audit |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Chemin inexistant | `echec`, motif `source_introuvable` | étape 1 |
| ZIP tronqué ou invalide | `echec` | étape 4 |
| Entrée `../x.json` ou `/etc/x.json` ou `json\\a.json` | entrée refusée `nom_dangereux`, archive `partiel` si elle ressemble à un scrutin, sinon avertissement | étape 10 |
| Deux entrées `json/VTANR5L17V5.json` | `echec` | étape 6 |
| Entrée `json/` (dossier) | ignorée, comptée | étape 9 |
| Entrée `json/readme.txt` | refusée `hors_motif`, avertissement (n'empêche pas `complet`) | étape 11 ; pas de scrutin perdu |
| Entrée `json/VTANR5L16V1.json` | refusée `legislature_inattendue` | étape 11 |
| Entrée chiffrée | refusée | étape 12 |
| En-tête annonçant 1 Ko mais flux de 100 Mo | refusée `taille` après lecture de `MAX_OCTETS_ENTREE + 1` octets au plus | étape 13 |
| CRC invalide au milieu de l'archive | cette entrée refusée `corrompue`, les autres lues, statut `partiel` | étape 14 |
| Fichier avec BOM ou octets invalides | refusé `encodage` | étape 16 |
| Clé JSON dupliquée | refusé `json_invalide` | étape 17 |
| Racine différente de `{"scrutin": {...}}` | refusé `structure` | étape 18 |
| `uid` ≠ nom de fichier | refusé `identite` | étape 19 |
| Numéros 1 à 8877 sauf 4000 | accepté, `trous = [4000]`, avertissement | étape 24 |
| Archive vide | `echec` | étape 23 |
| Dossier contenant un lien symbolique vers un fichier hors source | lien ignoré / refusé, jamais lu | étape 8 |

## Exemples chiffrés (à reproduire en test)
- Dossier réel `Scrutins.json` : `entrees_vues = 8877`, `acceptees = 8877`, `refusees = []`, `numero_min = 1`, `numero_max = 8877`, `trous = []`, `octets_lus = 180 527 979`, `statut = complet`, `type_empreinte = manifeste`.
- ZIP construit en test avec 3 scrutins valides, un dossier `json/` et un fichier `json/note.txt` : `entrees_vues = 5`, `acceptees = 3`, `ignorees = 1`, `refusees = [json/note.txt: hors_motif]`, `statut = complet`.
- Même ZIP avec une entrée `json/VTANR5L17V2.json` dont le CRC est altéré : `acceptees = 2`, `refusees = [..V2.json: corrompue]`, `statut = partiel`.

## Invariants
- `acceptees + refusees + ignorees = entrees_vues` (hors liens symboliques ignorés, comptés à part).
- Aucun nom accepté n'est dupliqué ; les entrées émises sont triées par numéro croissant.
- `octets_lus ≤ MAX_OCTETS_TOTAL` et aucune entrée acceptée n'a plus de `MAX_OCTETS_ENTREE` octets.
- Aucune écriture sur le disque, aucun accès réseau pendant la lecture.
- Deux lectures de la même source produisent la même empreinte et le même flux (déterminisme).

## Questions à trancher avant de coder
1. **Valeurs des limites** : `MAX_RATIO` surtout, à calibrer sur le vrai ZIP. OK pour les autres ?
2. **Entrée refusée = publication bloquée ?** Cette fiche le prévoit (`partiel`, voir ALG-12). Alternative moins stricte : publier avec avertissement. Je recommande la rigueur.
3. **Trou de numérotation** : simple avertissement ici. Doit-il bloquer aussi ? Il faut des données de suppression avant de décider.
4. **BOM** : refusé aujourd'hui, car jamais observé. Souhaites-tu plutôt l'accepter et le signaler ?
5. **Téléchargement** : on crée la fiche ALG-13 (URL, statut HTTP, taille minimale et maximale, fraîcheur, empreinte comparée à l'import précédent). Quelle est l'URL officielle de l'archive ?

## Sources et constats
`docs/analyse-donnees-sources.md`, cahier technique §5.2 (règles 1, 2, 8, 10) et §5.3 (fichier corrompu au milieu de l'archive), `docs/methodology.md` (garanties 2 et 4).

## Historique
- v1 (2026-10-25) : première rédaction.
