# Analyse des données sources (scrutins)

Constats vérifiés le 2026-10-22 sur le dossier `Scrutins.json/json/` (ignoré par Git). Méthode : lecture détaillée de `VTANR5L17V1017.json` et contrôles automatiques sur un échantillon aléatoire de 600 fichiers (graine 7) sur 8 877. Les chiffres ci-dessous valent pour l'échantillon ; l'ETL devra les revérifier sur l'ensemble.

## Fichiers

- 8 877 fichiers `VTANR5L17V<numéro>.json`, numéros de 1 à 8877, sans trou apparent. Dates des scrutins de l'échantillon : 2024-10-23 à 2026-10-16.
- Racine unique `scrutin`. Même jeu de clés dans tous les fichiers de l'échantillon (dont `@xmlns`, `@xmlns:xsi` à ignorer).
- JSON valide en UTF-8 avec séquences `\uXXXX` ; aucun problème d'encodage dans les fichiers (les caractères « � » vus dans certains terminaux Windows ne sont qu'un défaut d'affichage).

## Champs

- Identité : `uid`, `numero` (chaîne), `legislature` (chaîne), `dateScrutin` (AAAA-MM-JJ), `sessionRef`, `seanceRef`, `organeRef`, `quantiemeJourSeance`, `lieuVote`.
- `typeVote` : `codeTypeVote` vaut `SPO` (scrutin public ordinaire) dans 100 % de l'échantillon ; `typeMajorite` : majorité absolue des suffrages exprimés (598/600) ou requise pour une motion de censure (2/600). Ce dernier champ aide à repérer les motions de censure.
- `sort` : `code` `adopté` / `rejeté` (avec accent). Pas de code stable en ASCII : à normaliser (`adopte`, `rejete`).
- `titre` et `objet.libelle` : même texte dans l'exemple lu. `objet.dossierLegislatif` est `null` pour 393/600 : le rattachement à un texte n'est donc pas toujours disponible.
- `demandeur.texte` : texte libre (« Présidente du groupe … ») ; `demandeur.referenceLegislative` souvent `null`.
- `modePublicationDesVotes` : `DecompteNominatif` pour tout l'échantillon.

## Totaux

- `syntheseVote` : nombres stockés en chaînes. `suffragesExprimes` = pour + contre (les abstentions n'y sont pas comptées) ; `nombreVotants` = pour + contre + abstentions. Vérifié sur 600/600.
- Les non-votants (`decompte.nonVotants`, `nonVotantsVolontaires`) ne sont pas dans `nombreVotants`.
- Somme des `decompteVoix.pour` des groupes = total `pour` : 600/600. Nombre de votes nominatifs listés = `decompteVoix` : 0 écart sur 600 scrutins et 12 groupes chacun.
- Il y a 12 groupes dans chaque scrutin de l'échantillon, sous `ventilationVotes.organe.groupes.groupe` (liste ; l'ETL doit tout de même gérer un objet unique, cf. cahier §5.3).

## Variantes de structure à normaliser

Dans `decompteNominatif` de chaque groupe, les clés `pours`, `contres`, `abstentions`, `nonVotants` valent :

| Forme | Fréquence (échantillon, tous types confondus) |
|---|---|
| `null` (aucun votant) | très fréquent (ex. `abstentions` : 2 116 groupes-scrutins) |
| `{"votant": {…}}` (un seul votant, **objet**) | fréquent (ex. `pours` : 186) |
| `{"votant": [ {…}, … ]}` (**liste**) | fréquent (ex. `contres` : 1 198) |

Chaque `votant` contient `acteurRef` (`PA…`), `mandatRef` (`PM…`), `parDelegation` (`"true"`/`"false"` en chaîne, vrai pour environ 15 % des votes), `numPlace`, et parfois `causePositionVote`.

## Points d'attention pour la neutralité et l'exactitude

1. **`positionMajoritaire` de la source n'est pas fiable.** Elle diffère de la position la plus fréquente du groupe dans 226 cas sur 7 100 groupes-scrutins (ex. `VTANR5L17V2066`, groupe `PO845407` : 12 pour, 2 contre, source = « contre ») et vaut « pour » pour 630 groupes qui n'ont exprimé aucun vote. **Décision : calculer la position majoritaire dans l'ETL à partir des décomptes**, et conserver la valeur source dans `position_majoritaire_source` pour traçabilité. En cas d'égalité (139 cas), aucune position majoritaire.
2. **`causePositionVote`** (`MG` membre du gouvernement, `PAN` président de l'Assemblée, `PSE` président de séance) explique des non-votants : à afficher comme tel, pas comme une absence ordinaire. Valeurs relevées dans l'échantillon ; liste à confirmer sur l'ensemble.
3. **`miseAuPoint`** : corrections de position déclarées après le vote, non vide pour 99/600 scrutins. Il faut décider si l'on affiche la position initiale, la position rectifiée, ou les deux. À trancher avant l'import (voir `.agents/DECISIONS.md`).
4. **Votes par délégation** : `parDelegation` est une information à conserver et à afficher (le député ne vote pas lui-même).
5. **Référentiels absents** : les identifiants `PO…`, `PA…`, `PM…` n'ont aucun libellé dans ces fichiers.
6. **Aucun scrutin de l'échantillon n'est d'un autre type que `SPO`** : la classification en catégories (article, amendement, texte, motion) ne peut s'appuyer que sur `titre`, `objet`, `typeMajorite` et `dossierLegislatif` ; elle sera approximative, d'où l'indicateur « à vérifier ».
