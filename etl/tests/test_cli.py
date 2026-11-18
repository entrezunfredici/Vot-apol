import pytest

from etl.cli import main

DOSSIER = "tests/fixtures"


def test_cli_requires_command():
    with pytest.raises(SystemExit):
        main([])


def test_cli_export_base_introuvable(tmp_path):
    assert main(["export", "--db", str(tmp_path / "absente.db"), "--out", str(tmp_path / "o")]) == 2


def test_cli_validate_base_introuvable(tmp_path):
    assert main(["validate", "--db", str(tmp_path / "absente.db")]) == 2
