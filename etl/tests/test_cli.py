import pytest

from etl.cli import main


def test_cli_requires_command():
    with pytest.raises(SystemExit):
        main([])


def test_cli_commands_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        main(["validate", "--db", "x.sqlite"])
