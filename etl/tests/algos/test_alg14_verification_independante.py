"""Tests ALG-14 : script indépendant, détection de chaque type de dérive, échantillon reproductible."""

import ast
import importlib.util
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from etl.cli import main
from etl.io.db import appliquer_migrations

RACINE = Path(__file__).parents[3]
SCRIPT = RACINE / "scripts" / "verifier_echantillon.py"
FIXTURES = Path(__file__).parents[1] / "fixtures"
NUMEROS = (1, 2, 3, 489, 1017, 1302)

_spec = importlib.util.spec_from_file_location("verifier_echantillon", SCRIPT)
verifier_echantillon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verifier_echantillon)  # type: ignore[union-attr]
V = verifier_echantillon


@pytest.fixture(scope="module")
def archive_et_export(tmp_path_factory):
    """Archive ZIP des six scrutins réels, importée puis exportée par le pipeline."""
    base = tmp_path_factory.mktemp("alg14")
    archive = base / "Scrutins.json.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for n in NUMEROS:
            z.write(FIXTURES / f"VTANR5L17V{n}.json", f"json/VTANR5L17V{n}.json")
    db = base / "v.db"
    conn = sqlite3.connect(db)
    appliquer_migrations(conn)
    conn.close()
    main(["import", "--zip", str(archive), "--db", str(db), "--journal-dir", str(base / "j")])
    export = base / "out"
    assert main(["export", "--db", str(db), "--out", str(export)]) == 0
    return archive, export


@pytest.fixture
def export_modifiable(archive_et_export, tmp_path):
    """Copie de l'export, que les tests peuvent altérer sans effet sur les autres."""
    archive, export = archive_et_export
    copie = tmp_path / "out"
    for p in export.rglob("*"):
        if p.is_file():
            cible = copie / p.relative_to(export)
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(p.read_bytes())
    return archive, copie


