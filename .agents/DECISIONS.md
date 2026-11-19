# DECISIONS.md — Journal des décisions techniques

> Rempli par l'agent IA au fil du projet, pour chaque choix structurant.  
> Objectif : permettre de comprendre "pourquoi" le code est comme il est, 2 mois plus tard.

---

## Format

```markdown
### [YYYY-MM-DD] [Titre court]
**Contexte** : Quel problème / besoin a motivé cette décision.
**Décision** : Ce qui a été choisi.
**Alternative écartée** : Ce qui a été considéré mais rejeté, et pourquoi.
**Conséquences** : Ce que ça implique (contraintes, dette, dépendances).
```

---

## Décisions

### [2026-10-22] Nom du projet : Voteapol
**Contexte** : Trois noms coexistaient : « PolitiScope » (cahier technique), « Voteaplo » (maquette), « Voteapol » (dossier).  
**Décision** : Le nom retenu est **Voteapol**. Cahier technique et README alignés.  
**Alternative écartée** : PolitiScope, Voteaplo.  
**Conséquences** : La maquette a été renommée et corrigée (`Voteapol — UX UI.html`, voir `docs/revue-maquette.md`) ; l'ancien fichier `Voteaplo — UX UI.html` est conservé tel quel et peut être supprimé.

---

