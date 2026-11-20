"""Tests du script de reprise des données publiées (redéploiement du front seul)."""

import functools
import http.server
import importlib.util
import sqlite3
import threading
import zipfile
from pathlib import Path

import pytest

from etl.cli import main
from etl.io.db import appliquer_migrations

RACINE = Path(__file__).parents[2]
FIXTURES = Path(__file__).parent / "fixtures"
NUMEROS = (1, 2, 3, 489, 1017, 1302)

_spec = importlib.util.spec_from_file_location("recuperer", RACINE / "scripts" / "recuperer_donnees_publiees.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)  # type: ignore[union-attr]


@pytest.fixture(scope="module")
def export(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("recup")
    archive = base / "Scrutins.json.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for n in NUMEROS:
            z.write(FIXTURES / f"VTANR5L17V{n}.json", f"json/VTANR5L17V{n}.json")
    db = base / "v.db"
    conn = sqlite3.connect(db)
    appliquer_migrations(conn)
    conn.close()
    main(["import", "--zip", str(archive), "--db", str(db), "--journal-dir", str(base / "j")])
    sortie = base / "out"
    assert main(["export", "--db", str(db), "--out", str(sortie)]) == 0
    return sortie


def servir(dossier: Path):
    """Sert un dossier en HTTP local ; retourne (adresse, arrêt)."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(dossier))
    handler.log_message = lambda *a, **k: None  # type: ignore[attr-defined]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/", srv.shutdown


def test_recupere_et_verifie_les_donnees_publiees(export, tmp_path):
    url, arret = servir(export)
    try:
        n = R.recuperer(url, tmp_path / "copie")
    finally:
        arret()
    fichiers = [p for p in export.rglob("*") if p.is_file()]
    assert n == len(fichiers)
    for p in fichiers:
        assert (tmp_path / "copie" / p.relative_to(export)).read_bytes() == p.read_bytes()


def test_refuse_un_fichier_altere(export, tmp_path):
    publie = tmp_path / "publie"
    publie.mkdir()
    for p in export.rglob("*"):
        if p.is_file():
            cible = publie / p.relative_to(export)
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(p.read_bytes())
    un_scrutin = next((publie / "scrutins").glob("*.json"))
    un_scrutin.write_bytes(un_scrutin.read_bytes().replace(b"pour", b"contre", 1))
    url, arret = servir(publie)
    try:
        with pytest.raises(R.Refus, match="Empreinte"):
            R.recuperer(url, tmp_path / "copie")
    finally:
        arret()


def test_refuse_l_absence_de_publication(tmp_path):
    vide = tmp_path / "vide"
    vide.mkdir()
    url, arret = servir(vide)
    try:
        with pytest.raises(R.Refus, match="404"):
            R.recuperer(url, tmp_path / "copie")
    finally:
        arret()


def test_refuse_une_adresse_non_https(tmp_path):
    with pytest.raises(R.Refus, match="https"):
        R.recuperer("http://exemple.org/data/v1/", tmp_path)
