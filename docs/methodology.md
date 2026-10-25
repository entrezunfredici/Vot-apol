# Méthodologie

Document en construction. Il définit les calculs affichés par Voteapol. Tout chiffre présenté sur le site doit pouvoir être retrouvé par ces définitions et vérifié dans le scrutin officiel.

## Position majoritaire d'un groupe sur un scrutin

**Entrées** (pour un groupe `g` et un scrutin `s`, lues dans `decompteVoix`, identiques aux listes nominatives sur l'échantillon étudié) :

- `P` = nombre de membres du groupe ayant voté **pour**
- `C` = nombre ayant voté **contre**
- `A` = nombre s'étant **abstenus**
- `E = P + C + A` : positions exprimées
- `N` = non-votants, **exclus de E** (une absence n'est pas une abstention)
- `effectif` = `nombreMembresGroupe`

**Formule**

```text
m = max(P, C, A)

si E = 0                              → pas de position majoritaire (aucun vote exprimé)
si plusieurs positions valent m       → pas de position majoritaire (égalité)
sinon                                 → position majoritaire = la position qui vaut m
```

C'est une majorité **relative** (pluralité) : la position la plus fréquente parmi les positions exprimées.

**Valeurs dérivées, toutes calculées en entiers**

- `part_exprimes = m / E` (arrondi à l'affichage uniquement, jamais stocké arrondi)
- `majorite_absolue = (2 × m > E)` : vrai si la position réunit plus de la moitié des exprimés
- `participation = E / effectif`

**Affichage obligatoire** : la position n'est jamais montrée seule, mais avec ses effectifs, par exemple « Pour : 12 sur 14 exprimés (effectif du groupe : 94) ». Si `majorite_absolue` est faux, le libellé précise « majorité relative ». Si le groupe n'a pas de position majoritaire, le texte « Pas de position majoritaire » s'affiche avec la raison (égalité ou aucun vote exprimé).

**Ce qui est volontairement exclu**

- La valeur `positionMajoritaire` de la source n'est pas utilisée pour l'affichage : elle contredit les décomptes dans 226 cas sur environ 7 100 groupes-scrutins de l'échantillon et vaut « pour » pour des groupes sans aucun vote. Elle est conservée en base dans `position_majoritaire_source` à titre d'audit. Aucune explication de cet écart n'a été trouvée (elle ne correspond ni à la position dominante, ni à l'issue du scrutin, ni à une règle simple pour/contre).
- Les non-votants et leur cause (`MG`, `PAN`, `PSE`) ne sont pas traités comme des positions.
- Aucune interprétation : « contre » signifie « a voté contre sur ce scrutin », pas une opposition au thème du texte.

## Indicateur : part de la position majoritaire

Pour un groupe et un scrutin, il s'agit de `m sur E` : le nombre de membres ayant voté comme la position majoritaire du groupe, sur les positions exprimées. Il n'est défini que si une position majoritaire existe. Ce n'est pas un score : il n'y a pas de seuil ni de qualificatif, et les groupes ne sont jamais classés selon cet indicateur.

Sur plusieurs scrutins, on affiche la répartition brute (par exemple : « sur 120 scrutins, 80 avec au moins 90 % des exprimés sur la position majoritaire »), jamais une moyenne unique.

## Présence au scrutin

`E` membres sur `effectif` : membres du groupe ayant exprimé une position. Les non-votants sont indiqués à part (`N`), avec leur cause lorsqu'elle est connue.

## Cas limites à tester

| Cas | Résultat attendu |
|---|---|
| P=12, C=2, A=0 | Pour, 12 sur 14, majorité absolue |
| P=5, C=6, A=49 | Abstention, 49 sur 60, majorité absolue |
| P=6, C=6, A=1 | Pas de position majoritaire (égalité) |
| P=0, C=0, A=0 | Pas de position majoritaire (aucun vote exprimé) |
| P=3, C=2, A=2 | Pour, 3 sur 7, majorité relative |

## Mises au point (rectifications de position après le vote)

Un député peut signaler après coup qu'il souhaitait voter autrement. Ces signalements figurent dans `miseAuPoint` (non vide dans 99 scrutins sur 600). Constats sur l'échantillon :

- Les décomptes officiels (`syntheseVote`, `decompteVoix`, `decompteNominatif`) **ne sont pas modifiés** par les mises au point : ils restent la position initialement enregistrée.
- Une mise au point liste des députés par position rectifiée (`pours`, `contres`, `abstentions`, `nonVotants`), sans indiquer le groupe ni la position initiale. Le groupe et la position initiale se retrouvent dans le décompte nominatif ; 58 des 276 rectifications de l'échantillon n'y figurent pas (député introuvable).
- Elles changent rarement le résultat : la position majoritaire d'un groupe est modifiée dans 7 cas sur 7 189 groupes-scrutins.

**Règle d'affichage**

1. Les chiffres principaux restent les chiffres officiels publiés, calculés comme ci-dessus.
2. Quand un scrutin comporte des mises au point, la fiche affiche un encart distinct : « N députés ont signalé une rectification de leur vote » avec la liste (position initiale → position déclarée).
3. Si la prise en compte des mises au point **change** la position majoritaire d'un groupe (ou la fait disparaître), la ligne du groupe le signale : « Une mise au point modifie ce résultat », avec les effectifs corrigés.
4. Les rectifications dont le député est introuvable dans le décompte sont listées à part, sans être rattachées à un groupe.
5. Aucun effectif corrigé n'est présenté comme le résultat officiel.

## Garanties d'intégrité et de neutralité

Principe : Voteapol rapporte des faits officiels, sans les interpréter. Une erreur ou une mise en forme orientée sur des données politiques peut influencer le débat public ; en cas de doute, on n'affiche pas, ou on affiche « non déterminé ».

**Exactitude**

1. **Aucune donnée inventée ni déduite.** Une valeur absente ou non résolue (nom, groupe, catégorie) s'affiche comme telle. Pas de rapprochement approximatif de noms : seuls les identifiants officiels (`PA…`, `PO…`) font foi.
2. **Réconciliation bloquante avant toute publication.** À chaque import, l'ETL vérifie pour chaque scrutin : pour + contre = suffrages exprimés ; pour + contre + abstentions = votants ; somme des groupes = totaux ; votes nominatifs = décomptes de groupe. Un écart n'est jamais corrigé en silence : il est consigné, et un écart nouveau **interrompt le déploiement** jusqu'à examen.
3. **Vérification indépendante.** Un script distinct du pipeline relit des fichiers JSON bruts tirés au hasard et compare chaque chiffre publié. Des tests utilisent des scrutins réels dont les valeurs ont été vérifiées à la main.
4. **Traçabilité.** Chaque scrutin publié porte le nom de son fichier source, son empreinte (SHA-256) et un lien vers la page officielle de l'Assemblée.
5. **Détection de changement anormal.** Si un réimport modifie de nombreux scrutins déjà publiés, ou en supprime, le déploiement attend une validation humaine.
6. **Historique public des données.** Une page « Qualité des données » indique la version, la date de synchronisation, l'empreinte de l'archive, les écarts connus de la source et les scrutins modifiés depuis la publication précédente.

**Neutralité**

7. **Lexique contrôlé.** Les textes de l'interface sont écrits dans un vocabulaire descriptif. Un test automatique refuse des termes évaluatifs (par exemple : cohésion, discipline, dissident, rebelle, frondeur, loyal, sage, extrême).
8. **Pas de mise en avant éditoriale.** Ordre alphabétique ou chronologique par défaut, jamais par « importance » ; pas de scrutin « à la une » choisi à la main, pas de classement de groupes ou de députés.
9. **Couleurs.** Les couleurs de vote (pour, contre, abstention, non-votant) sont les seules couleurs sémantiques. Aucune couleur n'est associée à un groupe politique, pour ne pas suggérer une orientation.
10. **Catégories incertaines signalées.** Une catégorie déduite d'un titre est marquée « à vérifier » ; un filtre ne présente jamais une catégorie incertaine comme une certitude.
11. **Corrections.** Un moyen de signaler une erreur est affiché sur le site ; les corrections publiées sont datées et conservées dans l'historique.
12. **Ce que le site n'est pas.** La page « Méthodologie » rappelle qu'il ne note ni n'évalue aucun élu ou groupe, que « contre » ne dit rien de la position sur le thème général d'un texte, et que les scrutins publics ne représentent qu'une partie de l'activité parlementaire.
