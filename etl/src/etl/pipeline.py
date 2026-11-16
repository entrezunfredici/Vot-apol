"""Orchestration : télécharger → lire → normaliser → extraire → réconcilier → importer → exporter.

Seul module (avec cli.py) autorisé à relier algos/ et io/.
"""

import json
import os
import signal
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from .algos import alg02_normalisation, alg04_extraction_scrutin, alg06_mises_au_point
from .algos.alg01_archive import (
    LIMITES_PAR_DEFAUT,
    ErreurSource,
    LimitesLecture,
    SourceArchive,
    lire_archive,
)
from .algos.alg02_normalisation import normaliser_scrutin
from .algos.alg04_extraction_scrutin import ErreurExtraction, extraire_scrutin
from .algos.alg05_reconciliation import (
    ErreurEcartsConnus,
    RapportReconciliation,
    ScrutinAControler,
    charger_ecarts_connus,
    controler,
    depuis_lot,
)
from .algos.alg06_mises_au_point import rattacher
from .algos.alg07_import_idempotent import (
    ErreurBase,
    RapportImport,
    calculer_version_etl,
    importer,
)
from .config import DATA_DIR, SOURCE_URL
from .io.db import DepotSqlite, lire_pour_controle, version_schema_attendue
from .io.dossier import SourceDossier
from .io.fs import ecrire_journal_import
from .io.zipfile import SourceZip
from .models import EntreeAcceptee, LotScrutin, RapportLecture, ScrutinRefuse

ECARTS_CONNUS = Path(__file__).parents[2] / "ecarts_connus.json"
JOURNAUX = DATA_DIR / "journaux"


def lire_source(
    chemin: str, legislature: int = 17, limites: LimitesLecture = LIMITES_PAR_DEFAUT
) -> tuple[list[EntreeAcceptee], RapportLecture]:
    """Ouvre un ZIP ou un dossier et applique ALG-01 (étape ALG-01.1 : choix de la source)."""
    # ALG-01.1 : source absente ou ni fichier ni dossier -> échec explicite
    source: SourceArchive
    try:
        if os.path.isdir(chemin):
            source = SourceDossier.ouvrir(chemin)
        elif os.path.isfile(chemin):
            source = SourceZip.ouvrir(chemin)
        else:
            return [], RapportLecture(motif_echec="source_introuvable")
    except ErreurSource as exc:
        return [], RapportLecture(motif_echec=exc.motif)
    try:
        return lire_archive(source, legislature, limites)
    finally:
        source.fermer()


def version_etl() -> str:
    """ALG-07, décision 2 : empreinte du contenu des modules ALG-02, ALG-04 et ALG-06."""
    modules = (alg02_normalisation, alg04_extraction_scrutin, alg06_mises_au_point)
    return calculer_version_etl(Path(m.__file__).read_text(encoding="utf-8") for m in modules)


def preparer_flux(
    entrees: list[EntreeAcceptee],
    importe_le: str,
    version: str,
    a_controler: list[ScrutinAControler],
) -> Iterator[LotScrutin | ScrutinRefuse]:
    """ALG-02 -> ALG-04 -> ALG-06 (A) pour chaque entrée, dans l'ordre des numéros.

    Une erreur à l'une des étapes donne un `ScrutinRefuse` (rien ne sera écrit pour ce scrutin).
    Les chiffres du niveau « lot » d'ALG-05 sont collectés dans `a_controler`.
    """
    for entree in sorted(entrees, key=lambda e: e.numero):
        identifiant = entree.nom.rsplit("/", 1)[-1].removesuffix(".json")
        resultat = normaliser_scrutin(entree.document_json)
        if resultat.scrutin is None:
            codes = sorted({e.code for e in resultat.erreurs})
            yield ScrutinRefuse(identifiant, "normalisation : " + ", ".join(codes))
            continue
        try:
            lot = extraire_scrutin(
                resultat.scrutin,
                entree.nom,
                entree.sha256_fichier,
                SOURCE_URL or None,
                importe_le,
                version,
            )
        except ErreurExtraction as exc:
            yield ScrutinRefuse(identifiant, f"extraction : {exc.motif}")
            continue
        a_controler.append(depuis_lot(resultat.scrutin, lot))
        yield rattacher(lot)


def _resume(rapport: RapportImport) -> dict:
    return {
        "statut": rapport.statut,
        "motif_echec": rapport.motif_echec,
        "import_id": rapport.import_id,
        "statut_lecture": rapport.statut_lecture,
        "nouveaux": rapport.nouveaux,
        "inchanges": rapport.inchanges,
        "modifies": len(rapport.modifies),
        "retraites": len(rapport.retraites),
        "refuses": len(rapport.refuses),
        "absents_de_l_archive": len(rapport.absents_de_l_archive),
        "duree_secondes": round(rapport.duree_secondes, 2),
    }


