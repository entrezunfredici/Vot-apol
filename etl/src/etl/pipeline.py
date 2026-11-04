"""Orchestration : télécharger → lire → normaliser → extraire → réconcilier → importer → exporter.

Seul module (avec cli.py) autorisé à relier algos/ et io/.
"""


def run_inspect(zip_path: str) -> None:
    raise NotImplementedError("en attente de ALG-01/02/04 validés")


def run_import(zip_path: str, db_path: str) -> None:
    raise NotImplementedError("en attente de ALG-07 validé")


def run_validate(db_path: str) -> None:
    raise NotImplementedError("en attente de ALG-05 validé")


def run_export(db_path: str, out_dir: str) -> None:
    raise NotImplementedError("en attente de ALG-11 validé")
