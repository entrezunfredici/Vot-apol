"""ALG-07 : Import idempotent (UPSERT, détection de changement, journal).

Spécification : docs/algorithmes/ALG-07-import-idempotent.md (statut « Validé »).
Aucun SQL ni fichier ici : toute écriture passe par un `Depot` (adaptateur SQLite dans
etl/io/db.py). Le temps est fourni par l'appelant (`horloge`), jamais lu ici.
Chaque bloc de code est précédé de « # ALG-07.k : <résumé> ».
"""

import dataclasses
import hashlib
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any

from ..models import (
    AncienScrutin,
    Depot,
    LotScrutin,
    RapportImport,
    RapportLecture,
    ScrutinRefuse,
)

TAILLE_LOT = 200  # scrutins écrits par transaction (à confirmer par mesure, fiche décision 4)
MAX_CAUSES_RESUME = 20  # causes conservées dans imports.error_summary (ALG-07.15)

# Colonnes de métadonnées exclues de `champs_modifies` (elles changent à chaque réécriture)
_METADONNEES = ("imported_at", "source_hash", "etl_version")


class ErreurBase(Exception):
    """Erreur de base de données (disque plein, contrainte, verrou…) ; `motif` est stable."""

    def __init__(self, motif: str, detail: str = ""):
        super().__init__(f"{motif} : {detail}" if detail else motif)
        self.motif = motif








