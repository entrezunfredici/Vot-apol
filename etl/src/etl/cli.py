"""Interface en ligne de commande : inspect / import / validate / export."""

import argparse

from . import pipeline


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="etl")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inspect")
    s.add_argument("--zip", required=True)
    s = sub.add_parser("import")
    s.add_argument("--zip", required=True)
    s.add_argument("--db", required=True)
    s = sub.add_parser("validate")
    s.add_argument("--db", required=True)
    s = sub.add_parser("export")
    s.add_argument("--db", required=True)
    s.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.cmd == "inspect":
        pipeline.run_inspect(a.zip)
    elif a.cmd == "import":
        pipeline.run_import(a.zip, a.db)
    elif a.cmd == "validate":
        pipeline.run_validate(a.db)
    elif a.cmd == "export":
        pipeline.run_export(a.db, a.out)
    return 0
