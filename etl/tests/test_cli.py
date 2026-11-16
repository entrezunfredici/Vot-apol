import pytest

from etl.cli import main

DOSSIER = "tests/fixtures"


def test_cli_requires_command():
    with pytest.raises(SystemExit):
        main([])


def test_cli_export_pas_encore_implemente():
    with pytest.raises(NotImplementedError):
        main(["export", "--db", "x.sqlite", "--out", "o"])


def test_cli_validate_base_introuvable(tmp_path):
    assert main(["validate", "--db", str(tmp_path / "absente.db")]) == 2
