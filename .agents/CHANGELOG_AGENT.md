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

### 2026-11-18 — ALG-08 codée

**Ce qui a été fait** : code `etl/src/etl/algos/alg08_classification.py` (`classifier`, `charger_corrections`, `normaliser_titre`, commentaires `# ALG-08.k`), dataclasses `Classification` et `CorrectionTitre` et liste `CATEGORIES` (12 catégories) dans `models.py`. Tests `etl/tests/algos/test_alg08_classification.py` (un test par règle sur titre réel, cas limites, fichier de corrections `etl/corrections_classification.json`, archive locale complète). Suite complète : 269 réussis, 1 ignoré, 13 désélectionnés (tests `contenu_refuse` d'ALG-01, qui échouent sous Windows à cause de la longueur de l'identifiant de test).

**Vérifié sur les 8 877 scrutins locaux** : 0 conflit entre règles ; sans corrections 6 931 amendements, 654 sous-amendements, 936 articles, 240 textes, 58 motions de rejet, 23 motions de censure, 18 procédures, 4 déclarations du Gouvernement, 7 parties de loi de finances, 6 indéterminés ; avec les six corrections validées, 0 indéterminé.

**Ce qui n'est PAS couvert** : comptes non remesurés sur l'archive officielle de 9 895 scrutins (non téléchargée dans les tests) ; aucun branchement à l'export (ALG-11) ; mention générale sur le filtre à faire côté front ; `docs/methodology.md` déjà reformulé (garantie 10).

**Points d'attention** : le test d'archive complète lit les 8 877 fichiers (environ 40 s). La fiche ALG-14, ALG-01 (profil « référentiels ») et la migration `civilite` (ALG-09) restent à faire.

### 2026-11-18 — ALG-09 codée (et profil « référentiels » d'ALG-01)

**Ce qui a été fait** : `alg09_resolution_noms.py` (`resoudre_noms`, `indexer_referentiel`, commentaires `# ALG-09.k`) ; dataclasses `NomGroupe`, `NomDepute`, `RapportResolution`, `ResolutionNoms` dans `models.py` ; profils de lecture d'ALG-01 (`ProfilLecture`, `PROFIL_SCRUTINS` par défaut, `PROFIL_REFERENTIELS`, paramètre `profil` de `lire_archive` et `lire_source`) ; migration `db/migrations/002_deputes_civilite.sql` ; `appliquer_migrations` ne rejoue plus que les migrations postérieures à `user_version` ; fonctions SQLite `lire_references_noms`, `lire_anciens_noms`, `ecrire_noms` dans `io/db.py`. Tests : `test_alg09_resolution_noms.py` (23) et 8 tests de profil dans `test_alg01_archive.py`.

**Vérifié sur données réelles** : référentiel AMO30 téléchargé le 2026-11-14 (14 059 entrées : 14 000 acceptées, 59 `deport` ignorées, 0 refusée) ; avec l'archive locale de 8 877 scrutins : 13 groupes sur 13 et 652 députés sur 652 résolus, civilités 406 `M.` et 246 `Mme`, `PO847173` et `PO872880` distincts (sigle `UDR`).

