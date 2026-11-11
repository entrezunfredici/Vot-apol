"""Orchestration : télécharger → lire → normaliser → extraire → réconcilier → importer → exporter.

Seul module (avec cli.py) autorisé à relier algos/ et io/.
"""

import os

from .algos.alg01_archive import (
    LIMITES_PAR_DEFAUT,
    ErreurSource,
    LimitesLecture,
    SourceArchive,
    lire_archive,
)
from .io.dossier import SourceDossier
from .io.zipfile import SourceZip
from .models import EntreeAcceptee, RapportLecture


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


def run_inspect(zip_path: str) -> None:
    raise NotImplementedError("en attente de ALG-01/02/04 validés")


def run_import(zip_path: str, db_path: str) -> None:
    raise NotImplementedError("en attente de ALG-07 validé")


def run_validate(db_path: str) -> None:
    raise NotImplementedError("en attente de ALG-05 validé")


def run_export(db_path: str, out_dir: str) -> None:
    raise NotImplementedError("en attente de ALG-11 validé")