### [2026-10-22] Périmètre : députés et groupes parlementaires
**Contexte** : Le besoin initial parlait des « votes des ministres ».  
**Décision** : Le projet couvre les **scrutins publics de l'Assemblée nationale** : votes des députés, agrégés par groupe parlementaire.  
**Alternative écartée** : Votes des membres du gouvernement (non pertinent : ils ne votent pas à l'Assemblée, leur suppléant prend leur place).  
**Conséquences** : Le vocabulaire du projet est `scrutin`, `groupe`, `depute`.

---

### [2026-10-22] Source : open data officiel, pas de scraping
**Contexte** : L'idée initiale était de « scraper » une plateforme publique.  
**Décision** : Télécharger l'archive open data officielle (ZIP JSON des scrutins) et les référentiels acteurs/organes, avec contrôle du SHA-256 et conservation de la provenance.  
**Alternative écartée** : Scraping HTML — fragile, moins fiable, juridiquement moins clair.  
**Conséquences** : L'ETL dépend du format publié par l'Assemblée ; la structure doit être vérifiée sur données réelles avant d'être figée.

---

### [2026-10-22] Priorité à l'ETL, noms résolus dès la phase A
**Contexte** : Le ZIP ne contient que des identifiants `PO…` / `PA…`.  
**Décision** : L'import des référentiels de groupes et de députés fait partie de la phase A, pas de la phase B.  
**Alternative écartée** : Afficher des identifiants bruts jusqu'au MVP — site inutilisable.  
**Conséquences** : L'ETL doit gérer plusieurs sources (scrutins + référentiels).

---

### [2026-10-22] Site statique : pas d'API, pas de D1, Workers Static Assets
**Contexte** : Le cahier prévoyait un Worker API + D1. Vérification de la documentation Cloudflare : requêtes sur assets statiques gratuites et illimitées ; D1 gratuit limité à 100 000 lignes écrites/jour et, depuis le 2026-09-01, les requêtes échouent au-delà du quota. Cloudflare Pages reste supporté mais les nouveaux projets sont orientés vers Workers + Static Assets.
**Décision** : L'ETL (GitHub Actions) exporte des fichiers JSON statiques, déployés avec le front par `wrangler deploy` sur Workers Static Assets. Recherche, filtres, pagination et comparaison s'exécutent dans le navigateur. SQLite ne sert qu'à l'ETL.
**Alternative écartée** : D1 + Worker API (quota d'écritures, complexité, pas de bénéfice pour des données mises à jour une fois par jour) ; Cloudflare Pages (voie moins recommandée pour un nouveau projet).
**Conséquences** : Limites à respecter : 20 000 fichiers par déploiement, 25 Mo par fichier. Le contrat des fichiers (`/data/v1/…`) devient l'interface publique ; le cahier §8 est réécrit en conséquence. L'index de recherche doit rester léger pour le mobile. À revérifier dans la documentation Cloudflare avant le déploiement (limites susceptibles d'évoluer).

---

### [2026-10-22] Indicateurs sur les groupes (remplace la « cohésion » de la maquette)
**Contexte** : La maquette affiche une « cohésion » par groupe. Le cahier interdit les scores de cohérence idéologique ; l'objectif est d'informer sans influencer.
**Décision** : Le mot « cohésion » est abandonné. Seuls deux indicateurs descriptifs sont autorisés, toujours affichés sous forme « n sur N » avec leur dénominateur :
1. **Présence au scrutin** : nombre de membres ayant voté (pour, contre, abstention) sur l'effectif du groupe au moment du scrutin. Les non-votants sont comptés à part, jamais comme abstentions.
2. **Part de la position majoritaire du groupe** : `m sur E` (nombre de membres ayant voté comme la position la plus fréquente, sur les positions exprimées). La position majoritaire est **recalculée par l'ETL** à partir de `decompteVoix` (pluralité stricte ; égalité ou aucun vote exprimé → pas de position majoritaire). La formule complète et les cas limites sont dans `docs/methodology.md`.

Sur plusieurs scrutins : afficher la répartition brute (nombre de scrutins par niveau), jamais une moyenne unique présentée comme un score.
**Alternative écartée** : « cohésion », « discipline de vote », « loyauté », « dissidents/frondeurs » (connotés, jugent le comportement) ; classement des groupes par alignement.
**Conséquences** : Pas de tri par défaut ni de classement fondé sur ces indicateurs ; ordre par défaut des groupes alphabétique (ou par effectif, annoncé). Les libellés exacts et les cas limites seront détaillés dans `docs/methodology.md`. La maquette (fiche groupe, statistiques) devra être adaptée : tout libellé « cohésion » est remplacé.

---

### [2026-10-22] Position majoritaire d'un groupe : calcul ETL, valeur source écartée
**Contexte** : `positionMajoritaire` de la source contredit les décomptes (226 cas sur environ 7 100 groupes-scrutins ; « pour » pour des groupes sans vote). Les décomptes eux-mêmes sont cohérents avec les listes nominatives (600 scrutins). Aucune explication de l'écart trouvée.  
**Décision** : La position est recalculée (majorité relative stricte sur les positions exprimées, voir `docs/methodology.md`). La valeur source reste en base dans `position_majoritaire_source`, non affichée.  
**Alternative écartée** : Faire confiance à la source ; supprimer la notion de position (on perdrait une information utile alors qu'elle est calculable).  
**Conséquences** : Tests sur les cas limites du document de méthodologie ; mention de l'écart dans le dictionnaire de données.

---

### [2026-10-22] Mises au point : affichées à part, résultat officiel inchangé
**Contexte** : `miseAuPoint` recense des députés qui déclarent après coup une autre position. Sur 600 scrutins : 99 concernés ; les décomptes officiels ne les intègrent pas ; la position majoritaire d'un groupe change dans 7 cas sur 7 189 ; 58 rectifications sur 276 visent un député absent des décomptes nominatifs.  
**Décision** : Les chiffres principaux restent les chiffres officiels. Les mises au point sont affichées dans un encart dédié par scrutin, et un signalement apparaît sur la ligne d'un groupe dont la position majoritaire changerait. Détail dans `docs/methodology.md`.  
**Alternative écartée** : Remplacer les votes initiaux par les positions rectifiées (ce n'est pas le résultat officiel et masquerait l'information d'origine) ; ignorer les mises au point (information officielle perdue).  
**Conséquences** : Table `scrutin_mises_au_point` ajoutée au cahier (scrutin, député, groupe si connu, position initiale si connue, position déclarée). Le champ `dysfonctionnement` (pour/contre déclarés lors d'un dysfonctionnement du boîtier, 11 scrutins sur 600) reste à étudier.

---

### [2026-10-25] Charte d'intégrité et de neutralité
**Contexte** : Des données politiques mal traitées ou mal présentées peuvent influencer le débat public.  
**Décision** : Les 12 garanties de `docs/methodology.md` (« Garanties d'intégrité et de neutralité ») sont obligatoires : réconciliation bloquante, vérification indépendante, traçabilité, validation humaine en cas de changement anormal, lexique contrôlé par test, pas de couleur par groupe, pas de classement.  
**Alternative écartée** : Appliquer ces contrôles seulement à titre indicatif (risque de dérive silencieuse).  
**Conséquences** : Tests et CI à prévoir dès la phase A (réconciliation) et phase B (lexique, couleurs). La maquette doit être revue pour les couleurs de groupe éventuelles.

---

### [2026-10-25] Spécification avant code, fiches ALG-NN
**Contexte** : Les données politiques exigent un traitement rigoureux et auditable.
**Décision** : Chaque traitement a une fiche `ALG-NN` (formules, algorithme numéroté et justifié, cas limites, exemples, invariants) validée avant le code. Le code reprend les étapes une à une (`# ALG-NN.k`) et les tests reprennent les cas de la fiche.
**Alternative écartée** : Documenter après coup (dérive possible entre la documentation et le code).
**Conséquences** : Plus de rédaction en amont ; en contrepartie, relecture facilitée et audit possible. Dossier `docs/algorithmes/`.

---

### [2026-10-22] Sujets et résumés pédagogiques reportés en P2 ; Tailwind retenu
**Contexte** : La maquette montre des filtres par sujet et un résumé pédagogique ; le cahier exclut la catégorisation sémantique du MVP.
**Décision** : Reportés en P2, absents du MVP. Tailwind CSS est confirmé comme framework de style (tokens de la maquette).
**Alternative écartée** : Les inclure dans le MVP via une classification par mots-clés (peu fiable).
**Conséquences** : Le MVP filtre par date, catégorie (article, amendement, texte, motion, déduite des métadonnées/titres, avec « à vérifier ») et résultat.

---

### [2026-11-04] Licence du code : MIT
**Contexte** : Le dépôt devait être ouvert (transparence du traitement des données politiques).
**Décision** : Le **code** est sous licence MIT (fichier `LICENSE`). Les **données** gardent leur licence d'origine (Assemblée nationale, open data) : attribution et conditions à rappeler dans `docs/methodology.md` et le pied de page du site.
**Alternative écartée** : Licence copyleft (GPL/AGPL) : contraignante pour des réutilisateurs sans bénéfice pour ce projet.
**Conséquences** : Licence vérifiée le 2026-11-14 : « Licence Ouverte / Open Licence » (version non précisée sur la page), mention de la paternité obligatoire ; voir la décision du 2026-11-14 sur les sources.

---

### [2026-11-04] Recherche côté navigateur : MiniSearch (provisoire)
**Contexte** : Environ 8 900 scrutins à rechercher par titre, avec filtres date/catégorie/résultat, dans un site statique (SPA Vue).
**Décision** : MiniSearch, derrière une petite interface `search(query, filtres)` pour pouvoir le remplacer. Poids réel de l'index mesuré après le premier export (phase A).
**Alternative écartée** : Pagefind, conçu pour indexer des pages HTML et mal adapté à une SPA alimentée par JSON.
**Conséquences** : Seuil de bascule : si l'index dépasse environ 1 Mo compressé, découpage par année ou passage à Pagefind. L'index doit rester généré par l'ETL (ALG-11).

---

### [2026-11-04] Architecture du code : algos purs, I/O isolées, front sans Worker
**Contexte** : 13 fiches ALG à coder, et un hébergement gratuit Cloudflare sans code serveur.
**Décision** : ETL en trois couches : `algos/` (un module par fiche, fonctions pures), `io/` (réseau, ZIP, SQLite, fichiers), `pipeline.py` + `cli.py` (seuls à relier les deux). Front Vue 3 + TypeScript + Vite + Tailwind ; `data/` est le seul endroit qui fait `fetch`. Aucun code Worker : `wrangler.jsonc` ne contient que des assets, avec repli SPA. Gestionnaires : uv (Python), npm (web).
**Alternative écartée** : Dossier `web/worker/` du cahier initial (contredisait la décision « pas d'API ») ; store Pinia (données en lecture seule, composables suffisants).
**Conséquences** : Tout calcul à la volée côté visiteur doit tenir dans le navigateur à partir des JSON. À revérifier : `not_found_handling: single-page-application` dans la doc Cloudflare avant le premier déploiement.

---

### [2026-11-14] Relecture des algorithmes : corrections de spécification
**Contexte** : Une relecture externe des fiches ALG-01 à ALG-13 a signalé des incohérences et des faiblesses.
**Décision** : (1) ALG-05 : l'écart du scrutin n° 1 (21 non-votants nominatifs pour 10 au total) apparaît en R07 **et** R08 (deux écarts connus) ; R11 et R12 réservés au niveau lot. (2) ALG-01 : trous de numérotation comptés sans énumération (détail plafonné à 1 000), bornes aussi pour les dossiers, numéros limités à 9 chiffres ; ALG-02 : entiers limités à 18 chiffres. (3) ALG-12 : « rien à faire » repose sur une empreinte d'entrées composite (archive, versions d'algorithmes, référentiels, règles de classification), pas sur l'archive seule. (4) « Présence » renommée « participation au vote enregistrée » (les délégations comptent) ; `change_resultat` renommé `change_position_majoritaire` ; toute position affichée avec son effectif (ALG-03).
**Alternative écartée** : Garder « présence » (mathématiquement exact mais trompeur politiquement) ; décider « rien à faire » sur l'archive seule.
**Conséquences** : Fiches ALG-01, 02, 03, 05, 06, 10, 11, 12 modifiées ; la garantie 10 de `docs/methodology.md` reformulée le 2026-11-14 (voir ci-dessous).

---

### [2026-11-14] Classification : vocabulaire étendu et affichage de l'incertitude (ALG-08)
**Contexte** : 99,7 % des scrutins sont déduits d'un titre ; un badge « à vérifier » presque partout perd son sens.
**Décision** : Donnée conservée (`a_verifier`, `classification_confidence`) ; affichage par une mention générale sur le filtre, badge réservé aux scrutins indéterminés ou incohérents. Catégories ajoutées : `sous_amendement`, `declaration_gouvernement`, `partie_loi_finances`. Catégorie non stockée, recalculée à l'export. Six corrections de titres validées le 2026-11-18 (`etl/corrections_classification.json`).
**Alternative écartée** : Badge sur chaque scrutin ; garder les sous-amendements dans `amendement`.
**Conséquences** : Vocabulaire du cahier §6 étendu ; garantie 10 reformulée ; comptes à remesurer sur l'archive complète (9 895 scrutins).

---

### [2026-11-14] Indicateurs de groupe : tranches réglables sans qualificatif, personnes distinctes (ALG-10)
**Contexte** : La fiche proposait des tranches à 90 % et 75 % ; le responsable a demandé des tranches réglables (<20, 20-40, 40-60, 60-80, >80, 100 %).
**Décision** : Tranches réglables par défaut `[20, 40, 60, 80]` + 100 % (unanime), libellées par leurs bornes seules, **sans qualificatif** (« faible », « élevé » refusés : décision de neutralité du 2026-10-22 maintenue) ; bornes = limites inférieures incluses ; nombre de personnes distinctes calculé en plus des membres-scrutins. La tranche « moins de 20 % » est structurellement vide (part minimale 33,4 %).
**Alternative écartée** : Libellés qualitatifs ; seuils fixes.
**Conséquences** : Statistiques précalculées par catégorie et par année (ALG-11). `PO847173` et `PO872880` restent deux groupes distincts (même sigle UDR, sans lien dans le référentiel).

---

### [2026-11-14] Sources officielles vérifiées (ALG-09, ALG-13)
**Contexte** : Les adresses officielles et les référentiels n'étaient pas vérifiés.
**Décision** : Scrutins : `https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip` (30 518 412 octets, 9 895 scrutins au 2026-11-14). Référentiels : fichier AMO30 (`.../17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip`, 13 736 513 octets). Hôte autorisé : `data.assemblee-nationale.fr`. Licence : Licence Ouverte / Open Licence (mention de la paternité obligatoire ; version non précisée sur la page). Un téléchargement a confirmé les empreintes MD5 affichées sur la page source ; elles ne sont pas utilisées (pas de lecture de page web).
**Alternative écartée** : Lire la page web pour récupérer l'empreinte (contraire à « pas de scraping »).
**Conséquences** : Mention de la paternité à prévoir sur le site ; les références `PO0` n'existent pas dans le référentiel.

---

### [2026-11-18] Fiches ALG-01 à ALG-13 validées ; ALG-14 créée
**Contexte** : Les questions ouvertes ont été posées au responsable du projet.
**Décision** : (1) Base reconstruite à chaque exécution de la CI ; `etl_version` **calculée** (SHA-256 des modules ALG-02, 04, 06) ; aucune suppression de scrutin (pas d'`etl prune`) ; `--dry-run` ajouté. (2) Votes individuels **dans `scrutins/<id>.json`** ; un fichier par scrutin, alerte à 15 000 fichiers ; nouveaux fichiers `deputes.json`, `qualite.json`, `manifeste.json`, `scrutins-index.json` ; lien officiel `https://www.assemblee-nationale.fr/dyn/17/scrutins/<numéro>` ; validateurs de schémas écrits à la main. (3) Mode sûr au départ, validation par un seul relecteur (le responsable) ; seuils de 20 et 500 conservés. (4) Noms des députés : nom, prénom et civilité seulement ; profil de lecture ajouté à ALG-01 pour les référentiels. (5) 404 sur `meta.json` = première publication, autre erreur = échec ; archives et artefacts conservés 30 jours. (6) **ALG-14** (vérification indépendante sur fichiers bruts tirés au hasard) créée, règle bloquante G06 d'ALG-12.
**Alternative écartée** : `etl_version` manuelle ; fichiers de votes séparés ; ALG-14 repoussée.
**Conséquences** : Cahier technique passé en 0.2 (2026-11-18). Reste à faire dans le code : profil ALG-01, migration `civilite`, ALG-08 à ALG-14. ALG-14 est encore en « Brouillon ».

---

### [2026-11-18] Modèles de données : paquet `models/` (commun + un fichier par algorithme)
**Contexte** : `models.py` atteignait 437 lignes et mêlait les modèles de sept algorithmes, tandis que ceux d'ALG-05, 07 et 13 vivaient dans leur module algo : deux conventions à la fois.
**Décision** : `etl/models/` avec `commun.py` (modèles utilisés par au moins deux algorithmes : sorties d'ALG-01, contrat d'ALG-02, position majoritaire d'ALG-03, lot d'ALG-04), un fichier `algNN.py` par algorithme pour ses modèles propres (types d'entrée, de sortie, de rapport, paramètres, protocoles d'E/S), et un `__init__.py` qui ré-exporte tout. Règle : un modèle passe dans `commun.py` dès qu'un deuxième algorithme l'importe. `commun.py` n'importe rien d'autre du projet ; les fichiers `algNN.py` n'importent que `commun.py` et leurs voisins du paquet. Les exceptions et les constantes de comportement restent dans les modules d'algorithmes.
**Alternative écartée** : laisser les modèles propres dans le module de leur algorithme (mélange données et fonctions pures) ; garder un seul `models.py`.
**Conséquences** : `from etl.models import X` fonctionne partout, sans changement des imports existants. `etl_version` (ALG-07) est inchangée : elle ne hache que les modules ALG-02, 04 et 06, qui n'ont pas été modifiés. Les modèles d'ALG-11, 12 et 14 iront dans `models/alg11.py`, `alg12.py`, `alg14.py`.

### [2026-11-19] Assemblage de la chaîne : `etl sync`, déploiement en deux travaux
**Contexte** : ALG-01 à ALG-14 sont codés ; il restait à les enchaîner (téléchargement, référentiels de noms, vérification indépendante, décision) et à décrire le déploiement.
**Décision** : (1) Commande `etl sync` (`pipeline.run_sync`) : lit l'état publié (`manifeste`, `meta`, `qualite`, `groupes`, `deputes`), télécharge scrutins puis référentiels AMO30 (ALG-13), répond « rien à faire » avant tout traitement si **toutes** les entrées sont identiques, importe dans une base neuve, résout les noms (ALG-09), exporte, lance ALG-14 **dans un processus séparé** (le script n'importe rien de `etl`), puis écrit `decision.json` (ALG-12). (2) L'empreinte composite des entrées contient désormais `referentiels_sha256` (empreinte de l'archive AMO30) : un référentiel modifié fait retraiter une archive inchangée. (3) La base étant reconstruite, ALG-09.8 compare les noms aux fichiers publiés `groupes.json` et `deputes.json`, pas à la base. (4) Référentiels indisponibles ou lecture non complète, état publié illisible, tests en échec : la décision est `bloquer` (G01 ou G05), jamais une publication dégradée ; seul un 404 vaut « première publication ». (5) Déploiement : travail `deploy` distinct, environnement `validation-publication` (un relecteur) si la décision est `attente_validation`, `publication` si `publier` ; `etl autoriser` recalcule `rapport_sha256` et `donnees_sha256` avant de laisser passer ; `etl verifier-deploiement` relit `meta.json` en ligne (ALG-12.9). (6) Restauration : redéployer l'artefact `donnees` d'une exécution antérieure (30 jours).
**Alternative écartée** : appeler `etl import` / `etl export` séparément depuis le YAML (la logique de décision serait dispersée dans le workflow) ; importer ALG-14 dans le paquet (perdrait son indépendance).
**Conséquences** : interface publique ajoutée (commandes `sync`, `autoriser`, `verifier-deploiement`) ; `type_empreinte` est maintenant renseigné par `sync` (reste `non_renseigne` pour `etl export` seul). À faire avant la première exécution : variable `VOTEAPOL_URL_PUBLIEE`, secrets Cloudflare, deux environnements GitHub (voir `docs/deployment.md`).

---

---

## Décisions en suspens

| Sujet | Options | Critère de décision |
|-------|---------|---------------------|
| *(aucune)* | Le format des votes individuels est tranché (dans `scrutins/<id>.json`, voir la décision du 2026-11-18). | |
