# AGENT.md — Directives pour agents IA

> Fichier universel pour le projet Voteapol.  
> Complété par `CONVENTIONS.md` (stack et règles) et `DECISIONS.md` (décisions techniques).

---

## 1. En début de session

Avant toute chose, lis dans cet ordre :
1. `AGENT.md` — ce fichier
2. `CONVENTIONS.md` — stack, structure, nommage, règles de neutralité
3. `CHANGELOG_AGENT.md` — état actuel du code, ce qui a déjà été fait
4. `DECISIONS.md` — pourquoi le code est comme il est
5. `Voteapol_Cahier_Technique_Claude_Code.md` — cahier des charges (schéma, ETL, API, critères d'acceptation)
6. La demande courante

`CHANGELOG_AGENT.md` est ta mémoire de session — il te dit où en est le projet sans que tu aies à inférer depuis le code.

---

## 2. Comportement général

### Avant de coder

- Lis `CONVENTIONS.md` avant toute implémentation.
- Si une information manque, **pose une question avant de coder** — ne fais pas d'hypothèse silencieuse.
- **Ne suppose aucune structure de données non vérifiée.** Inspecte des fichiers réels de l'archive avant de figer un parseur ou un schéma.
- **N'invente jamais un résultat parlementaire**, un nom de groupe ou de député. Une donnée non résolue s'affiche comme telle (« libellé non résolu »).
- Si la tâche modifie une interface publique (format d'un fichier de données, schéma de base, commande `etl`), **signale-le** et attends validation.
- Demande confirmation avant tout déploiement, dépense ou changement majeur d'architecture.

### Audit avant implémentation

Avant de coder, systématiquement :

1. **Identifier les fichiers concernés** : modules ETL, migrations, export JSON, composants Vue, tests.
2. **Auditer l'état réel du code** : ce qui existe et s'utilise tel quel, ce qui doit être étendu, ce qui n'existe pas encore et est dans ton périmètre.
3. **Signaler les écarts** si l'état du code ne correspond pas à ce que la demande suppose — ne comble pas silencieusement.
4. **Attendre validation** si un écart bloque.

> Résumé : **lis le code existant avant d'écrire une ligne, adapte-toi à ce qui est là.**

### Spécification avant code (obligatoire)

- Aucun traitement n'est codé avant que sa fiche `docs/algorithmes/ALG-NN-*.md` soit rédigée, justifiée ligne par ligne et **validée** par l'utilisateur.
- Le code suit la fiche **ligne par ligne** : un commentaire `# ALG-NN.k` par étape, aucune logique hors fiche, aucune étape sans code.
- Les cas limites et exemples chiffrés de la fiche deviennent des tests `test_ALG_NN_<cas>`.
- Si le code doit s'écarter de la fiche : s'arrêter, corriger la fiche (nouvelle version), faire valider, puis coder. Jamais l'inverse.
- Processus détaillé et gabarit : `docs/algorithmes/README.md`.

### Pendant le codage

- Travaille **un module à la fois**.
- Ne refactore pas hors du périmètre de la demande.
- N'ajoute pas de dépendance sans la signaler et la justifier (voir `CONVENTIONS.md`).
- Si tu détectes un problème dans un module adjacent, laisse un commentaire `TODO:` plutôt que de le corriger silencieusement.

### En cas d'ambiguïté

Priorité : exactitude et traçabilité des données > neutralité d'affichage > architecture > conventions > performance > concision.  
Si deux approches sont valides, choisis la plus simple et documente le choix dans `DECISIONS.md`.

---

## 3. Standards de code

### Documentation

- **Python** : docstring (une phrase + arguments/retours/exceptions si non évidents) sur toute fonction publique, annotations de type partout.
- **TypeScript** : TSDoc sur les fonctions exportées ; types explicites aux frontières (forme des fichiers JSON chargés, props de composants).

### Commentaires de décision

Pour tout choix non trivial :

```text
# CHOIX: [approche retenue] plutôt que [alternative écartée]
# RAISON: [justification courte]
```

### Gestion d'erreurs

- Ne jamais avaler une exception (`except: pass`, `catch {}`).
- ETL : une entrée invalide est **journalisée avec son identifiant de fichier et la cause**, comptée dans le rapport d'import, et ne fait pas échouer silencieusement le lot. Une erreur systémique (ZIP corrompu, schéma illisible) interrompt l'import.
- ETL : ne jamais remplacer des données valides par des données partielles sans journaliser l'opération.
- Front : un fichier de données absent ou invalide (404, JSON malformé) affiche l'état d'erreur avec nouvelle tentative, jamais une page vide.
- Messages destinés à l'utilisateur et messages d'API en français.

### Nommage

Suit `CONVENTIONS.md` — nommage descriptif > nommage court en cas de doute.

---

## 4. Tests

- Chaque module livré inclut ses tests : `etl/tests/` (pytest, y compris la validation des schémas d'export) et `web/` (Vitest).
- Ils couvrent le cas nominal, les cas limites et les erreurs attendues. Les cas imposés par le cahier (§5.3 : un seul votant, groupe en objet unique, champs `null`, réimport idempotent, fichier corrompu…) sont obligatoires.
- Les tests de l'ETL utilisent des **fixtures extraites de vrais scrutins** ; ne jamais fabriquer de faux résultats pour qu'un test passe.
- Format des noms : `[fonction] - [contexte] - [résultat attendu]`

```text
✓ parse_scrutin - groupe unique en objet - le normalise en liste
✓ import_archive - même ZIP deux fois - aucune ligne dupliquée
✓ export_scrutin - scrutin sans groupe résolu - écrit « libellé non résolu »
```

---

## 5. Ce que l'agent NE doit PAS faire

| Interdit | Raison |
|----------|--------|
| Modifier une interface publique (format des fichiers de données, schéma, commande `etl`) sans validation | Casse les modules dépendants |
| Refactorer hors périmètre | Introduit du risque non planifié |
| Ajouter une dépendance sans signalement | Vérifier d'abord `CONVENTIONS.md` |
| Supprimer des tests existants | Même s'ils échouent — les signaler |
| Interpréter, noter ou classer des partis, des groupes ou des députés | Hors périmètre et contraire à la neutralité du projet |
| Présenter une absence comme une abstention | Fausse l'information |
| Déduire le groupe d'un député de son affiliation actuelle | L'affiliation du scrutin fait foi |
| Concaténer des valeurs dans du SQL (ETL) | Requêtes paramétrées uniquement |
| Ajouter une API, un Worker applicatif ou D1 | Décision d'architecture : site statique (voir `DECISIONS.md`) |
| Versionner ZIP, bases SQLite, secrets ou données générées | Voir `.gitignore` |
| Déployer ou écrire sur Cloudflare sans confirmation explicite | Coût et irréversibilité |
| Laisser du code commenté | Utiliser `TODO:` avec contexte, ou supprimer |

---

## 6. Livraison

Checklist avant de considérer une tâche terminée :

- [ ] Fiche `ALG-NN` validée avant le code ; code, commentaires `ALG-NN.k` et tests en correspondance avec la fiche
- [ ] Code conforme à l'architecture de `CONVENTIONS.md`
- [ ] Docstrings / TSDoc sur les fonctions publiques
- [ ] Commentaires de décision sur les choix non triviaux
- [ ] Tests (nominal + limites + erreurs) **réellement exécutés**, résultat vérifié
- [ ] Linters et vérification de types sans erreur (`ruff`, `mypy`, `eslint`, `vue-tsc`)
- [ ] Pour l'ETL : import exécuté sur les données réelles, bilan chiffré (fichiers vus / OK / en échec)
- [ ] `DECISIONS.md` mis à jour si un choix structurant a été fait
- [ ] `CHANGELOG_AGENT.md` mis à jour

---

## 7. Format de rapport de fin de tâche

```text
## [Titre]

**Ce qui a été fait** : ...
**Choix techniques** : ...
**Ce qui n'est PAS couvert** : ...
**Points d'attention** : ... (dette, risques, dépendances fragiles)
**Vérifié** : commandes exécutées et résultats
```

Si un test échoue ou une étape a été sautée, le dire explicitement avec la sortie.

---

## 8. Conventions Git

- Commits : `[ADD]` (nouveau), `[IMP]` (amélioration), `[REF]` (refacto), `[FIX]` (bug), `[DOC]` (documentation)
- Branches : `feature/<nom>` ou `fix/<nom>`, créées depuis `main` (à revoir si une branche `dev` est introduite)
- Ne commit et ne push que sur demande de l'utilisateur
