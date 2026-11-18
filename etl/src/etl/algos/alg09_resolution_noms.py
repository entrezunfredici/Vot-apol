"""ALG-09 : Résolution des noms (référentiels des groupes et des députés).

Spécification : docs/algorithmes/ALG-09-resolution-noms.md (statut « Validé », version 3).
Fonction pure : pas de disque, pas de réseau, pas de SQL (voir etl/io/db.py pour l'écriture).
Seul l'appariement par identifiant exact est permis : jamais par nom, sigle ou ressemblance.
Chaque bloc de code est précédé de « # ALG-09.k : <résumé> ».
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from ..models import EntreeAcceptee, NomDepute, NomGroupe, RapportResolution, ResolutionNoms

_ID_ORGANE = re.compile(r"PO[1-9][0-9]*")
_ID_ACTEUR = re.compile(r"PA[1-9][0-9]*")


def _texte(valeur: Any) -> str | None:
    """ALG-09.2 : NFC, bords retirés, chaîne vide -> None ; le texte intérieur n'est jamais réécrit.

    Une valeur qui n'est pas une chaîne (objet XML vide, nombre…) vaut None : on ne devine rien.
    """
    if not isinstance(valeur, str):
        return None
    t = unicodedata.normalize("NFC", valeur).strip()
    return t or None


def indexer_referentiel(
    entrees: Iterable[EntreeAcceptee],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], list[str]]:
    """ALG-09.2 à 4 : organes et acteurs par identifiant, avec les doublons conservés.

    Renvoie (organes, acteurs, avertissements). Un identifiant présent plusieurs fois reste en
    liste : le contenu éventuellement différent le rendra ambigu (ALG-09.4).
    """
    organes: dict[str, list[dict[str, Any]]] = {}
    acteurs: dict[str, list[dict[str, Any]]] = {}
    avertissements: list[str] = []
    for e in entrees:
        doc = e.document_json
        if "organe" in doc:
            o = doc["organe"]
            uid = o.get("uid")
            # ALG-09.2 : identifiant d'organe valide
            if not (isinstance(uid, str) and _ID_ORGANE.fullmatch(uid)):
                avertissements.append(f"organe_identifiant_invalide : {e.nom}")
                continue
            organes.setdefault(uid, []).append(o)
        elif "acteur" in doc:
            a = doc["acteur"]
            uid = a.get("uid")
            uid = uid.get("#text") if isinstance(uid, dict) else uid
            # ALG-09.3 : identifiant d'acteur valide
            if not (isinstance(uid, str) and _ID_ACTEUR.fullmatch(uid)):
                avertissements.append(f"acteur_identifiant_invalide : {e.nom}")
                continue
            acteurs.setdefault(uid, []).append(a)
    return organes, acteurs, avertissements


def resoudre_noms(
    entrees: Iterable[EntreeAcceptee],
    groupes_references: Mapping[str, int],
    deputes_references: Mapping[str, int],
    anciens_groupes: Mapping[str, tuple[str | None, str | None]] | None = None,
    anciens_deputes: Mapping[str, tuple[str | None, str | None, str | None]] | None = None,
) -> ResolutionNoms:
    """Associe un nom à chaque identifiant référencé, ou le déclare non résolu.

    `groupes_references` et `deputes_references` : identifiant -> nombre d'occurrences (scrutins
    pour un groupe, lignes de vote pour un député), utilisés dans le rapport (ALG-09.9).
    `anciens_*` : noms déjà en base, pour signaler un changement de nom (ALG-09.8).
    """
    anciens_groupes = anciens_groupes or {}
    anciens_deputes = anciens_deputes or {}
    rapport = RapportResolution()
    organes, acteurs, rapport.avertissements = indexer_referentiel(entrees)

    groupes: list[NomGroupe] = []
    deputes: list[NomDepute] = []

    # ALG-09.5 et 11 : seuls les groupes référencés sont traités ; PO0 n'est jamais un organe
    refs_g = {g: n for g, n in groupes_references.items() if g is not None and g != "PO0"}
    rapport.groupes_references = len(refs_g)

    for gid in sorted(refs_g):
        occurrences = refs_g[gid]

        def non_resolu_g(raison: str, gid=gid, occurrences=occurrences) -> None:
            rapport.groupes_non_resolus.append(
                {"id": gid, "raison": raison, "occurrences": occurrences}
            )

        candidats = organes.get(gid, [])
        # ALG-09.9 : absent du référentiel
        if not candidats:
            non_resolu_g("absent")
            continue
        # ALG-09.4 : plusieurs contenus différents pour un même identifiant
        if len(candidats) > 1 and any(c != candidats[0] for c in candidats[1:]):
            non_resolu_g("identifiant_ambigu")
            continue
        if len(candidats) > 1:
            rapport.avertissements.append(f"organe_en_double_identique : {gid}")
        organe = candidats[0]
        # ALG-09.6 : un organe qui n'est pas un groupe parlementaire n'est jamais présenté comme tel
        if organe.get("codeType") != "GP":
            rapport.avertissements.append(f"organe_pas_un_groupe : {gid}")
            non_resolu_g("organe_pas_un_groupe")
            continue
        # ALG-09.2 : libellé et sigle normalisés ; libellé vide -> non résolu
        libelle = _texte(organe.get("libelle"))
        sigle = _texte(organe.get("libelleAbrege"))
        if libelle is None:
            non_resolu_g("libelle_vide")
            continue
        # ALG-09.8 : un nom différent de celui déjà en base est signalé, jamais appliqué en silence
        ancien = anciens_groupes.get(gid)
        if ancien is not None and ancien[0] is not None and ancien[0] != libelle:
            rapport.noms_modifies.append({"id": gid, "ancien": ancien[0], "nouveau": libelle})
        groupes.append(NomGroupe(gid, libelle, sigle))
        rapport.groupes_resolus += 1

    # ALG-09.5 : seuls les députés référencés (votes et mises au point)
    rapport.deputes_references = len(deputes_references)
    for did in sorted(deputes_references):
        occurrences = deputes_references[did]

        def non_resolu_d(raison: str, did=did, occurrences=occurrences) -> None:
            rapport.deputes_non_resolus.append(
                {"id": did, "raison": raison, "occurrences": occurrences}
            )

        candidats = acteurs.get(did, [])
        if not candidats:
            non_resolu_d("absent")
            continue
        if len(candidats) > 1 and any(c != candidats[0] for c in candidats[1:]):
            non_resolu_d("identifiant_ambigu")
            continue
        ident = (candidats[0].get("etatCivil") or {}).get("ident") or {}
        # ALG-09.3 : nom, prénom et civilité normalisés ; un nom vide rend le député non résolu
        nom = _texte(ident.get("nom"))
        if nom is None:
            non_resolu_d("nom_vide")
            continue
        prenom = _texte(ident.get("prenom"))
        civilite = _texte(ident.get("civ"))
        ancien_d = anciens_deputes.get(did)
        if ancien_d is not None and (ancien_d[0] is not None) and (ancien_d[0], ancien_d[1]) != (
            nom,
            prenom,
        ):
            rapport.noms_modifies.append(
                {
                    "id": did,
                    "ancien": f"{ancien_d[1] or ''} {ancien_d[0]}".strip(),
                    "nouveau": f"{prenom or ''} {nom}".strip(),
                }
            )
        deputes.append(NomDepute(did, nom, prenom, civilite))
        rapport.deputes_resolus += 1

    # ALG-09.12 : le rapport est retourné en entier (journalisé par l'appelant)
    return ResolutionNoms(groupes, deputes, rapport)
