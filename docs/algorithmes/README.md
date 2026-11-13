 

# Spécifications des traitements (algorithmes)

**Règle du projet : aucun traitement n'est codé avant que son algorithme soit écrit, justifié ligne par ligne et validé. Le code suit ensuite cette spécification ligne par ligne.**

## Processus

1. **Spécifier** : rédiger la fiche `ALG-NN` du traitement (gabarit ci-dessous). Chaque étape est numérotée et justifiée.
2. **Valider** : la fiche est relue et acceptée (statut `Validé`) avant tout code.
3. **Coder** : une étape de la fiche = un bloc de code, précédé d'un commentaire `# ALG-NN.k : <résumé>` (même numérotation). Aucune logique sans étape correspondante, aucune étape sans code.
4. **Tester** : chaque cas limite de la fiche a un test nommé `test_ALG_NN_<cas>`. Les exemples chiffrés de la fiche servent de valeurs attendues.
5. **Modifier** : tout changement de comportement commence par la fiche (nouvelle version, historique en bas), puis le code, puis les tests.

Si le code doit s'écarter de la fiche, on s'arrête et on corrige la fiche d'abord, jamais l'inverse.

## Gabarit d'une fiche

```text
# ALG-NN — Titre
Statut : Brouillon | Validé    Version : n    Date : AAAA-MM-JJ

## But
Une phrase : ce que le traitement produit et pourquoi.

## Entrées / Sorties
Champs, types, valeurs possibles, provenance (fichier, champ source).

## Définitions et formules
Symboles, formules mathématiques, avec leur justification.

## Algorithme logique (vue d'ensemble)
Pseudo-code en langage naturel (notations, si/sinon, boucles, formules), avec le numéro [k] de l'étape détaillée correspondante. Le tableau qui suit fait foi.

## Algorithme
| # | Étape (pseudo-code) | Justification |
|---|---------------------|---------------|
| 1 | ...                 | pourquoi cette ligne existe, quel risque elle évite |

## Cas limites et erreurs
| Cas | Comportement attendu | Pourquoi |

## Exemples chiffrés (valeurs vérifiées à la main)
Entrée → sortie attendue, utilisés comme tests.

## Invariants vérifiés
Propriétés qui doivent toujours être vraies (contrôlées par l'ETL ou les tests).

## Sources et constats
Références aux constats de `docs/analyse-donnees-sources.md`, aux décisions de `.agents/DECISIONS.md`.

## Historique
```

## Index des traitements prévus

| ID     | Traitement                                                                                    | Statut                                     |
| ------ | --------------------------------------------------------------------------------------------- | ------------------------------------------ |
| ALG-01 | Lecture sécurisée de l'archive (ZIP/dossier, taille, chemins, empreinte)                    | [Validé](ALG-01-lecture-archive.md)         |
| ALG-02 | Normalisation des valeurs (null / objet / liste, nombres, booléens, dates, positions)        | [Validé](ALG-02-normalisation.md)           |
| ALG-03 | Calcul de la position majoritaire d'un groupe                                                 | [Brouillon](ALG-03-position-majoritaire.md) |
| ALG-04 | Extraction d'un scrutin (totaux, groupes, votes nominatifs) | [Brouillon](ALG-04-extraction-scrutin.md) |
| ALG-05 | Contrôles de réconciliation (totaux, groupes, nominatif) | [Brouillon](ALG-05-reconciliation.md) |
| ALG-06 | Mises au point (rattachement au groupe, position initiale, effectifs corrigés) | [Brouillon](ALG-06-mises-au-point.md) |
| ALG-07 | Import idempotent (UPSERT, détection de changement, journal) | [Brouillon](ALG-07-import-idempotent.md) |
| ALG-08 | Classification des scrutins (catégorie, confiance, « à vérifier ») | [Brouillon](ALG-08-classification.md) |
| ALG-09 | Résolution des noms (référentiels groupes et députés) ; référentiels à inspecter | [Brouillon](ALG-09-resolution-noms.md) |
| ALG-10 | Indicateurs de groupe (participation au vote enregistrée, part de la position majoritaire) et comparaison de deux groupes | [Brouillon](ALG-10-indicateurs-groupe.md) |
| ALG-11 | Export statique (fichiers JSON, déterminisme, limites Cloudflare) | [Brouillon](ALG-11-export-statique.md) |
| ALG-12 | Garde-fou avant déploiement (changement anormal, écarts nouveaux) | [Brouillon](ALG-12-garde-fou-deploiement.md) |
| ALG-13 | Téléchargement de l'archive (URL, statut HTTP, taille, fraîcheur, comparaison d'empreinte) | [Brouillon](ALG-13-telechargement.md) |
| ALG-14 | Vérification indépendante sur fichiers bruts tirés au hasard (garantie 3) | Proposé, à rédiger si accepté |
