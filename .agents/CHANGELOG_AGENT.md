# CHANGELOG_AGENT.md — Journal d'état du projet

> Mis à jour par l'agent IA après chaque tâche terminée.  
> **But** : permettre à un humain ou un autre agent de reprendre le travail sans contexte de session.  
> Ne remplace pas `DECISIONS.md` (pourquoi) ni le README (usage) — répond à la question **"où en est le code ?"**

---

## Comment lire ce fichier

- Lis les entrées **du bas vers le haut** — la plus récente est en bas.
- Chaque entrée = une tâche terminée.
- La section **"État global"** en haut est mise à jour à chaque entrée et reflète toujours le présent.

---

## État global du projet

> Mis à jour après chaque tâche. Reflète l'état actuel.

| Module | État | Dernière modif |
|--------|------|----------------|
| ETL Python (`etl/`) | Non démarré | — |
| Base SQLite / migrations (`db/`) | Non démarré | — |
| API Worker (`web/worker/`) | Non démarré | — |
| Front Vue (`web/src/`) | Non démarré (maquette disponible) | — |
| CI / sync GitHub Actions | Non démarré | — |
| Documentation (`README.md`, `docs/`) | README rédigé ; `docs/` à créer | 2026-10-22 |

**Données** : l'archive `Scrutins.json.zip` n'est pas encore dans le dépôt (attendue dans `data/`, ignoré par Git).

---

## Entrées

### 2026-10-22 — Cadrage initial

