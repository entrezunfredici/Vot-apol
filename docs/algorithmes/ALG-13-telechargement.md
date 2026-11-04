# ALG-13 — Téléchargement de l'archive (URL, statut HTTP, taille, fraîcheur, comparaison d'empreinte)
Statut : Brouillon    Version : 1    Date : 2026-11-03

## But
Récupérer l'archive officielle des scrutins en s'assurant qu'on a bien reçu **une archive complète, depuis la source prévue**, en conserver la provenance, et dire si elle diffère de ce qui est déjà publié, avant de lui appliquer ALG-01. Un téléchargement douteux ne produit aucune archive.

## Périmètre
Inclus : validation de l'adresse, requête, redirections, nouvelles tentatives, bornes de taille, vérification de complétude et de format minimal, fraîcheur annoncée par la source, empreinte, comparaison avec la version publiée, enregistrement de la provenance.
Exclus : contrôle du contenu du ZIP (ALG-01), décision de déployer (ALG-12), téléchargement des référentiels de noms (même fonction, autre adresse, voir ALG-09), usage hors ligne (l'option `--zip` de l'ETL ne passe pas par cette fiche et n'ouvre aucune connexion, cahier §5.2 règle 9).

## Constats
- L'archive reçue pour le projet fait environ 27 Mo (8 877 entrées) ; elle a été fournie par le porteur du projet, **l'adresse officielle de téléchargement n'est pas connue ni vérifiée** (question 1).
- La source ne fournit, à ma connaissance, ni empreinte publiée ni signature : l'intégrité se limite à la taille annoncée, à la vérification du format et au contrôle de cohérence d'ALG-01 et ALG-05. Cette hypothèse reste à vérifier sur la page de la source.
- Une exécution par jour suffit (cahier §10) : l'archive n'est demandée qu'une fois par exécution, sans requête conditionnelle (la comparaison par empreinte fait foi ; 27 Mo par jour ne justifie pas la complexité d'un en-tête `ETag` dont la fiabilité n'est pas établie).

## Entrées / Sorties
- Entrées : `url` (variable de configuration, jamais en dur), `hotes_autorises` (liste), `url_meta_publie` (adresse du `meta.json` de la version publiée, variable de configuration, sur un hôte autorisé ; l'étape 2 en tire `empreinte_publiee`, qui vaut `null` seulement si la version publiée n'existe pas), `repertoire_archives`, `telechargee_le` (horodatage UTC fourni par l'appelant), paramètres de limites.
- Sorties : fichier `repertoire_archives/<sha256>.zip` ; `provenance.json` ; `RapportTelechargement` = `{statut, url_demandee, url_finale, code_http, tentatives, octets, sha256, entetes (ETag, Last-Modified, Content-Length, Content-Type, Date), avertissements, cause_echec}` avec `statut` ∈ `nouvelle` | `inchangee` | `echec`.

## Paramètres (propositions, à recaler)
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `MAX_OCTETS_TELECHARGEMENT` | 200 Mio | Environ 7 fois la taille observée (27 Mo) ; borne le disque et la durée en cas de réponse anormale |
| `MIN_OCTETS_TELECHARGEMENT` | 10 Mio | Environ 37 % de la taille observée ; une réponse bien plus petite est une page d'erreur ou une archive tronquée |
| `MAX_REDIRECTIONS` | 5 | Au-delà : boucle ou configuration anormale |
| `DELAI_CONNEXION` / `DELAI_INACTIVITE` | 30 s / 60 s | Un serveur qui ne répond plus ne doit pas bloquer l'exécution |
| `DELAI_TOTAL` | 15 min | Environ 30 fois la durée attendue pour 27 Mo à débit modeste |
| `MAX_TENTATIVES` | 3, attentes de 10 s puis 60 s | Absorber une panne brève sans insister auprès d'un service public |
| `FRAICHEUR_JOURS` | 90 | Avertissement seulement : le Parlement suspend ses travaux jusqu'à plusieurs semaines |

## Algorithme logique (vue d'ensemble)
Lecture en langage naturel ; `[k]` renvoie aux étapes du tableau suivant, qui fait foi. Un téléchargement douteux ne laisse aucune archive.

```text
# Notations
url      = Entrée[url]                      # configuration, jamais en dur
publiee  = empreinte lue dans meta.json en ligne (null si 404)                    [2]

si url n'est pas en https, contient un mot de passe, ou son hôte ∉ hotes_autorises:
    statut = "echec" (config_invalide) ; arrêt                                    [1]
si lecture de meta.json échoue autrement qu'en 404:
    statut = "echec" (publie_inconnu) ; arrêt                                     [2]

pour tentative = 1 … MAX_TENTATIVES (3):
    réponse = GET(url, sans cookie ni jeton, TLS vérifié)                         [3]
    suivre au plus 5 redirections, toutes en https et sur un hôte autorisé        [4]
        sinon: echec (redirection_refusee)
    si code = 200:                       sortir de la boucle
    sinon si code = 429, 5xx ou délai dépassé:  attendre 10 s puis 60 s, recommencer   [5]
    sinon:                               echec ; arrêt   # 404, 4xx : pas d'insistance

octets = 0 ; h = SHA256 vide
pour chaque bloc de 1 Mio du flux:                                                [6]
    octets += |bloc| ; h.mettre_a_jour(bloc) ; écrire dans le temporaire
    si octets > 200 Mio: supprimer, echec (trop_gros) ; arrêt

si Content-Length présent et ≠ octets:          echec (incomplet)                 [7]
si octets < 10 Mio:                              echec (trop_petit)               [8]
si les 4 premiers octets ≠ "PK\\x03\\x04":        echec (pas_un_zip)               [9]
si Last-Modified absent: avertissement "fraicheur_inconnue"
sinon si âge > 90 jours: avertissement "archive_ancienne"                         [10]

sha256 = h.résultat
si fichier(sha256 + ".zip") existe: supprimer le temporaire
sinon: renommer le temporaire en sha256 + ".zip"                                  [11]

si publiee = sha256:  statut = "inchangee"
sinon:                statut = "nouvelle"                                         [12]
écrire provenance.json (url finale, code, en-têtes, sha256, octets, date)         [13]

en cas d'échec à une étape quelconque: supprimer le temporaire, aucune archive conservée   [14]
```

Propriétés : l'empreinte est celle des octets reçus ; le nom du fichier conservé est son SHA-256 (deux téléchargements identiques = un seul fichier) ; la comparaison se fait avec la version **publiée**, jamais avec le dernier import ; aucune requête hors des hôtes autorisés. Exemples : 503 puis 200 → `nouvelle`, `tentatives = 2` ; page HTML de 5 Ko avec code 200 → `trop_petit`.

## Algorithme
| # | Étape | Justification |
|---|-------|---------------|
| 1 | Lire la configuration ; refuser (`config_invalide`) si l'adresse n'est pas en `https`, contient un identifiant ou un mot de passe, ou si son hôte n'est pas dans `hotes_autorises` | La source est fixée à l'avance ; aucune adresse ne vient d'une donnée téléchargée |
| 2 | Lire `meta.json` de la version publiée pour obtenir `empreinte_publiee` ; réponse 404 → `null` (aucune publication) ; autre échec → `echec` (`publie_inconnu`) | Sans point de comparaison, on ne peut pas décider (ALG-12) ; on n'interprète pas une panne comme « première publication » |
| 3 | Demander l'archive : méthode GET, en-têtes `User-Agent` identifiant le projet, `Accept-Encoding: identity`, vérification du certificat TLS activée, aucun jeton ni cookie | Les octets reçus sont les octets hachés ; aucune identification inutile ; pas d'authentification à protéger |
| 4 | Suivre au plus `MAX_REDIRECTIONS` redirections ; chacune doit rester en `https` et sur un hôte autorisé ; sinon `echec` (`redirection_refusee`) | Une redirection ne doit pas faire sortir de la source prévue |
| 5 | Code HTTP : `200` → continuer ; `429`, `5xx`, délai dépassé, connexion coupée → nouvelle tentative (jusqu'à `MAX_TENTATIVES`, en respectant `Retry-After` limité à 120 s) ; tout autre code (dont `3xx` non géré, `4xx`) → `echec` sans nouvelle tentative | Une panne transitoire se rattrape, une erreur de configuration ne se rattrape pas en insistant |
| 6 | Écrire le flux dans un fichier temporaire du même volume que `repertoire_archives`, par blocs de 1 Mio, en calculant le SHA-256 au fil de l'eau ; si le nombre d'octets dépasse `MAX_OCTETS_TELECHARGEMENT` : interrompre, supprimer, `echec` (`trop_gros`) | Mémoire constante ; l'empreinte est celle des octets reçus ; la borne s'applique à ce qui est réellement reçu et non à l'en-tête |
| 7 | À la fin du flux : si `Content-Length` est présent et diffère du nombre d'octets reçus : `echec` (`incomplet`) | Détecte une coupure |
| 8 | Si le nombre d'octets est inférieur à `MIN_OCTETS_TELECHARGEMENT` : `echec` (`trop_petit`) | Écarte une page d'erreur servie avec un code 200 ou une archive tronquée |
| 9 | Vérifier que les quatre premiers octets sont ceux d'un ZIP (`PK\x03\x04`) ; sinon `echec` (`pas_un_zip`) | Contrôle de format minimal avant ALG-01 qui contrôlera tout le reste |
| 10 | Lire `Last-Modified` : absent → avertissement `fraicheur_inconnue` ; plus ancien que `FRAICHEUR_JOURS` avant `telechargee_le` → avertissement `archive_ancienne` | « Vérifier son actualité » (cahier §10) ; un avertissement car une période d'interruption des travaux est normale |
| 11 | Calculer le chemin `repertoire_archives/<sha256>.zip` ; si ce fichier existe déjà, supprimer le temporaire ; sinon renommer le temporaire | Archive adressée par son contenu : jamais d'écrasement, réimport identique sans doublon |
| 12 | Si `empreinte_publiee` est égale au SHA-256 : `statut = inchangee` ; sinon `nouvelle` | Cahier §10 : ne pas importer si inchangée ; comparée à la version **publiée**, jamais au dernier import, pour retenter après un déploiement raté (ALG-12, étape 1) |
| 13 | Écrire `provenance.json` (url demandée et finale, code, en-têtes retenus, empreinte, octets, `telechargee_le`, nombre de tentatives) | Provenance exigée par la garantie 4 et le cahier §5.2 règle 10 ; l'URL finale sert de `source_url` (ALG-04) |
| 14 | Toute étape en échec : supprimer le fichier temporaire, ne conserver aucune archive partielle, retourner `echec` avec sa cause ; ne jamais laisser une exception non rapportée | Un échec de téléchargement ne casse pas la version publiée (cahier §10, point 6) |

## Cas limites et erreurs
| Cas | Résultat attendu | Pourquoi |
|-----|------------------|----------|
| Adresse en `http` | `echec` `config_invalide` | étape 1 |
| Hôte non autorisé (configuration ou redirection) | `echec` | étapes 1, 4 |
| Réponse 404 sur l'archive | `echec`, sans nouvelle tentative | étape 5 |
| Réponses 503 puis 200 | `nouvelle`, `tentatives = 2` | étape 5 |
| Trois réponses 503 | `echec` après 3 tentatives | étape 5 |
| Coupure à mi-flux | `echec` `incomplet`, aucun fichier conservé | étapes 7, 14 |
| Page HTML d'erreur avec code 200, 5 Ko | `echec` `trop_petit` | étape 8 |
| 15 Mio de HTML | `echec` `pas_un_zip` | étape 9 |
| Flux de 300 Mio | interrompu à 200 Mio, `echec` `trop_gros` | étape 6 |
| Redirection vers un autre hôte | `echec` `redirection_refusee` | étape 4 |
| Même archive que la version publiée | `inchangee`, fichier conservé sous son empreinte | étape 12 |
| Version publiée inexistante (404 sur `meta.json`) | `nouvelle`, `empreinte_publiee = null` | étape 2 |
| Site publié injoignable (autre erreur sur `meta.json`) | `echec` `publie_inconnu` | étape 2 |
| `Last-Modified` absent | avertissement | étape 10 |
| `Last-Modified` plus vieux que 90 jours | avertissement, la décision reste à ALG-12 | étape 10 |

## Exemples chiffrés (à reproduire en test)
Les tests utilisent un **serveur HTTP local** de test (aucun accès au réseau public) servant de petites archives ZIP. Le test est le seul contexte où une adresse `http` sur l'interface locale est admise, par un paramètre explicite désactivé par défaut. Les seuils de taille sont abaissés en test. Cas à couvrir : 200 correct, 404, 503 puis 200, coupure, HTML avec code 200, redirection hors source, flux trop gros, réponse lente (délai d'inactivité), même archive deux fois, archive différente. Aucune valeur parlementaire n'est produite par ces tests.

## Invariants vérifiés
- Aucun fichier d'archive n'existe à l'issue d'un `echec`.
- Le SHA-256 enregistré est celui des octets du fichier conservé.
- Le nom du fichier conservé est son SHA-256 ; deux téléchargements identiques ne créent qu'un fichier.
- Aucune requête n'est faite hors de `hotes_autorises` ; aucun certificat n'est ignoré ; aucun secret n'est envoyé ni journalisé.
- La fonction n'est pas appelée en mode hors ligne.

## Questions à trancher avant de coder
1. **Adresse officielle** de l'archive des scrutins et hôtes autorisés : à fournir ou à confirmer (je n'ai pas vérifié l'adresse de la source) ; indiquer aussi si la source publie une empreinte ou un horodatage.
2. **Comparaison avec la version publiée** : elle suppose que `meta.json` est lisible en ligne. Au premier déploiement, aucune version n'existe (`null`). D'accord ?
3. **Seuils de taille et de fraîcheur** : propositions raisonnées à partir d'une seule archive ; à recaler après quelques téléchargements réels.
4. **Conservation des archives** : `data/archives/` est ignoré par Git. En CI, conserver l'archive comme artefact d'exécution pendant combien de jours (provenance et audit, cahier §5.2 règle 10) ?
5. **Référentiels de noms** (ALG-09) : même fonction avec une adresse et des seuils propres ? Les seuils de taille sont à définir à partir des vrais fichiers.

## Sources et constats
Cahier technique §5.2 (règles 9 et 10), §10 (points 1, 2 et 6) ; `.agents/DECISIONS.md` (2026-10-22 « Source : open data officiel, pas de scraping ») ; `docs/methodology.md` (garantie 4) ; `.agents/CONVENTIONS.md` (bibliothèque standard en priorité) ; fiches ALG-01, 04, 12.

## Historique
- v1 (2026-11-03) : première rédaction.