**Ce qui n'est PAS couvert** : pas de commande `etl` ni d'étape de `pipeline.py` qui télécharge le référentiel et appelle ALG-09 (dépend d'ALG-13) ; l'archive officielle de 9 895 scrutins n'a pas été rejouée ; la civilité n'est pas encore dans l'export (ALG-11).

**Points d'attention** : la version de schéma attendue passe à 2 ; une base locale créée avant cette migration est détectée comme incompatible par ALG-07 (`schema_incompatible`) et doit être recréée ou migrée.

### 2026-11-18 — ALG-10 codée

**Ce qui a été fait** : `alg10_indicateurs_groupe.py` (`calculer_indicateurs`, `comparer_groupes`, `valider_bornes`, `libelles_tranches`, `indice_tranche`, commentaires `# ALG-10.k`) ; dataclasses `LigneGroupeScrutin`, `LigneVoteSelection`, `IndicateursGroupe`, `ScrutinCompare`, `ComparaisonGroupes` dans `models.py`. Tranches réglables (`bornes`, défaut `(20, 40, 60, 80)`), libellés en bornes numériques seules, personnes distinctes, tri sans critère évaluatif. Tests `test_alg10_indicateurs_groupe.py` (29), dont les exemples chiffrés de la fiche et l'archive locale complète.

**Vérifié sur les 8 877 scrutins locaux** : 13 groupes identifiés, 106 378 groupes-scrutins retenus (146 exclus, 14 scrutins concernés) ; **9 547 groupes-scrutins sans vote exprimé et 2 035 égalités, comme mesuré dans la fiche** ; tranche « moins de 20 % » vide pour tous les groupes ; `PO872880` et `PO847173` : 0 scrutin commun et 8 865 scrutins où un seul est présent.

**Ce qui n'est PAS couvert** : le recalcul de la comparaison dans le navigateur (cahier §8) et les vecteurs de test partagés avec Vitest (invariant « conformité inter-langages » de la fiche) ; les sélections précalculées (ALG-11) ; la catégorie des lignes n'est pas filtrée ici (les filtres sont appliqués par l'appelant).

**Points d'attention** : une ligne en double pour un même (groupe, scrutin) est une erreur de donnée ; la fonction ne lit jamais les mises au point.

### 2026-11-18 — ALG-13 codée

**Ce qui a été fait** : `alg13_telechargement.py` (`telecharger`, `url_autorisee`, `Parametres`, `PARAMETRES_SCRUTINS`, `PARAMETRES_REFERENTIELS`, protocoles `Transport` et `Stockage`, commentaires `# ALG-13.k`) ; `io/http.py` (`TransportHttp`, `http.client`, TLS vérifié, sans redirection automatique, `Accept-Encoding: identity`, délais de connexion et d'inactivité) ; `io/fs.py` (`StockageFichiers` : fichier temporaire, archive `<sha256>.zip`, `provenance.json`). Bibliothèque standard seulement. Tests `test_alg13_telechargement.py` (44) sur un serveur HTTP local : 200, 404, 503 puis 200, trois 503, `Retry-After`, coupure, page HTML, non-ZIP, flux trop gros, redirections (même hôte, autre hôte, boucle), configuration invalide, fraîcheur, version publiée (404, erreur, JSON invalide), délai total, erreurs de stockage.

**Vérifié en réel (hors tests)** le 2026-11-18 sur data.assemblee-nationale.fr : scrutins 30 755 838 octets, 1 tentative, relu par ALG-01 : `complet`, 9 969 scrutins (1 à 9 969, sans trou) ; référentiel AMO30 13 738 715 octets, relu avec le profil `referentiels` : 14 000 entrées, 59 ignorées. `Last-Modified` présent, aucun avertissement.

**Ce qui n'est PAS couvert** : pas de commande `etl download` ni d'étape de `pipeline.py` (variables de configuration `VOTEAPOL_SOURCE_URL`, hôtes autorisés, `meta.json` publié) ; TLS invalide non testé (aucun certificat de test) ; la conservation de 30 jours des artefacts est une affaire du workflow CI ; l'archive officielle évolue (9 895 scrutins le 2026-11-14, 9 969 le 2026-11-18).

**Points d'attention** : `url_meta_publie = None` désactive la comparaison (usage local) ; un `404` sur `meta.json` = première publication, toute autre erreur = échec `publie_inconnu`.

### 2026-11-18 — Refactoring : `models.py` devient le paquet `models/`

**Ce qui a été fait** : `etl/src/etl/models.py` supprimé ; paquet `etl/src/etl/models/` : `commun.py` (16 éléments : ALG-01 `EntreeAcceptee`, `EntreeRefusee`, `RapportLecture` ; ALG-02 `ScrutinNormalise`, `GroupeNormalise`, `Votant`, `LigneCorrection` ; ALG-03 `PositionMajoritaire` ; ALG-04 lot et lignes, `POSITIONS_VOTE`), `alg02.py`, `alg05.py`, `alg06.py`, `alg07.py`, `alg08.py`, `alg09.py`, `alg10.py`, `alg13.py` et `__init__.py` (47 éléments ré-exportés). Les modèles d'ALG-05, 07 et 13 ont quitté leurs modules algo (qui les importent depuis `..models`) ; `io/db.py`, `io/http.py` et `pipeline.py` importent depuis `..models`. Aucun changement de comportement.

**Vérifié** : suite complète (voir ci-dessous) ; `etl_version` inchangée (modules ALG-02, 04 et 06 non modifiés).

**Ce qui n'est PAS couvert** : les tests importent encore certains modèles depuis les modules d'algorithmes (ils fonctionnent, car ces modules les importent) ; migration des imports de tests à faire au fil de l'eau.

### 2026-11-18 — ALG-11 codée (export statique)

**Ce qui a été fait** : `alg11_export_statique.py` (`exporter`, `serialiser`, `construire_document`, `empreinte_chiffres`, `calculer_diff`, `lien_officiel`, commentaires `# ALG-11.k`) ; `alg11_schemas.py` (validateur écrit à la main, schémas de tous les fichiers) ; `models/alg11.py` (`ContexteExport`, `ParametresExport`, `ReferentielsExport`, `RapportExport`) ; `io/db.py` (`lire_scrutins_export`, `lire_referentiels_export`, `lire_contexte_base`) ; `io/fs.py` (`publier_fichiers` avec la procédure `.tmp` / `.precedent` et sa restauration, `recuperer_publication_interrompue`, `retirer_temporaire`) ; `pipeline.run_export` et option `--manifeste-precedent` de `etl export` ; `docs/data-dictionary.md`. Tests `test_alg11_export_statique.py` (38) : contenu, déterminisme, schémas, limites, refus (réconciliation, base vide, flux non trié), échantillon, empreinte composite, diff, publication, CLI de bout en bout, archive réelle.

**Vérifié sur les 8 877 scrutins locaux (import puis export, 7 min)** : 8 919 fichiers (8 877 scrutins, 13 groupes, 22 fragments d'index, 652 députés), 1 323 978 votes, scrutin 489 : 12 groupes `groupe_id = null`, `sans_vote_enregistre = null`, 118 Mo au total.

**Ce qui n'est PAS couvert** : le garde-fou de déploiement (ALG-12) qui consomme `manifeste.json` ; `type_empreinte` est écrit `non_renseigne` (non stocké en base) ; l'empreinte des référentiels n'entre pas encore dans `entrees` ; l'export ne produit pas encore les vecteurs de test partagés avec Vitest (ALG-10) ; ALG-14 relit les fichiers bruts (non écrite).

**Points d'attention** : fichiers `groupes/<id>.json` de 2,6 Mio (avertissement `fichier_volumineux` permanent, décision demandée) ; le test d'archive réelle dure environ 7 minutes.

### 2026-11-18 — ALG-12 codée (garde-fou de déploiement)

**Ce qui a été fait** : `alg12_garde_fou_deploiement.py` (`decider`, `doit_traiter`, `serialiser_decision`, `deploiement_autorise`, `verifier_deploiement`, commentaires `# ALG-12.k`) ; `models/alg12.py` (`EntreesDecision`, `ParametresDecision`, `DecisionPublication`) ; `empreinte_entrees` rendue publique dans `alg11_export_statique.py` ; `pipeline.version_algorithmes()` (empreinte du code d'ALG-02, 03, 04, 06, 08, 09, 10, 11 et des schémas) ajoutée aux entrées du manifeste par `etl export`. Tests `test_alg12_garde_fou_deploiement.py` (44) : un test par cas de la fiche, chaque règle G, les validations V toutes relevées, les avertissements A, les invariants sur toutes les combinaisons, `decision.json` canonique sans secret, autorisation de déploiement, et un enchaînement avec le vrai manifeste d'ALG-11.

**Ce qui n'est PAS couvert** : le workflow GitHub Actions (`sync.yml`) et la commande qui assemble les rapports (téléchargement, import, export, décision) ; ALG-14 (la règle G06 attend son rapport : sans lui, la décision est toujours `bloquer`) ; les empreintes des référentiels de noms (ALG-09 n'est pas encore branchée au pipeline) ; la restauration sur Cloudflare (`docs/deployment.md`).

**Points d'attention** : G02, G03 et G04 sont plus strictes que la fiche (tout statut inconnu bloque), documenté dans la fiche ; le mode sûr est actif par défaut dans `EntreesDecision`.

### 2026-11-18 — ALG-14 validée et codée (vérification indépendante)

**Ce qui a été fait** : fiche ALG-14 passée en `Validé` (v2 : échantillon de 200 + 4 obligatoires + 20 récents, champs comparés figés, contrôle global ajouté). Script `scripts/verifier_echantillon.py` : bibliothèque standard seulement, aucun import du paquet `etl` (vérifié par un test sur l'arbre syntaxique) ; relit le ZIP ou le dossier source et les fichiers `scrutins/<id>.json` ; extraction indépendante des variantes XML (objet unique, liste, `null`), comparaison des groupes par rang, des votes un à un, des empreintes SHA-256 ; code de sortie 0, 1 ou 2 ; rapport `verification.json`. Tests `test_alg14_verification_independante.py` (33) : export fidèle, écart du scrutin n° 1 reproduit tel quel, 18 types de dérive détectés, fichier absent ou en trop, `meta` incohérent, entrées illisibles, échantillon reproductible, indépendance du script.

**Vérifié sur les 8 877 scrutins locaux** (ajouté au test d'archive réelle d'ALG-11) : voir le résultat de la suite complète ci-dessous dans cette même entrée de journal.

**Ce qui n'est PAS couvert** : mises au point, dysfonctionnements, catégorie, position majoritaire (dérivées, voir la fiche) ; l'appel du script dans le workflow de CI et la transmission de son statut à ALG-12 (règle G06) ; la durée de l'échantillon de 200 en CI est à mesurer.

**Points d'attention** : la comparaison du SHA-256 du ZIP n'a lieu que si l'archive est un fichier (pas pour un dossier extrait).

### 2026-11-18 — ALG-11 : compactage de `groupes/<id>.json`

**Ce qui a été fait** (décision du responsable) : `groupes/<id>.json` porte `colonnes` (nommées une fois, `COLONNES_GROUPE` dans `alg11_schemas.py`) et des lignes en tableaux, position majoritaire mise à plat ; le validateur vérifie les colonnes ; l'avertissement `fichier_volumineux` exclut `manifeste.json` (lu seulement par le garde-fou). Fiche ALG-11 et `docs/data-dictionary.md` mis à jour ; trois tests ajoutés (équivalence ligne compacte et scrutin, schéma, avertissement).

**Ce qui n'est PAS couvert** : le front n'existe pas encore (aucun code à adapter) ; la taille réelle après compactage est mesurée par le test d'archive réelle (voir le résultat de la suite complète).

### 2026-11-19 — Chaîne ETL assemblée : `etl sync`, `autoriser`, `verifier-deploiement`, workflow

**Ce qui a été fait** : `pipeline.py` : `run_sync` (ALG-13 scrutins puis référentiels AMO30, « rien à faire » avant tout traitement, import dans une base neuve, ALG-09 branché, export, ALG-14 en sous-processus, décision ALG-12 écrite dans `decision.json`), `run_autoriser` (ALG-12.8 : décision et fichiers recalculés), `run_verifier_deploiement` (ALG-12.9), `entrees_composites` (inclut `referentiels_sha256`), `executer_import` et `executer_export` extraits de `run_import` / `run_export` (comportement inchangé). `io/http.py` : `lire_json_publie` (404 = aucune publication, toute autre anomalie lève). `config.py` : URL officielles et `VOTEAPOL_URL_PUBLIEE`. `cli.py` : commandes `sync`, `autoriser`, `verifier-deploiement`. `.github/workflows/sync.yml` : travail `sync` (tests, sync, artefacts 30 jours) et travail `deploy` (environnement `validation-publication` si `attente_validation`). `docs/deployment.md`. Tests `tests/integration/test_pipeline_sync.py` (13) : première publication, mode sûr, G01 (téléchargement, référentiels, état publié illisible), G05, « rien à faire », forçage, `publier` hors mode sûr, V06 (nom modifié), autorisation refusée pour une décision ou un artefact altéré, confirmation du déploiement.

**Vérifié** : suite complète `uv run pytest tests` : 517 réussis, 1 ignoré (16 min, archive réelle comprise). `ruff check` propre sur les fichiers modifiés.

**Ce qui n'est PAS couvert** : aucune exécution réelle de `etl sync` sur le réseau ni du workflow (variable, secrets et deux environnements GitHub à créer) ; comportement de la lecture ALG-01 (profil référentiels) sur le vrai fichier AMO30 non observé (statut `partiel` bloque, comme pour les scrutins) ; durée de `sync` complet en CI non mesurée ; restauration Cloudflare native à vérifier dans la documentation de la plateforme ; le build du front (`npm run build`) n'a pas été relancé.

**Points d'attention** : le hôte de la version publiée est ajouté à la liste des hôtes autorisés d'ALG-13 (une seule liste pour tout) ; le lint (`ruff check .`) avait 41 erreurs antérieures (style, `# fmt: skip` mal placés, `dict()` dans les tests…) : toutes corrigées le 2026-11-19, sans changement de comportement (réglage `extend-immutable-calls` ajouté dans `pyproject.toml` pour les paramètres figés `ParametresExport` et `ParametresDecision`) ; suite relancée hors tests d'archive réelle : 511 réussis, 1 ignoré ; la fiche ALG-12 dit encore que `sync.yml` n'est pas couvert (maintenant décrit dans `docs/deployment.md`).
