"""Écriture des fichiers exportés (ALG-11) et du journal d'import (ALG-07.15)."""

import dataclasses
import json
from pathlib import Path

from ..algos.alg07_import_idempotent import RapportImport


def ecrire_journal_import(rapport: RapportImport, dossier: Path | str) -> Path:
    """Écrit le rapport complet dans `import-<id>.json` (`import-sans-id.json` si pas de ligne)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    identifiant = rapport.import_id if rapport.import_id is not None else "sans-id"
    chemin = dossier / f"import-{identifiant}.json"
    chemin.write_text(
        json.dumps(dataclasses.asdict(rapport), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chemin
