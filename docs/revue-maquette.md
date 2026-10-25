# Revue de la maquette au regard des règles du projet

Maquette corrigée : `Voteapol — UX UI.html` (copie de `Voteaplo — UX UI.html`, laissée intacte). Revue du 2026-10-25, faite sur le texte, les données d'exemple et les styles des 16 artboards. **Aucun rendu visuel n'a été contrôlé dans un navigateur** : les corrections sont vérifiées structurellement (les 16 pages se décompressent, le gabarit est un JSON valide, plus aucune occurrence des termes retirés).

## Écarts corrigés

| # | Règle | Écart constaté | Correction |
|---|-------|----------------|------------|
| 1 | Nom du projet | « Voteaplo » partout | « Voteapol » |
| 2 | Données | Législature XVIᵉ (2022–2027) et choix XVᵉ ; la source couvre la XVIIᵉ (scrutins d'octobre 2024 à octobre 2026 dans l'échantillon) | XVIIᵉ (depuis 2024), option XVᵉ retirée, période 2024–2026 |
| 3 | Pas de « cohésion » (décision 2026-10-22) | Cohésion sur les cartes de groupes, fiche groupe, comparaison, statistiques (KPI « Cohésion moyenne » et colonne du tableau), mobile, documentation d'intégration | Supprimée partout, y compris les clés de données d'exemple |
| 4 | Pas de score ni d'indicateur non défini | KPI « Activité parlementaire +12 % » (non défini dans la méthodologie) | Supprimé (desktop et mobile) |
| 5 | Pas de couleur par groupe (garantie 9) | Chaque groupe avait une teinte propre (cartes de groupes, comparaison) | Teinte neutre unique pour tous les groupes |
| 6 | `VoteBadge` seul porteur des couleurs de vote | « Adopté » en vert et « Rejeté » en rouge : le résultat d'un scrutin n'est pas un vote, et les couleurs suggèrent un jugement | Nouveau type neutre `resultat` du composant `VoteBadge` (icône + libellé, couleur neutre) ; badges de résultat de l'accueil, de l'explorateur, de la fiche scrutin, du mobile et du design system basculés. Le libellé erroné « Non-votants: 48 » comme résultat est remplacé |
| 7 | Dénominateurs explicites (neutralité) | Fiche scrutin : pourcentages calculés sur 577 en incluant les non-votants | Pourcentages sur les 564 suffrages exprimés, non-votants indiqués à part |
| 8 | Hors MVP signalé « à venir » | Résumé pédagogique rédigé à la main sur la fiche scrutin ; sujets présentés comme opérationnels | Résumé supprimé ; « (à venir) » ajouté sur « Explorer par sujet », « Statistiques par domaine », « Comparaison par sujet », « Par sujet » |
| 9 | Formulations neutres | « Positions majoritaires convergentes / divergentes » (suggère des rapprochements) | « Même position majoritaire » / « Positions majoritaires différentes » |
| 10 | Architecture (site statique) | Documentation d'intégration : D1 et endpoints `GET /api/…` | D1 retiré, `GET /api/` remplacé par `JSON /data/v1/` |

## Écrans ajoutés sur la fiche scrutin (2026-10-25)

Tous sont sur l'artboard « Fiche scrutin ». La position majoritaire y est calculée par le script de la page selon la fiche `ALG-03` (données fictives).

| Écran / état | Contenu |
|--------------|---------|
| Position majoritaire avec effectifs | « Pour : 140 sur 164 » + effectifs complets du groupe (pour, contre, abstentions, non-votants) et « 164 exprimés sur 168 membres » ; mention « majorité absolue des exprimés » ou « majorité relative » |
| Pas de position majoritaire | Pastille neutre « Pas de position majoritaire » avec la raison : « Égalité entre 2 positions » (LR) ou « Aucun vote exprimé » (NI) |
| Cause de non-vote | Pastille sur le député : membre du gouvernement, président de séance, président de l'Assemblée ; phrase de synthèse sous la répartition des voix |
| Vote par délégation | Pastille « Vote par délégation » sur le député |
| Mises au point | Carte dédiée : explication (résultats officiels non modifiés), tableau député / groupe / position enregistrée → position déclarée, cas du député sans groupe retrouvé (« Groupe non déterminé », « Position enregistrée non retrouvée ») |
| Mise au point qui change le résultat | Bandeau sous la ligne du groupe concerné (SOC) : effectifs corrigés, « Les chiffres officiels restent ceux affichés ci-dessus » ; pastille « Mise au point signalée » sur les députés concernés |
| Ordre des groupes | Annoncé : « Groupes classés par effectif » ; rappel de la définition de la position majoritaire avec lien vers la méthodologie |

## Écarts non corrigés (à traiter au moment du développement)

1. **Effectifs et pourcentages hors fiche scrutin** : les cartes de groupes, la fiche groupe et les statistiques affichent encore des pourcentages (participation, répartition) sans « n sur N ». À remplacer par `E sur effectif` et `m sur E` (ALG-03, ALG-10).
2. **Fiche groupe** : la colonne « Position majoritaire » de l'historique n'a pas encore l'état « pas de position majoritaire ».
3. **Filtres par sujet** : encore présents dans l'explorateur et les statistiques (P2). À masquer dans le MVP plutôt que de les laisser sans effet.
4. **Comparateur de groupes** : la liste des scrutins en accord / désaccord doit montrer ses effectifs et la raison quand il n'y a pas de position majoritaire.
5. **Données d'exemple fictives** : 11 groupes, 4 812 scrutins, numéros 1248, etc. La source compte 8 877 scrutins et 12 groupes par scrutin dans l'échantillon. Tout chiffre réel devra venir de `meta.json`.
6. **Couleur des sujets** : les tuiles de sujets de l'accueil gardent des teintes distinctes ; elles ne concernent pas des groupes mais disparaissent avec le report du sujet en P2.
7. **Version mobile** de la fiche scrutin : non dessinée (un seul composant responsive est prévu au développement).
