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

## Décisions en suspens

| Sujet | Options | Critère de décision |
|-------|---------|---------------------|
| Bibliothèque de recherche côté navigateur | MiniSearch (index chargé en mémoire) / Pagefind (index fragmenté, chargé à la demande) | Poids de l'index pour 8 900 scrutins sur mobile ; mesure après la phase A |
| Format des votes individuels | Dans `scrutins/<id>.json` / fichier voisin chargé à la demande | Taille moyenne d'un scrutin (environ 577 votants) ; limite de 20 000 fichiers |
| Licence du code | à définir | |