def _modifier(export: Path, ident: str, fonction) -> None:
    chemin = export / "scrutins" / f"{ident}.json"
    doc = json.loads(chemin.read_text(encoding="utf-8"))
    fonction(doc)
    chemin.write_text(json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")


def _champs(rapport):
    return {(e["scrutin_id"], e["champ"]) for e in rapport["ecarts"]}


# --- conformité -------------------------------------------------------------------------------------------------


def test_ALG_14_export_fidele_a_la_source(archive_et_export):
    archive, export = archive_et_export
    r = V.verifier(archive, export)
    assert (r["statut"], r["ecarts"]) == ("ok", [])
    assert r["nb_verifies"] == 6 and r["nombre_scrutins_archive"] == 6 and r["nb_champs_compares"] > 100


def test_ALG_14_scrutin_1_ecart_de_la_source_reproduit_tel_quel(archive_et_export):
    """21 non-votants nominatifs pour 10 au total : on vérifie la fidélité, pas la cohérence."""
    archive, export = archive_et_export
    brut = V.extraire_brut(zipfile.ZipFile(archive).read("json/VTANR5L17V1.json"))
    assert brut["totaux"]["non_votants"] == 10
    assert sum(1 for v in brut["votes"] if v[2] == "non_votant") == 21
    assert V.verifier(archive, export, taille=1)["statut"] == "ok"  # n° 1 est toujours tiré


def test_ALG_14_dossier_extrait_accepte_comme_archive(archive_et_export, tmp_path):
    archive, export = archive_et_export
    dossier = tmp_path / "extrait"
    zipfile.ZipFile(archive).extractall(dossier)
    r = V.verifier(dossier, export)
    assert r["statut"] == "ok" and r["nb_verifies"] == 6  # sans empreinte d'archive : pas de contrôle de cet champ


def test_ALG_14_extraction_independante_des_variantes_xml():
    brut = V.extraire_brut(zipfile.ZipFile(archive_fixture()).read("json/VTANR5L17V489.json"))
    assert len(brut["groupes"]) == 12 and all(g["groupe_id"] is None for g in brut["groupes"])
    assert [g["rang"] for g in brut["groupes"]] == list(range(1, 13))
    brut = V.extraire_brut(zipfile.ZipFile(archive_fixture()).read("json/VTANR5L17V1017.json"))
    cause = [v for v in brut["votes"] if v[2] == "non_votant"]
    assert cause and all(v[4] in ("MG", "PSE", "PAN") for v in cause)
    assert all(v[4] is None for v in brut["votes"] if v[2] != "non_votant")


_ARCHIVE_FIXTURE: list[Path] = []


def archive_fixture() -> Path:
    if not _ARCHIVE_FIXTURE:
        import tempfile

        chemin = Path(tempfile.mkdtemp()) / "a.zip"
        with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
            for n in NUMEROS:
                z.write(FIXTURES / f"VTANR5L17V{n}.json", f"json/VTANR5L17V{n}.json")
        _ARCHIVE_FIXTURE.append(chemin)
    return _ARCHIVE_FIXTURE[0]


# --- détection de chaque dérive -------------------------------------------------------------------------------


def test_ALG_14_un_pour_modifie_dans_l_export(export_modifiable):
    archive, export = export_modifiable
    _modifier(export, "VTANR5L17V2", lambda d: d["totaux"].__setitem__("pour", d["totaux"]["pour"] + 1))
    r = V.verifier(archive, export)
    assert r["statut"] == "echec" and ("VTANR5L17V2", "totaux.pour") in _champs(r)
    assert all(e["attendu_source"] != e["obtenu_export"] for e in r["ecarts"])


@pytest.mark.parametrize(
    "champ, modification",
    [
        ("date", lambda d: d.__setitem__("date", "1999-01-01")),
        ("titre", lambda d: d.__setitem__("titre", d["titre"] + " ")),
        ("resultat", lambda d: d.__setitem__("resultat", "autre")),
        ("type_vote.code", lambda d: d["type_vote"].__setitem__("code", "XXX")),
        ("numero", lambda d: d.__setitem__("numero", 999)),
        ("source.sha256", lambda d: d["source"].__setitem__("sha256", "0" * 64)),
        ("source.archive_sha256", lambda d: d["source"].__setitem__("archive_sha256", "0" * 64)),
        ("source.lien_officiel", lambda d: d["source"].__setitem__("lien_officiel", "https://exemple.fr/")),
        ("totaux.non_votants", lambda d: d["totaux"].__setitem__("non_votants", 99)),
        ("totaux.nombre_votants", lambda d: d["totaux"].__setitem__("nombre_votants", 0)),
        ("groupes[1].pour", lambda d: next(g for g in d["groupes"] if g["rang"] == 1).__setitem__("pour", 12345)),
        ("groupes[1].membres", lambda d: next(g for g in d["groupes"] if g["rang"] == 1).__setitem__("membres", 1)),
        ("groupes[1].groupe_id", lambda d: next(g for g in d["groupes"] if g["rang"] == 1).__setitem__("groupe_id", "PO1")),
        ("votes", lambda d: d["votes"].pop()),
        ("votes", lambda d: d["votes"][0].__setitem__(3, 1 - d["votes"][0][3])),  # drapeau de délégation
        ("votes", lambda d: d["votes"][0].__setitem__(0, "PA-inconnu")),
        ("votes", lambda d: d["votes"][0].__setitem__(2, "contre" if d["votes"][0][2] != "contre" else "pour")),
        ("votes.nombre.non_votant", lambda d: [v.__setitem__(2, "pour") for v in d["votes"] if v[2] == "non_votant"]),
    ],
)
def test_ALG_14_chaque_derive_est_detectee(export_modifiable, champ, modification):
    archive, export = export_modifiable
    _modifier(export, "VTANR5L17V1017", modification)
    r = V.verifier(archive, export)
    assert r["statut"] == "echec"
    assert ("VTANR5L17V1017", champ) in _champs(r), _champs(r)


def test_ALG_14_cause_d_un_non_votant_modifiee(export_modifiable):
    archive, export = export_modifiable

    def changer(d):
        v = next(v for v in d["votes"] if v[2] == "non_votant")
        v[4] = "MG" if v[4] != "MG" else "PSE"

    _modifier(export, "VTANR5L17V1017", changer)
    assert ("VTANR5L17V1017", "votes") in _champs(V.verifier(archive, export))


def test_ALG_14_fichier_absent_en_trop_et_meta_incoherent(export_modifiable):
    archive, export = export_modifiable
    (export / "scrutins" / "VTANR5L17V3.json").unlink()
    (export / "scrutins" / "VTANR5L17V99999.json").write_text("{}", encoding="utf-8")
    meta = json.loads((export / "meta.json").read_text(encoding="utf-8"))
    meta["nombre_scrutins"] = 7
    (export / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    r = V.verifier(archive, export)
    champs = _champs(r)
    assert ("VTANR5L17V3", "fichier") in champs and ("VTANR5L17V99999", "fichier") in champs
    assert (None, "meta.nombre_scrutins") in champs and r["statut"] == "echec"


def test_ALG_14_fichier_publie_illisible(export_modifiable):
    archive, export = export_modifiable
    (export / "scrutins" / "VTANR5L17V2.json").write_text("{pas du json", encoding="utf-8")
    r = V.verifier(archive, export)
    assert ("VTANR5L17V2", "lecture") in _champs(r) and r["statut"] == "echec"


# --- entrées illisibles : jamais « ok » sur un contrôle vide ----------------------------------------------------


def test_ALG_14_entrees_illisibles(archive_et_export, tmp_path):
    archive, export = archive_et_export
    with pytest.raises(V.ErreurEntree):
        V.verifier(tmp_path / "absente.zip", export)
    with pytest.raises(V.ErreurEntree):
        V.verifier(archive, tmp_path / "absent")
    faux = tmp_path / "faux.zip"
    faux.write_bytes(b"pas un zip")
    with pytest.raises(V.ErreurEntree):
        V.verifier(faux, export)
    vide = tmp_path / "vide.zip"
    zipfile.ZipFile(vide, "w").close()
    with pytest.raises(V.ErreurEntree):
        V.verifier(vide, export)
    assert V.main(["--archive", str(tmp_path / "absente.zip"), "--export", str(export)]) == 2


def test_ALG_14_export_sans_meta_illisible(archive_et_export, tmp_path):
    archive, _export = archive_et_export
    copie = tmp_path / "out"
    (copie / "scrutins").mkdir(parents=True)
    with pytest.raises(V.ErreurEntree):
        V.verifier(archive, copie)


# --- échantillon ------------------------------------------------------------------------------------------------


def test_ALG_14_echantillon_reproductible_obligatoires_et_recents():
    ids = [f"VTANR5L17V{n}" for n in range(1, 2001)]
    a = V.tirer_echantillon(ids, "ab" * 32)
    assert a == V.tirer_echantillon(list(reversed(ids)), "ab" * 32)  # indépendant de l'ordre d'entrée
    assert len(a) == 200 and a == sorted(a, key=V.numero)
    assert set(V.IDS_OBLIGATOIRES) <= set(a)  # les quatre cas particuliers sont toujours testés
    assert {f"VTANR5L17V{n}" for n in range(1981, 2001)} <= set(a)  # les 20 plus récents
    assert V.tirer_echantillon(ids, "cd" * 32) != a  # une autre archive, un autre échantillon
    assert len(set(V.tirer_echantillon(ids, "ab" * 32, 50))) == 50


def test_ALG_14_echantillon_plus_grand_que_l_archive_verifie_tout():
    ids = [f"VTANR5L17V{n}" for n in range(1, 31)]
    assert V.tirer_echantillon(ids, "ab" * 32, 200) == sorted(ids, key=V.numero)
    # obligatoires absents de l'archive : ignorés sans erreur
    assert "VTANR5L17V489" not in V.tirer_echantillon(ids, "ab" * 32, 5)


def test_ALG_14_deterministe_meme_archive_meme_rapport(archive_et_export):
    archive, export = archive_et_export
    assert V.verifier(archive, export) == V.verifier(archive, export)
    a = V.verifier(archive, export)["graine"]
    assert a == V.sha256_fichier(archive)  # graine par défaut = SHA-256 de l'archive


def test_ALG_14_cli_rapport_et_code_de_sortie(archive_et_export, export_modifiable, tmp_path, capsys):
    archive, export = archive_et_export
    sortie = tmp_path / "verification.json"
    assert V.main(["--archive", str(archive), "--export", str(export), "--sortie", str(sortie)]) == 0
    assert json.loads(sortie.read_text(encoding="utf-8"))["statut"] == "ok"
    assert "vérification : ok" in capsys.readouterr().out
    _, copie = export_modifiable
    _modifier(copie, "VTANR5L17V2", lambda d: d.__setitem__("date", "1999-01-01"))
    assert V.main(["--archive", str(archive), "--export", str(copie)]) == 1
    assert "écart" in capsys.readouterr().out


# --- indépendance -----------------------------------------------------------------------------------------------


def test_ALG_14_le_script_n_importe_rien_du_pipeline_ni_hors_bibliotheque_standard():
    arbre = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    modules = set()
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            modules |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            modules.add((n.module or "").split(".")[0])
    assert "etl" not in modules
    import sys

    assert modules <= set(sys.stdlib_module_names), modules - set(sys.stdlib_module_names)
