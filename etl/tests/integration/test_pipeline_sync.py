"""`etl sync` de bout en bout : transport simulé, vraies fixtures, vrai script ALG-14.

Aucun réseau : un faux `Transport` sert l'archive des scrutins, celle des référentiels et, selon le
cas, la version « publiée » (fichiers d'un export précédent).
"""

import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from etl.io.db import appliquer_migrations, lire_references_noms
from etl.models import Parametres
from etl.pipeline import (
    ConfigSync,
    executer_import,
    run_autoriser,
    run_sync,
    run_verifier_deploiement,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
NUMEROS = (1, 2, 3, 489, 1017, 1302)
URL_SCRUTINS = "https://data.assemblee-nationale.fr/test/Scrutins.json.zip"
URL_REFERENTIELS = "https://data.assemblee-nationale.fr/test/AMO30.json.zip"
URL_PUBLIEE = "https://voteapol.example/data/v1/"
PARAMS = Parametres(min_octets=0, attentes=(0.0, 0.0))


class _Reponse:
    def __init__(self, code: int, corps: bytes):
        self.code = code
        self.entetes = {"content-length": str(len(corps))} if code == 200 else {}
        self._corps = corps

    def lire_blocs(self, taille: int):
        if self._corps:
            yield self._corps

    def fermer(self) -> None:
        pass


class _Transport:
    """Sert des octets par adresse ; une adresse inconnue répond 404 (aucune publication)."""

    def __init__(self, contenus: dict[str, bytes] | None = None):
        self.contenus = contenus or {}
        self.pannes: set[str] = set()

    def get(self, url: str, params):
        if url in self.pannes:
            return _Reponse(500, b"")
        corps = self.contenus.get(url)
        return _Reponse(200, corps) if corps is not None else _Reponse(404, b"")


def _zip_scrutins(chemin: Path, numeros=NUMEROS) -> bytes:
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        for n in numeros:
            z.write(FIXTURES / f"VTANR5L17V{n}.json", f"json/VTANR5L17V{n}.json")
    return chemin.read_bytes()


def _zip_referentiels(base: Path, archive: Path) -> bytes:
    """Un organe GP par groupe référencé et un acteur par député, d'après les fixtures."""
    db = base / "ids.db"
    conn = sqlite3.connect(db)
    appliquer_migrations(conn)
    conn.close()
    executer_import(str(archive), str(db), "2026-01-01T00:00:00+00:00", journal_dir=base / "j")
    conn = sqlite3.connect(db)
    groupes, deputes = lire_references_noms(conn)
    conn.close()
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for gid in sorted(g for g in groupes if g != "PO0"):
            organe = {"uid": gid, "codeType": "GP", "libelle": f"Groupe {gid}", "libelleAbrege": gid[2:]}
            z.writestr(f"json/organe/{gid}.json", json.dumps({"organe": organe}))
        for did in sorted(deputes):
            acteur = {
                "uid": {"@xsi:type": "x", "#text": did},
                "etatCivil": {"ident": {"civ": "Mme", "nom": f"Nom{did[2:]}", "prenom": "Prénom"}},
            }
            z.writestr(f"json/acteur/{did}.json", json.dumps({"acteur": acteur}))
    return tampon.getvalue()


@pytest.fixture(scope="module")
def sources(tmp_path_factory) -> dict[str, bytes]:
    base = tmp_path_factory.mktemp("sources")
    complet = _zip_scrutins(base / "complet.zip")
    reduit = _zip_scrutins(base / "reduit.zip", numeros=tuple(n for n in NUMEROS if n != 1302))
    return {
        "complet": complet,
        "reduit": reduit,
        "referentiels": _zip_referentiels(base, base / "complet.zip"),
    }


def _cfg(tmp_path: Path, **kw) -> ConfigSync:
    return ConfigSync(
        dossier_travail=tmp_path / "travail",
        sortie=tmp_path / "data" / "v1",
        url_scrutins=URL_SCRUTINS,
        url_referentiels=URL_REFERENTIELS,
        url_publiee=kw.pop("url_publiee", URL_PUBLIEE),
        tests_ok=kw.pop("tests_ok", True),
        **kw,
    )


def _sync(cfg: ConfigSync, transport: _Transport) -> int:
    return run_sync(cfg, transport, PARAMS, PARAMS, attendre=lambda _: None)


def _decision(cfg: ConfigSync) -> dict:
    return json.loads((cfg.dossier_travail / "decision.json").read_text(encoding="utf-8"))


def _ids(decision: dict) -> set[str]:
    return {r["id"] for r in decision["raisons"]}


def _publie(sortie: Path) -> dict[str, bytes]:
    """Les fichiers d'un export, tels que le site les servirait (adresse publique -> octets)."""
    return {
        URL_PUBLIEE + p.relative_to(sortie).as_posix(): p.read_bytes()
        for p in sortie.rglob("*")
        if p.is_file()
    }


def _transport(sources, archive="complet", publie: dict[str, bytes] | None = None) -> _Transport:
    return _Transport(
        {URL_SCRUTINS: sources[archive], URL_REFERENTIELS: sources["referentiels"], **(publie or {})}
    )


def test_sync_premiere_publication_attend_la_validation(sources, tmp_path):
    cfg = _cfg(tmp_path)
    assert _sync(cfg, _transport(sources)) == 0
    d = _decision(cfg)
    assert d["decision"] == "attente_validation"
    assert {"V00", "V01"} <= _ids(d)  # mode sûr et première publication
    assert not {i for i in _ids(d) if i.startswith("G")}
    # l'artefact et la vérification indépendante existent
    assert (cfg.sortie / "manifeste.json").is_file()
    verification = json.loads((cfg.dossier_travail / "verification.json").read_text("utf-8"))
    assert verification["statut"] == "ok"
    # les noms viennent du référentiel (ALG-09) et le manifeste porte son empreinte
    groupes = json.loads((cfg.sortie / "groupes.json").read_text("utf-8"))["groupes"]
    assert any(g["libelle"] and g["libelle"].startswith("Groupe PO") for g in groupes)
    manifeste = json.loads((cfg.sortie / "manifeste.json").read_text("utf-8"))
    assert "referentiels_sha256" in manifeste["entrees"]


def test_sync_sans_tests_reussis_bloque(sources, tmp_path):
    cfg = _cfg(tmp_path, tests_ok=False)
    assert _sync(cfg, _transport(sources)) == 1
    d = _decision(cfg)
    assert d["decision"] == "bloquer" and "G05" in _ids(d)


def test_sync_telechargement_en_echec_bloque_sans_artefact(sources, tmp_path):
    transport = _transport(sources)
    transport.pannes.add(URL_SCRUTINS)
    cfg = _cfg(tmp_path)
    assert _sync(cfg, transport) == 1
    d = _decision(cfg)
    assert d["decision"] == "bloquer" and "G01" in _ids(d)
    assert not cfg.sortie.exists()


def test_sync_referentiels_indisponibles_bloque(sources, tmp_path):
    transport = _transport(sources)
    transport.pannes.add(URL_REFERENTIELS)
    cfg = _cfg(tmp_path)
    assert _sync(cfg, transport) == 1
    assert "G01" in _ids(_decision(cfg))


def test_sync_etat_publie_illisible_bloque(sources, tmp_path):
    transport = _transport(sources)
    transport.pannes.add(URL_PUBLIEE + "manifeste.json")
    cfg = _cfg(tmp_path)
    assert _sync(cfg, transport) == 1
    d = _decision(cfg)
    assert d["decision"] == "bloquer" and "G01" in _ids(d)  # jamais pris pour une première publication


def test_sync_entrees_identiques_rien_a_faire(sources, tmp_path):
    premier = _cfg(tmp_path / "a")
    assert _sync(premier, _transport(sources)) == 0
    publie = _publie(premier.sortie)
    second = _cfg(tmp_path / "b")
    assert _sync(second, _transport(sources, publie=publie)) == 0
    assert _decision(second)["decision"] == "rien_a_faire"
    assert not second.sortie.exists()  # rien n'est reconstruit


def test_sync_forcer_retraite_malgre_entrees_identiques(sources, tmp_path):
    premier = _cfg(tmp_path / "a")
    _sync(premier, _transport(sources))
    publie = _publie(premier.sortie)
    second = _cfg(tmp_path / "b", forcer=True)
    assert _sync(second, _transport(sources, publie=publie)) == 0
    d = _decision(second)
    assert d["decision"] == "attente_validation" and "V08" in _ids(d)


def test_sync_nouveau_scrutin_publie_sans_validation_hors_mode_sur(sources, tmp_path):
    premier = _cfg(tmp_path / "a")
    assert _sync(premier, _transport(sources, archive="reduit")) == 0
    publie = _publie(premier.sortie)
    second = _cfg(tmp_path / "b", mode_sur=False)
    assert _sync(second, _transport(sources, publie=publie)) == 0
    d = _decision(second)
    assert d["decision"] == "publier", d["raisons"]
    assert d["diff"]["nouveaux"] == 1


def test_sync_nom_modifie_demande_une_validation(sources, tmp_path):
    premier = _cfg(tmp_path / "a")
    _sync(premier, _transport(sources, archive="reduit"))
    publie = _publie(premier.sortie)
    cle = URL_PUBLIEE + "deputes.json"
    deputes = json.loads(publie[cle])
    deputes["deputes"][0]["nom"] = "Ancien nom"
    publie[cle] = json.dumps(deputes).encode("utf-8")
    second = _cfg(tmp_path / "b", mode_sur=False)
    assert _sync(second, _transport(sources, publie=publie)) == 0
    d = _decision(second)
    assert d["decision"] == "attente_validation" and "V06" in _ids(d)


def test_autoriser_exige_la_validation_puis_refuse_un_artefact_altere(sources, tmp_path):
    cfg = _cfg(tmp_path)
    _sync(cfg, _transport(sources))
    decision = cfg.dossier_travail / "decision.json"
    assert run_autoriser(decision, cfg.sortie, approuvee=False) == 1  # attend l'approbation
    assert run_autoriser(decision, cfg.sortie, approuvee=True) == 0
    # un fichier modifié après la décision n'est plus l'artefact examiné
    cible = next((cfg.sortie / "scrutins").glob("*.json"))
    cible.write_bytes(cible.read_bytes() + b" ")
    assert run_autoriser(decision, cfg.sortie, approuvee=True) == 1


def test_autoriser_refuse_une_decision_alteree(sources, tmp_path):
    cfg = _cfg(tmp_path)
    _sync(cfg, _transport(sources))
    decision = cfg.dossier_travail / "decision.json"
    brut = json.loads(decision.read_text("utf-8"))
    brut["decision"] = "publier"  # sans recalculer rapport_sha256
    decision.write_text(json.dumps(brut), encoding="utf-8")
    assert run_autoriser(decision, cfg.sortie, approuvee=True) == 1


def test_autoriser_ne_deploie_jamais_une_decision_bloquee(sources, tmp_path):
    cfg = _cfg(tmp_path, tests_ok=False)
    _sync(cfg, _transport(sources))
    assert _decision(cfg)["decision"] == "bloquer"
    assert run_autoriser(cfg.dossier_travail / "decision.json", cfg.sortie, approuvee=True) == 1


def test_verifier_deploiement_compare_meta_en_ligne(sources, tmp_path):
    cfg = _cfg(tmp_path)
    _sync(cfg, _transport(sources))
    en_ligne = _Transport(_publie(cfg.sortie))
    assert run_verifier_deploiement(URL_PUBLIEE, cfg.sortie, en_ligne, PARAMS) == 0
    # meta.json en ligne d'une autre archive : le déploiement n'est pas confirmé
    meta = json.loads((cfg.sortie / "meta.json").read_text("utf-8"))
    meta["archive_sha256"] = "0" * 64
    en_ligne.contenus[URL_PUBLIEE + "meta.json"] = json.dumps(meta).encode("utf-8")
    assert run_verifier_deploiement(URL_PUBLIEE, cfg.sortie, en_ligne, PARAMS) == 1
    # absent en ligne (404) : non confirmé aussi
    assert run_verifier_deploiement(URL_PUBLIEE, cfg.sortie, _Transport(), PARAMS) == 1