def _afficher_reconciliation(rapport: RapportReconciliation) -> None:
    nb_ecarts = sum(c["nb_ecarts"] for c in rapport.controles.values())
    print(
        f"reconciliation ({rapport.niveau}) : {rapport.statut}, "
        f"{rapport.scrutins_controles} scrutins, {nb_ecarts} écarts"
    )
    for e in rapport.ecarts[:20]:
        connu = " (connu)" if e.connu else ""
        print(
            f"  {e.controle} {e.scrutin_id} rang={e.groupe_rang} {e.detail or ''} "
            f"attendu={e.attendu} obtenu={e.obtenu}{connu}"
        )
    for a in rapport.avertissements:
        print(f"  avertissement : {a}")


def run_inspect(zip_path: str) -> int:
    """Lit l'archive (ALG-01) et affiche le rapport de lecture, sans rien écrire."""
    _, lecture = lire_source(zip_path)
    rapport = {**lecture.__dict__, "refusees": len(lecture.refusees)}
    print(json.dumps(rapport, indent=2, ensure_ascii=False, default=str))
    return 0 if lecture.statut == "complet" else 1


def _horloge() -> datetime:
    return datetime.now(UTC)  # seul endroit où l'heure est lue ; les algos la reçoivent en argument


def run_import(
    zip_path: str,
    db_path: str,
    dry_run: bool = False,
    journal_dir: str | Path | None = None,
    ecarts_connus: str | Path = ECARTS_CONNUS,
) -> int:
    """ALG-01 -> 02 -> 04 -> 06 -> 07, puis ALG-05 (niveau lot, puis niveau base après l'import)."""
    importe_le = _horloge().isoformat()
    try:
        connus = charger_ecarts_connus(ecarts_connus)
    except ErreurEcartsConnus as exc:
        print(f"écarts connus illisibles : {exc}")
        return 2

    entrees, lecture = lire_source(zip_path)
    a_controler: list[ScrutinAControler] = []
    flux = preparer_flux(entrees, importe_le, version_etl(), a_controler)

    try:
        depot = DepotSqlite(db_path, lecture_seule=dry_run)
    except ErreurBase as exc:
        print(f"base inutilisable : {exc.motif}")
        return 1

    # ALG-07.12 : un Ctrl-C termine le scrutin en cours et valide le lot
    demande = {"stop": False}
    ancien = signal.signal(signal.SIGINT, lambda *_: demande.update(stop=True))
    try:
        rapport = importer(
            depot,
            flux,
            lecture,
            importe_le,
            _horloge,
            version_schema_attendue(),
            simulation=dry_run,
            interruption=lambda: demande["stop"],
        )
    finally:
        depot.fermer()
        signal.signal(signal.SIGINT, ancien)

    chemin = ecrire_journal_import(rapport, journal_dir or JOURNAUX)
    print(json.dumps(_resume(rapport), indent=2, ensure_ascii=False))
    print(f"journal : {chemin}")

    # ALG-05 niveau lot : contrôles sur les lots construits (informatif, ne bloque pas l'import)
    _afficher_reconciliation(controler(a_controler, connus, "lot"))

    code = 0 if rapport.statut in ("termine", "simulation") else 1
    if rapport.statut in ("termine", "termine_avec_erreurs") and not dry_run:
        # ALG-05 niveau base : après l'import, relu par requêtes
        attendu = (
            rapport.nouveaux
            + rapport.inchanges
            + len(rapport.modifies)
            + len(rapport.retraites)
            + len(rapport.absents_de_l_archive)
        )
        code = max(code, _valider_base(db_path, connus, attendu))
    return code


def _valider_base(db_path: str | Path, connus, nb_attendu: int | None) -> int:
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        rapport = controler(lire_pour_controle(conn), connus, "base", nb_attendu)
    finally:
        conn.close()
    _afficher_reconciliation(rapport)
    return 1 if rapport.statut == "ecarts_nouveaux" else 0


def run_validate(db_path: str, ecarts_connus: str | Path = ECARTS_CONNUS) -> int:
    """ALG-05 niveau base : code de sortie 1 si des écarts nouveaux bloquants existent."""
    if not Path(db_path).is_file():
        print(f"base introuvable : {db_path}")
        return 2
    try:
        connus = charger_ecarts_connus(ecarts_connus)
    except ErreurEcartsConnus as exc:
        print(f"écarts connus illisibles : {exc}")
        return 2
    return _valider_base(db_path, connus, None)


def run_export(db_path: str, out_dir: str) -> int:
    raise NotImplementedError("en attente de ALG-11 validé")
