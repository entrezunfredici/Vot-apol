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
    s.add_argument("--dry-run", action="store_true", help="compare sans rien écrire (ALG-07.16)")
    s.add_argument("--journal-dir", default=None)
    s = sub.add_parser("validate")
    s.add_argument("--db", required=True)
    s = sub.add_parser("export")
    s.add_argument("--db", required=True)
    s.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.cmd == "inspect":
        return pipeline.run_inspect(a.zip)
    if a.cmd == "import":
        return pipeline.run_import(a.zip, a.db, a.dry_run, a.journal_dir)
    if a.cmd == "validate":
        return pipeline.run_validate(a.db)
    return pipeline.run_export(a.db, a.out)