def calculer_version_etl(sources: Iterable[str]) -> str:
    """`etl_version` calculée : SHA-256 du contenu des modules ALG-02, 04 et 06 (décision 2).

    Les fins de ligne sont normalisées pour que le résultat ne dépende pas du système.
    """
    h = hashlib.sha256()
    for texte in sources:
        h.update(texte.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def classer(ancien: tuple[str, str] | None, source_hash: str, etl_version: str) -> str:
    """ALG-07.6 : nouveau | inchange | modifie | retraite."""
    # ALG-07.6 : aucune ligne -> nouveau ; (hash, version) identiques -> inchange ;
    # hash différent -> modifie ; hash identique et version différente -> retraite
    if ancien is None:
        return "nouveau"
    hash_ancien, version_ancienne = ancien
    if hash_ancien != source_hash:
        return "modifie"
    return "inchange" if version_ancienne == etl_version else "retraite"


def champs_modifies(ancien: AncienScrutin, lot: LotScrutin) -> list[str]:
    """ALG-07.9 : colonnes de scrutins et totaux qui changent, compteurs de groupe, nb de lignes."""
    champs: list[str] = []
    for nom, nouvelle in dataclasses.asdict(lot.scrutin).items():
        if nom not in _METADONNEES and ancien.scrutin.get(nom) != nouvelle:
            champs.append(nom)
    for nom, nouvelle in dataclasses.asdict(lot.totaux).items():
        if nom != "scrutin_id" and ancien.totaux.get(nom) != nouvelle:
            champs.append(nom)
    nouveaux_groupes = {g.rang: dataclasses.asdict(g) for g in lot.groupes}
    for rang in sorted(set(ancien.groupes) | set(nouveaux_groupes)):
        vieux, neuf = ancien.groupes.get(rang), nouveaux_groupes.get(rang)
        if vieux is None or neuf is None:
            champs.append(f"groupes[{rang}]")
            continue
        for nom, valeur in neuf.items():
            if nom != "scrutin_id" and vieux.get(nom) != valeur:
                champs.append(f"groupes[{rang}].{nom}")
    if ancien.nb_votes != len(lot.votes):
        champs.append("votes")
    if ancien.nb_mises_au_point != len(lot.mises_au_point):
        champs.append("mises_au_point")
    return champs


def importer(
    depot: Depot,
    flux: Iterable[LotScrutin | ScrutinRefuse],
    lecture: RapportLecture,
    importe_le: str,
    horloge: Callable[[], datetime],
    version_schema_attendue: int,
    simulation: bool = False,
    taille_lot: int = TAILLE_LOT,
    interruption: Callable[[], bool] = lambda: False,
) -> RapportImport:
    """Importe le flux (ordre des numéros) ; l'unité atomique est un scrutin, le lot en groupe."""
    debut = horloge()
    r = RapportImport(
        archive_sha256=lecture.empreinte_archive,
        type_empreinte=lecture.type_empreinte,
        statut_lecture=lecture.statut,
        fichiers_vus=lecture.entrees_vues,
    )

    def fin(statut: str, motif: str | None = None) -> RapportImport:
        # ALG-07.15 : mise à jour de `imports` (hors simulation) ; le journal fichier est écrit
        # par l'appelant à partir du rapport complet
        r.statut, r.motif_echec = statut, motif
        r.fichiers_ok = r.nouveaux + r.inchanges + len(r.modifies) + len(r.retraites)
        r.fichiers_en_echec = len(r.refuses) + len(lecture.refusees)
        termine = horloge()
        r.duree_secondes = (termine - debut).total_seconds()
        if r.import_id is not None and not simulation:
            try:
                depot.terminer_import(r.import_id, termine.isoformat(), r)
            except ErreurBase as exc:
                r.statut, r.motif_echec = "echoue", exc.motif
        return r

    # ALG-07.1 : schéma de la base différent de celui attendu -> échec, aucune migration implicite
    try:
        version = depot.version_schema()
    except ErreurBase as exc:
        return fin("echoue", exc.motif)
    if version != version_schema_attendue:
        return fin("echoue", f"schema_incompatible : {version}, attendu {version_schema_attendue}")

    # ALG-07.2 : lecture de l'archive en échec -> rien à importer
    if lecture.statut == "echec":
        return fin("echoue", lecture.motif_echec or "lecture_en_echec")

    # ALG-07.3 : ligne `imports` validée immédiatement (trace d'une exécution commencée)
    if not simulation:
        try:
            r.import_id = depot.debut_import(importe_le, lecture.empreinte_archive)
        except ErreurBase as exc:
            return fin("echoue", exc.motif)

    vus: set[str] = set()  # identifiants acceptés ou refusés dans cet import (ALG-07.13)
    etat = {"en_transaction": False, "ecrits": 0}
    en_attente: list[tuple[str, dict[str, Any] | None]] = []  # comptés à la validation du lot
    interrompu = False

    def valider() -> None:
        # ALG-07.11 : validation du lot, puis comptage (un lot annulé n'est jamais compté)
        if etat["en_transaction"] and not simulation:
            depot.valider_lot()
        etat["en_transaction"], etat["ecrits"] = False, 0
        for classe, modif in en_attente:
            if classe == "inchange":
                r.inchanges += 1
            elif classe == "nouveau":
                r.nouveaux += 1
            elif classe == "modifie":
                r.modifies.append(modif or {})
            else:
                r.retraites.append(modif or {})
        en_attente.clear()

    try:
        for item in flux:
            # ALG-07.4 : refusé -> journalisé, rien d'écrit, l'ancienne donnée est conservée
            if isinstance(item, ScrutinRefuse):
                vus.add(item.id)
                r.refuses.append({"id": item.id, "cause": item.cause})
                continue
            lot = item
            sid = lot.scrutin.id
            vus.add(sid)

            if not etat["en_transaction"]:
                if not simulation:
                    depot.debut_lot()  # BEGIN IMMEDIATE : un second import échoue
                etat["en_transaction"] = True

            # ALG-07.5 et 6 : lecture de l'existant et classement
            empreinte = depot.lire_empreinte(sid)
            classe = classer(empreinte, lot.scrutin.source_hash, lot.scrutin.etl_version)

            if classe == "inchange":
                # ALG-07.7 : compter, ne rien écrire (pas même imported_at)
                en_attente.append(("inchange", None))
            else:
                modif: dict[str, Any] | None = None
                if empreinte is not None:
                    # ALG-07.9 : champs modifiés (lecture) puis suppression des lignes enfants
                    modif = {
                        "id": sid,
                        "ancien_hash": empreinte[0],
                        "nouveau_hash": lot.scrutin.source_hash,
                        "champs_modifies": champs_modifies(depot.lire_ancien(sid), lot),
                    }
                    if not simulation:
                        depot.supprimer_enfants(sid)
                if not simulation:
                    # ALG-07.8 : références (sans nom) pour respecter les clés étrangères
                    depot.inserer_references(lot.groupes_vus, lot.deputes_vus)
                    # ALG-07.10 : UPSERT du scrutin puis insertion des lignes enfants
                    depot.ecrire_scrutin(lot)
                en_attente.append((classe, modif))
                etat["ecrits"] += 1

            # ALG-07.12 : interruption demandée -> le scrutin en cours est terminé, lot validé
            if interruption():
                interrompu = True
                break
            # ALG-07.11 : validation tous les `taille_lot` scrutins écrits
            if etat["ecrits"] >= taille_lot:
                valider()
        valider()
    except ErreurBase as exc:
        # ALG-07.11 : erreur de base -> annuler le lot en cours, échec, arrêt
        if etat["en_transaction"] and not simulation:
            try:
                depot.annuler_lot()
            except ErreurBase:
                pass
        return fin("echoue", exc.motif)

    if interrompu:
        return fin("interrompu")

    # ALG-07.13 : scrutins en base mais ni acceptés ni refusés ; jamais supprimés
    try:
        r.absents_de_l_archive = sorted(depot.ids_en_base() - vus)
    except ErreurBase as exc:
        return fin("echoue", exc.motif)

    # ALG-07.14 : statut ; ALG-07.16 : en simulation, mêmes calculs, statut « simulation »
    if simulation:
        return fin("simulation")
    erreurs = r.refuses or lecture.refusees or lecture.statut == "partiel" or r.absents_de_l_archive
    return fin("termine_avec_erreurs" if erreurs else "termine")