**Ce qui a été fait** :
- Lecture du cahier technique et de la maquette (16 artboards, documentation d'intégration).
- Rédaction de `README.md`.
- Renommage « PolitiScope » → « Voteapol » dans le cahier technique.
- Adaptation du dossier `.agents/` au projet (il provenait d'un autre projet).
- Décision d'architecture : site statique sans API ni D1 sur Workers Static Assets (README, cahier, CONVENTIONS et DECISIONS mis à jour).
- Décision : indicateur « cohésion » remplacé par deux indicateurs descriptifs (voir DECISIONS) ; sujets reportés en P2 ; Tailwind confirmé.

**Ce qui n'est PAS couvert** : aucun code, aucune structure de dossiers `etl/` `web/` `db/`, pas de `.gitignore`.

**Points d'attention** : décisions en suspens listées dans `DECISIONS.md` (bibliothèque de recherche, format des votes individuels, licence). Limites Cloudflare à revalider avant déploiement. Prochaine étape : phase A du cahier (inspection du ZIP, ETL, SQLite).

### 2026-10-22 — Analyse d'un échantillon des scrutins

**Ce qui a été fait** : lecture de `VTANR5L17V1017.json` et contrôles automatiques sur 600 fichiers tirés au hasard (sur 8 877). Résultats consignés dans `docs/analyse-donnees-sources.md`.

**Ce qui n'est PAS couvert** : les 8 277 autres fichiers, les référentiels acteurs/organes (non fournis), la liste complète des valeurs de `causePositionVote`.

**Points d'attention** : `positionMajoritaire` de la source est incohérente avec les décomptes (calcul propre requis) ; `miseAuPoint` à traiter (décision à prendre) ; `dossierLegislatif` souvent `null`.

### 2026-10-25 — Revue et correction de la maquette

**Ce qui a été fait** : audit des 16 artboards au regard des règles (neutralité, cohésion, couleurs de groupe, dénominateurs, législature, hors MVP). 10 écarts corrigés dans `Voteapol — UX UI.html` ; liste dans `docs/revue-maquette.md`. Rédaction des fiches : `docs/algorithmes/` (ALG-03 en brouillon).

**Ce qui n'est PAS couvert** : écrans manquants (mises au point, absence de position majoritaire, causes de non-vote), « n sur N » sur les pourcentages, masquage des filtres par sujet ; aucun contrôle visuel dans un navigateur.

### 2026-10-25 — Écrans manquants de la fiche scrutin

**Ce qui a été fait** : ajout dans la maquette (fiche scrutin) de la position majoritaire avec effectifs, de l'état « pas de position majoritaire », des causes de non-vote, du vote par délégation et des mises au point (carte dédiée et bandeau de groupe). Logique de calcul de la page vérifiée sous Node (6 groupes d'exemple) ; détail dans `docs/revue-maquette.md`.

**Ce qui n'est PAS couvert** : rendu visuel non contrôlé dans un navigateur ; fiche groupe, comparateur et statistiques pas encore alignés sur « n sur N ».

### 2026-11-03 — Brouillons des fiches ALG-04 à ALG-13

**Ce qui a été fait** : rédaction des dix fiches restantes dans `docs/algorithmes/` (statut Brouillon, rien n'est validé) et mise à jour de l'index. Les fiches s'appuient sur des mesures faites sur les 8 877 fichiers (scrutin n° 1 : seul écart de non-votants ; 2 389 mises au point rattachables sur 3 243 ; classification des titres par règles : 8 871 sur 8 877 classés, 6 indéterminés par fautes de frappe ; 149 votes enregistrés par scrutin en moyenne ; 652 députés et 13 groupes réels).

**Ce qui n'est PAS couvert** : ALG-09 (référentiels non inspectés, aucune structure vérifiée) ; adresse officielle de l'archive (ALG-13) et modèle du lien officiel des scrutins (ALG-11) inconnus ; aucun code ; ALG-14 (vérification indépendante) seulement proposée.

**Points d'attention** : plusieurs fiches modifient des interfaces (schéma §4 : `rang`, `groupe_rang`, `cause`, `origine`, `etl_version` ; fichiers publics : `deputes.json`, `qualite.json`, `manifeste.json`) et demandent validation. Limite de 20 000 fichiers de Cloudflare atteinte en environ 3 mois si les votes ont un fichier séparé (ALG-11). La valeur « 577 votants par scrutin » de `DECISIONS.md` (décisions en suspens) est inexacte pour le nombre de votes enregistrés.

### 2026-11-11 — ALG-01 validée et codée

**Ce qui a été fait** : fiche ALG-01 passée en `Validé` (v2 : champs `motif_echec` et `liens_symboliques_ignores`, questions ouvertes tranchées). Code : `etl/src/etl/algos/alg01_archive.py` (commentaires `# ALG-01.k`), lecteurs `etl/src/etl/io/zipfile.py` et `io/dossier.py`, dataclasses dans `models.py`, `pipeline.lire_source`. Tests `etl/tests/algos/test_alg01_archive.py` (fixtures : 3 vrais scrutins).

**Ce qui n'est PAS couvert** : `MAX_RATIO` non calibré sur le vrai ZIP (seul le dossier extrait existe) ; la commande `etl inspect` n'est pas branchée (dépend d'ALG-02/04) ; cas « en-tête annonçant 1 Ko, flux de 100 Mo » non testable avec `zipfile` (il tronque à la taille déclarée, l'écart ressort en `corrompue`).

**Points d'attention** : `lire_archive` renvoie une liste : les 8 877 documents JSON sont tous gardés en mémoire (à surveiller, ou passer en flux si besoin). Le test du nom contenant un antislash est ignoré sous Windows.

### 2026-11-11 — ALG-02 validée et codée

**Ce qui a été fait** : fiche ALG-02 passée en `Validé` (v2, 5 propositions retenues). Code : `etl/src/etl/algos/alg02_normalisation.py` (`normaliser_scrutin`, fonctions N1 à N9, commentaires `# ALG-02.k`), dataclasses dans `models.py` (`ScrutinNormalise`, `GroupeNormalise`, `Votant`, `LigneCorrection`, `Anomalie`, `ResultatNormalisation`). Tests `etl/tests/algos/test_alg02_normalisation.py` (fixtures : scrutins 1, 2, 3, 489, 1017, 1302).

**Vérifié sur les 8 877 scrutins réels** : tous normalisés sans erreur ; 106 524 groupes dont 146 non identifiés ; 1 323 978 votes ; 3 243 mises au point ; 163 dysfonctionnements ; types et résultats conformes à la fiche ; seuls avertissements : 146 `groupe_non_identifie`.

**Ce qui n'est PAS couvert** : mise à jour de `docs/methodology.md` et de la maquette pour « sans vote enregistré » (décision 2 de la fiche) ; contrôles de totaux (ALG-05) ; `etl inspect` non branché.

**Points d'attention** : la normalisation des 8 877 scrutins prend environ 35 s (test d'intégration inclus dans la suite).
