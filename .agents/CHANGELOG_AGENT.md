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

