"""ALG-12 : Garde-fou avant déploiement (changement anormal, écarts nouveaux).

Spécification : docs/algorithmes/ALG-12-garde-fou-deploiement.md (statut « Validé », version 2).
Fonction pure : la décision ne dépend que des rapports reçus (ni réseau, ni horloge, ni disque).
Un blocage n'est jamais levé par une validation humaine ; rien n'est déployé sans que la décision
l'autorise. Chaque bloc de code est précédé de « # ALG-12.k : <résumé> ».
"""

import hashlib
from typing import Any

from ..models import DecisionPublication, EntreesDecision, ParametresDecision
from .alg11_export_statique import empreinte_entrees, serialiser



def _sha256(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


_IMPORT_BLOQUANT_SAUF = ("termine",)  # tout autre statut (echoue, interrompu, …) bloque
_RECONCILIATION_ADMISE = ("ok", "ecarts_connus", "ecarts_informatifs")
_AVERTISSEMENTS_FRAICHEUR = ("archive_ancienne", "fraicheur_inconnue")


def doit_traiter(
    entrees_courantes: dict[str, Any], manifeste_publie: dict[str, Any] | None, forcer: bool
) -> bool:
    """ALG-12.1 : faut-il traiter ? Faux seulement si **toutes** les entrées sont identiques.

    `entrees_courantes` : archive, version des algorithmes de transformation, empreintes des
    référentiels, version des règles de classification (`manifeste.json`, clé `entrees`). Une
    archive inchangée ne suffit pas : une correction d'algorithme ou un nouveau référentiel peut
    changer les données publiées. La comparaison se fait avec la version **publiée**, jamais avec le
    dernier import : si un déploiement a échoué, l'exécution suivante doit retenter.
    """
    if forcer or manifeste_publie is None:
        return True
    return manifeste_publie.get("empreinte_entrees") != empreinte_entrees(entrees_courantes)


def _raison(identifiant: str, detail: str = "") -> dict[str, str]:
    return {"id": identifiant, "detail": detail}


def _regles_bloquantes(e: EntreesDecision) -> list[dict[str, str]]:
    """ALG-12.2 : G01 à G06, toutes évaluées pour que le rapport dise tout d'un coup."""
    raisons = []
    # G01 : téléchargement échoué, ou lecture « echec » / « partiel »
    if e.telechargement is not None and e.telechargement.statut == "echec":
        raisons.append(_raison("G01", f"téléchargement : {e.telechargement.cause_echec}"))
    if e.lecture.statut in ("echec", "partiel"):
        raisons.append(_raison("G01", f"lecture : {e.lecture.statut}"))
    # G02 : import non terminé normalement (echoue, interrompu, termine_avec_erreurs, simulation…)
    if e.importation.statut not in _IMPORT_BLOQUANT_SAUF:
        raisons.append(_raison("G02", f"import : {e.importation.statut}"))
    # G03 : écart de réconciliation nouveau (ou statut inconnu : on ne devine pas)
    if e.reconciliation.statut not in _RECONCILIATION_ADMISE:
        raisons.append(_raison("G03", f"réconciliation : {e.reconciliation.statut}"))
    # G04 : export en échec
    if e.export.statut != "ok":
        raisons.append(_raison("G04", f"export : {e.export.cause_echec or e.export.statut}"))
    # G05 : tests, lexique contrôlé, couleurs
    if not e.tests_ok:
        raisons.append(_raison("G05", "tests en échec"))
    # G06 : vérification indépendante (ALG-14) en échec ou absente
    if e.verification != "ok":
        raisons.append(
            _raison("G06", "vérification indépendante non exécutée" if e.verification is None
                    else f"vérification indépendante : {e.verification}")
        )  # fmt: skip
    return raisons


def _regles_validation(e: EntreesDecision, p: ParametresDecision) -> list[dict[str, str]]:
    """ALG-12.4 : V00 à V08, toutes relevées."""
    raisons = []
    diff = e.diff or {}
    nb_chiffres = diff.get("nombre_modifies_chiffres", 0)
    nb_autres = diff.get("nombre_modifies_autres", 0)
    nb_supprimes = diff.get("nombre_supprimes", 0)
    if e.mode_sur:
        raisons.append(_raison("V00", "mode sûr actif"))
    if e.manifeste_precedent is None:
        raisons.append(_raison("V01", "première publication"))
    if nb_supprimes or e.importation.absents_de_l_archive:
        raisons.append(
            _raison("V02", f"{nb_supprimes} supprimé(s), "
                    f"{len(e.importation.absents_de_l_archive)} absent(s) de l'archive")
        )  # fmt: skip
    if nb_chiffres:
        raisons.append(_raison("V03", f"{nb_chiffres} scrutin(s) dont un chiffre officiel a changé"))
    if nb_autres + nb_chiffres > p.seuil_modifies:
        raisons.append(_raison("V04", f"{nb_autres + nb_chiffres} scrutins modifiés (seuil {p.seuil_modifies})"))
    nouveaux = diff.get("nouveaux", 0)
    if nouveaux > p.seuil_nouveaux:
        raisons.append(_raison("V05", f"{nouveaux} nouveaux scrutins (seuil {p.seuil_nouveaux})"))
    if e.noms_modifies:
        raisons.append(_raison("V06", f"{len(e.noms_modifies)} nom(s) modifié(s)"))
    if (
        e.nombre_groupes_precedent is not None
        and e.export.nombre_groupes != e.nombre_groupes_precedent
    ):
        raisons.append(
            _raison("V07", f"{e.export.nombre_groupes} groupes au lieu de {e.nombre_groupes_precedent}")
        )
    if e.forcer:
        raisons.append(_raison("V08", "republication forcée"))
    return raisons


def _avertissements(e: EntreesDecision) -> list[dict[str, str]]:
    """ALG-12.6 : A01 à A03, joints aux raisons sans effet sur la décision."""
    raisons = []
    if e.telechargement is not None:
        fraicheur = [a for a in e.telechargement.avertissements if a in _AVERTISSEMENTS_FRAICHEUR]
        if fraicheur:
            raisons.append(_raison("A01", ", ".join(fraicheur)))
    if (
        e.indetermines_courant is not None
        and e.indetermines_precedent is not None
        and e.indetermines_courant > e.indetermines_precedent
    ):
        raisons.append(_raison("A02", f"{e.indetermines_precedent} → {e.indetermines_courant} indéterminé(s)"))
    if e.export.avertissements:
        raisons.append(_raison("A03", "; ".join(e.export.avertissements)))
    return raisons


def decider(
    entrees: EntreesDecision, parametres: ParametresDecision = ParametresDecision()
) -> DecisionPublication:
    """Décide : `rien_a_faire`, `publier`, `attente_validation` ou `bloquer`, avec ses raisons."""
    e = entrees
    donnees = str(e.manifeste_courant.get("donnees_sha256", ""))
    empreinte = str(e.manifeste_courant.get("empreinte_entrees", ""))

    def conclure(decision: str, raisons: list[dict[str, str]]) -> DecisionPublication:
        # ALG-12.7 : empreinte du contenu de la décision, qui la relie à un état précis
        contenu = {
            "decision": decision,
            "raisons": raisons,
            "diff": e.diff,
            "donnees_sha256": donnees,
            "empreinte_entrees": empreinte,
        }
        return DecisionPublication(
            decision, tuple(raisons), e.diff, donnees, empreinte, _sha256(serialiser(contenu))
        )

    # ALG-12.1 : rien n'a changé depuis la version publiée (toutes les entrées, pas l'archive seule)
    if (
        not e.forcer
        and e.manifeste_precedent is not None
        and e.manifeste_precedent.get("empreinte_entrees") == empreinte
        and empreinte
    ):
        return conclure("rien_a_faire", [])

    # ALG-12.2 : un échec de contrôle ne se discute pas : toutes les raisons, puis `bloquer`
    bloquantes = _regles_bloquantes(e)
    if bloquantes:
        return conclure("bloquer", bloquantes + _avertissements(e))

    # ALG-12.4 et 5 : un changement anormal, ou le mode sûr, attend une validation humaine
    validation = _regles_validation(e, parametres)
    decision = "attente_validation" if validation else "publier"

    # ALG-12.6 : les avertissements sont joints sans effet sur la décision
    return conclure(decision, validation + _avertissements(e))


def serialiser_decision(decision: DecisionPublication) -> bytes:
    """`decision.json` (ALG-12.7) : sérialisation canonique, sans secret ni heure."""
    return serialiser(
        {
            "decision": decision.decision,
            "raisons": list(decision.raisons),
            "diff": decision.diff,
            "donnees_sha256": decision.donnees_sha256,
            "empreinte_entrees": decision.empreinte_entrees,
            "rapport_sha256": decision.rapport_sha256,
        }
    )


def deploiement_autorise(
    decision: DecisionPublication, approuvee: bool, rapport_sha256_artefact: str
) -> bool:
    """ALG-12.8 : le déploiement ne publie que l'artefact dont l'empreinte correspond à la décision.

    `publier` autorise ; `attente_validation` n'autorise qu'après approbation humaine de **cette**
    décision ; `bloquer` et `rien_a_faire` n'autorisent jamais, quelle que soit l'approbation.
    """
    if decision.rapport_sha256 != rapport_sha256_artefact:
        return False
    if decision.decision == "publier":
        return True
    return decision.decision == "attente_validation" and approuvee


def verifier_deploiement(
    meta_en_ligne: dict[str, Any] | None, archive_sha256: str, nombre_scrutins: int
) -> list[str]:
    """ALG-12.9 : relit `meta.json` en ligne ; liste vide = déploiement confirmé.

    On ne suppose pas que le déploiement a réussi : en cas de différence la version précédente
    reste disponible (restauration).
    """
    if not isinstance(meta_en_ligne, dict):
        return ["meta.json en ligne illisible"]
    erreurs = []
    if meta_en_ligne.get("archive_sha256") != archive_sha256:
        erreurs.append("archive_sha256 en ligne différent de celui déployé")
    if meta_en_ligne.get("nombre_scrutins") != nombre_scrutins:
        erreurs.append("nombre de scrutins en ligne différent de celui déployé")
    return erreurs
