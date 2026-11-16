"""Import de bout en bout sur les fixtures (dossier), puis rejeu, dry-run et validate."""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from etl.cli import main
from etl.io.db import appliquer_migrations

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def archive(tmp_path):
    dossier = tmp_path / "archive"
    (dossier / "json").mkdir(parents=True)
    for f in FIXTURES.glob("VTANR5L17V*.json"):
        shutil.copy(f, dossier / "json" / f.name)
    return dossier


def _nb(db, table):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_import_rejeu_dry_run_et_validate(archive, tmp_path, capsys):
    db = tmp_path / "v.db"
    conn = sqlite3.connect(db)
    appliquer_migrations(conn)
    conn.close()
    journaux = tmp_path / "j"
    args = ["import", "--zip", str(archive), "--db", str(db), "--journal-dir", str(journaux)]

    main(args)
    premier = json.loads((journaux / "import-1.json").read_text(encoding="utf-8"))
    assert premier["nouveaux"] == 6 and premier["statut"] in ("termine", "termine_avec_erreurs")
    n = _nb(db, "scrutin_individual_votes")

    main(args)
    second = json.loads((journaux / "import-2.json").read_text(encoding="utf-8"))
    assert (second["nouveaux"], second["inchanges"]) == (0, 6)
    assert _nb(db, "scrutin_individual_votes") == n

    assert main([*args, "--dry-run"]) in (0, 1)
    assert _nb(db, "imports") == 2  # la simulation n'écrit pas

    main(["validate", "--db", str(db)])
    assert "reconciliation (base)" in capsys.readouterr().out
