"""Interface en ligne de commande : inspect / import / validate / export / sync / autoriser."""

import argparse
from pathlib import Path

from . import config, pipeline


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
    s.add_argument("--manifeste-precedent", default=None, help="manifeste.json de la version publiée")
    s = sub.add_parser("sync", help="télécharger, importer, exporter, vérifier et décider (ALG-12)")
    s.add_argument("--workdir", required=True, help="archives, base, journaux, decision.json")
    s.add_argument("--out", required=True, help="répertoire exporté (artefact à déployer)")
    s.add_argument("--url-publiee", default=config.URL_PUBLIEE, help="racine en ligne des données")
    s.add_argument("--tests-ok", action="store_true", help="tests, lexique et couleurs réussis (G05)")
    s.add_argument("--forcer", action="store_true", help="republication forcée (V08)")
    s.add_argument(
        "--mode-automatique",
        action="store_true",
        help="désactive le mode sûr : sur instruction explicite du responsable seulement",
    )
    s = sub.add_parser("autoriser", help="le déploiement est-il autorisé pour cet artefact ? (ALG-12.8)")
    s.add_argument("--decision", required=True)
    s.add_argument("--data", required=True, help="répertoire exporté à déployer")
    s.add_argument("--approuvee", action="store_true", help="approbation humaine de CETTE décision")
    s = sub.add_parser("verifier-deploiement", help="meta.json en ligne = déployé ? (ALG-12.9)")
    s.add_argument("--url-publiee", required=True)
    s.add_argument("--data", required=True)
    a = p.parse_args(argv)
    if a.cmd == "inspect":
        return pipeline.run_inspect(a.zip)
    if a.cmd == "import":
        return pipeline.run_import(a.zip, a.db, a.dry_run, a.journal_dir)
    if a.cmd == "validate":
        return pipeline.run_validate(a.db)
    if a.cmd == "sync":
        return pipeline.run_sync(
            pipeline.ConfigSync(
                dossier_travail=Path(a.workdir),
                sortie=Path(a.out),
                url_publiee=a.url_publiee,
                tests_ok=a.tests_ok,
                forcer=a.forcer,
                mode_sur=not a.mode_automatique,
            )
        )
    if a.cmd == "autoriser":
        return pipeline.run_autoriser(a.decision, a.data, a.approuvee)
    if a.cmd == "verifier-deploiement":
        return pipeline.run_verifier_deploiement(a.url_publiee, a.data)
    return pipeline.run_export(a.db, a.out, manifeste_precedent=a.manifeste_precedent)
