"""Tests ALG-01 : un test par cas limite et exemple chiffré de la fiche."""

import hashlib
import json
import os
import struct
import warnings
import zipfile
from pathlib import Path

import pytest

from etl.algos.alg01_archive import LimitesLecture
from etl.pipeline import lire_source

FIXTURES = Path(__file__).parents[1] / "fixtures"  # 3 vrais scrutins (n° 1 à 3)
DOSSIER_REEL = Path(__file__).parents[3] / "Scrutins.json"


def _scrutin(n: int) -> bytes:
    return (FIXTURES / f"VTANR5L17V{n}.json").read_bytes()


def _faux(n: int, **surcharges: object) -> bytes:
    """Document minimal valide pour les cas qui testent la mécanique (pas le contenu métier)."""
    scrutin = {"uid": f"VTANR5L17V{n}", "legislature": "17"} | surcharges
    return json.dumps({"scrutin": scrutin}).encode()


def _zip(chemin: Path, entrees: list[tuple[str, bytes]], methode: int = zipfile.ZIP_DEFLATED) -> str:
    with zipfile.ZipFile(chemin, "w", methode) as z:
        for nom, octets in entrees:
            # ZipInfo remplace « \ » par « / » sous Windows : on fixe le nom après coup
            info = zipfile.ZipInfo("x")
            info.filename = nom
            info.compress_type = methode
            z.writestr(info, octets)
    return str(chemin)


def _zip_de_base(tmp_path: Path) -> str:
    return _zip(
        tmp_path / "a.zip",
        [
            ("json/", b""),
            *[(f"json/VTANR5L17V{n}.json", _scrutin(n)) for n in (1, 2, 3)],
            ("json/note.txt", b"x"),
        ],
    )


def test_ALG_01_zip_valide_avec_dossier_et_fichier_hors_motif(tmp_path):
    acceptees, r = lire_source(_zip_de_base(tmp_path))
    assert (r.entrees_vues, r.acceptees, r.ignorees) == (5, 3, 1)
    assert [(e.nom, e.motif) for e in r.refusees] == [("json/note.txt", "hors_motif")]
    assert r.statut == "complet" and r.type_empreinte == "fichier" and r.trous == []
    assert [a.numero for a in acceptees] == [1, 2, 3]
    assert r.acceptees + len(r.refusees) + r.ignorees == r.entrees_vues


def test_ALG_01_empreinte_zip_deterministe_et_egale_au_sha256_du_fichier(tmp_path):
    chemin = _zip_de_base(tmp_path)
    _, r1 = lire_source(chemin)
    _, r2 = lire_source(chemin)
    assert r1.empreinte_archive == r2.empreinte_archive
    assert r1.empreinte_archive == hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def test_ALG_01_empreinte_par_entree_et_octets_bruts(tmp_path):
    acceptees, _ = lire_source(_zip_de_base(tmp_path))
    assert acceptees[0].sha256_fichier == hashlib.sha256(_scrutin(1)).hexdigest()
    assert acceptees[0].octets_bruts == len(_scrutin(1))
    assert acceptees[0].document_json["scrutin"]["uid"] == "VTANR5L17V1"


def test_ALG_01_tri_par_numero_et_non_par_ordre_alphabetique(tmp_path):
    chemin = _zip(tmp_path / "b.zip", [(f"json/VTANR5L17V{n}.json", _faux(n)) for n in (10, 2, 1)])
    acceptees, _ = lire_source(chemin)
    assert [a.numero for a in acceptees] == [1, 2, 10]


def test_ALG_01_source_introuvable(tmp_path):
    acceptees, r = lire_source(str(tmp_path / "absent.zip"))
    assert acceptees == [] and r.statut == "echec" and r.motif_echec == "source_introuvable"


def test_ALG_01_zip_invalide(tmp_path):
    f = tmp_path / "x.zip"
    f.write_bytes(b"ceci n'est pas un zip")
    acceptees, r = lire_source(str(f))
    assert acceptees == [] and r.statut == "echec" and r.motif_echec == "zip_invalide"


def test_ALG_01_zip_tronque(tmp_path):
    chemin = Path(_zip_de_base(tmp_path))
    chemin.write_bytes(chemin.read_bytes()[:-30])
    acceptees, r = lire_source(str(chemin))
    assert acceptees == [] and r.statut == "echec"


@pytest.mark.parametrize(
    "nom",
    ["../x.json", "/etc/x.json", "json\\a.json", "json/../x.json", "C:/x.json", "json/a\x01.json"],
)
def test_ALG_01_nom_dangereux(tmp_path, nom):
    if "\\" in nom and os.sep == "\\":
        pytest.skip("sous Windows, zipfile convertit déjà le antislash en / à la lecture")
    chemin = _zip(tmp_path / "d.zip", [("json/VTANR5L17V1.json", _faux(1)), (nom, b"{}")])
    _, r = lire_source(chemin)
    assert [(e.nom, e.motif) for e in r.refusees] == [(nom, "nom_dangereux")]
    assert r.statut == "complet" and r.avertissements


def test_ALG_01_nom_dangereux_ressemblant_a_un_scrutin_rend_partiel(tmp_path):
    chemin = _zip(
        tmp_path / "d.zip",
        [("json/VTANR5L17V1.json", _faux(1)), ("../VTANR5L17V2.json", _faux(2))],
    )
    _, r = lire_source(chemin)
    assert r.statut == "partiel"


def test_ALG_01_nom_en_double(tmp_path):
    f = tmp_path / "dup.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # zipfile signale lui-même le doublon
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("json/VTANR5L17V5.json", _faux(5))
            z.writestr("json/VTANR5L17V5.json", _faux(5))
    acceptees, r = lire_source(str(f))
    assert acceptees == [] and r.statut == "echec" and r.motif_echec == "nom_en_double"


def test_ALG_01_legislature_inattendue(tmp_path):
    chemin = _zip(
        tmp_path / "l.zip",
        [("json/VTANR5L16V1.json", b"{}"), ("json/VTANR5L17V1.json", _faux(1))],
    )
    _, r = lire_source(chemin)
    assert [(e.nom, e.motif) for e in r.refusees] == [
        ("json/VTANR5L16V1.json", "legislature_inattendue")
    ]
    assert r.statut == "complet"


def test_ALG_01_motif_sensible_a_la_casse_et_zero_initial(tmp_path):
    chemin = _zip(
        tmp_path / "c.zip",
        [
            ("json/vtanr5l17v1.json", b"{}"),
            ("json/VTANR5L17V01.json", b"{}"),
            ("json/VTANR5L017V1.json", b"{}"),
        ],
    )
    _, r = lire_source(chemin)
    assert len(r.refusees) == 3 and {e.motif for e in r.refusees} == {"hors_motif"}


def test_ALG_01_entree_chiffree(tmp_path):
    chemin = Path(
        _zip(
            tmp_path / "e.zip",
            [("json/VTANR5L17V1.json", _faux(1)), ("json/VTANR5L17V2.json", _faux(2))],
        )
    )
    octets = bytearray(chemin.read_bytes())
    # bit « chiffré » (flag_bits & 1) dans l'en-tête central de la seconde entrée
    positions = [i for i in range(len(octets) - 4) if octets[i : i + 4] == b"PK\x01\x02"]
    drapeaux = struct.unpack_from("<H", octets, positions[1] + 8)[0] | 1
    struct.pack_into("<H", octets, positions[1] + 8, drapeaux)
    chemin.write_bytes(bytes(octets))
    _, r = lire_source(str(chemin))
    assert [(e.nom, e.motif) for e in r.refusees] == [
        ("json/VTANR5L17V2.json", "nom_non_supporte")
    ]
    assert r.statut == "partiel"


def test_ALG_01_crc_invalide_entree_refusee_les_autres_lues(tmp_path):
    # entrées stockées sans compression pour pouvoir altérer leurs octets
    chemin = Path(
        _zip(
            tmp_path / "crc.zip",
            [(f"json/VTANR5L17V{n}.json", _scrutin(n)) for n in (1, 2, 3)],
            zipfile.ZIP_STORED,
        )
    )
    octets = bytearray(chemin.read_bytes())
    octets[octets.index(_scrutin(2)) + 100] ^= 0xFF
    chemin.write_bytes(bytes(octets))
    acceptees, r = lire_source(str(chemin))
    assert [a.numero for a in acceptees] == [1, 3]
    assert [(e.nom, e.motif) for e in r.refusees] == [("json/VTANR5L17V2.json", "corrompue")]
    assert r.statut == "partiel" and r.trous == [2]
    assert "numérotation discontinue" in r.avertissements


def test_ALG_01_taille_entree_excessive(tmp_path):
    chemin = _zip(
        tmp_path / "t.zip",
        [("json/VTANR5L17V1.json", _scrutin(1)), ("json/VTANR5L17V2.json", _faux(2))],
    )
    acceptees, r = lire_source(chemin, limites=LimitesLecture(max_octets_entree=1000))
    assert [a.numero for a in acceptees] == [2]
    assert [(e.nom, e.motif) for e in r.refusees] == [("json/VTANR5L17V1.json", "taille")]
    assert r.statut == "partiel"


def test_ALG_01_ratio_de_compression_excessif(tmp_path):
    chemin = _zip(tmp_path / "r.zip", [("json/VTANR5L17V1.json", b" " * 100_000 + _faux(1))])
    _, r = lire_source(chemin)
    assert r.refusees[0].motif == "taille"


def test_ALG_01_trop_d_entrees(tmp_path):
    chemin = _zip(tmp_path / "n.zip", [(f"json/VTANR5L17V{n}.json", _faux(n)) for n in (1, 2, 3)])
    acceptees, r = lire_source(chemin, limites=LimitesLecture(max_entrees=2))
    assert acceptees == [] and r.statut == "echec" and r.motif_echec == "trop_d_entrees"


def test_ALG_01_taille_declaree_totale_excessive(tmp_path):
    chemin = _zip(tmp_path / "s.zip", [("json/VTANR5L17V1.json", _scrutin(1))])
    acceptees, r = lire_source(chemin, limites=LimitesLecture(max_octets_total=100))
    assert acceptees == [] and r.statut == "echec"
    assert r.motif_echec == "taille_declaree_excessive"


@pytest.mark.parametrize(
    "octets, motif",
    [
        (b"\xef\xbb\xbf" + _faux(1), "encodage"),
        (b'{"scrutin": {"uid": "VTANR5L17V1", "x": "\xff"}}', "encodage"),
        (
            b'{"scrutin": {"uid": "VTANR5L17V1", "uid": "VTANR5L17V1", "legislature": "17"}}',
            "json_invalide",
        ),
        (b'{"scrutin": {"uid": "VTANR5L17V1", "legislature": "17", "x": NaN}}', "json_invalide"),
        (b'{"scrutin": {"uid": "VTANR5L17V1", "legislature": "17", "x": Infinity}}', "json_invalide"),
        (b"{pas du json", "json_invalide"),
        (b"[" * 100_000, "json_invalide"),
        (b'{"autre": {}}', "structure"),
        (b'{"scrutin": {}, "autre": 1}', "structure"),
        (b'{"scrutin": []}', "structure"),
        (_faux(1, uid="VTANR5L17V9"), "identite"),
        (_faux(1, legislature="16"), "identite"),
        (_faux(1, legislature=17), "identite"),
    ],
)
def test_ALG_01_contenu_refuse(tmp_path, octets, motif):
    chemin = _zip(
        tmp_path / "k.zip",
        [("json/VTANR5L17V1.json", octets), ("json/VTANR5L17V2.json", _faux(2))],
        zipfile.ZIP_STORED,  # évite que le ratio de compression masque le motif testé
    )
    acceptees, r = lire_source(chemin)
    assert [(e.nom, e.motif) for e in r.refusees] == [("json/VTANR5L17V1.json", motif)]
    assert [a.numero for a in acceptees] == [2]
    assert r.statut == "partiel"


def test_ALG_01_archive_vide(tmp_path):
    _, r = lire_source(_zip(tmp_path / "v.zip", []))
    assert r.statut == "echec" and r.motif_echec == "aucune_entree_acceptee"


def test_ALG_01_trou_de_numerotation_est_un_avertissement(tmp_path):
    chemin = _zip(tmp_path / "t.zip", [(f"json/VTANR5L17V{n}.json", _faux(n)) for n in (1, 2, 4)])
    _, r = lire_source(chemin)
    assert r.trous == [3] and r.statut == "complet"
    assert "numérotation discontinue" in r.avertissements


def test_ALG_01_numerotation_ne_commencant_pas_a_1(tmp_path):
    chemin = _zip(tmp_path / "t.zip", [("json/VTANR5L17V2.json", _faux(2))])
    _, r = lire_source(chemin)
    assert r.trous == [] and "numérotation discontinue" in r.avertissements


def _dossier(racine: Path, numeros: list[int]) -> Path:
    (racine / "json").mkdir(parents=True)
    for n in numeros:
        (racine / "json" / f"VTANR5L17V{n}.json").write_bytes(_faux(n))
    return racine


def test_ALG_01_dossier_manifeste_deterministe(tmp_path):
    d = _dossier(tmp_path / "d", [1, 2, 10])
    acceptees, r = lire_source(str(d))
    assert r.type_source == "dossier" and r.type_empreinte == "manifeste"
    assert r.statut == "complet" and [a.numero for a in acceptees] == [1, 2, 10]
    manifeste = "".join(
        f"json/VTANR5L17V{n}.json\t{hashlib.sha256(_faux(n)).hexdigest()}\n" for n in (1, 10, 2)
    )
    assert r.empreinte_archive == hashlib.sha256(manifeste.encode()).hexdigest()
    assert lire_source(str(d))[1].empreinte_archive == r.empreinte_archive


def test_ALG_01_dossier_sans_sous_dossier_json(tmp_path):
    (tmp_path / "vide").mkdir()
    _, r = lire_source(str(tmp_path / "vide"))
    assert r.statut == "echec"


def test_ALG_01_dossier_lien_symbolique_jamais_lu(tmp_path):
    d = _dossier(tmp_path / "d", [1])
    cible = tmp_path / "hors.json"
    cible.write_bytes(_faux(2))
    try:
        os.symlink(cible, d / "json" / "VTANR5L17V2.json")
        os.symlink(cible, d / "json" / "autre.txt")
    except OSError:
        pytest.skip("création de liens symboliques non autorisée")
    acceptees, r = lire_source(str(d))
    assert [a.numero for a in acceptees] == [1]
    assert [(e.nom, e.motif) for e in r.refusees] == [("json/VTANR5L17V2.json", "lien_symbolique")]
    assert r.liens_symboliques_ignores == 1 and r.statut == "partiel"


def test_ALG_01_aucune_ecriture_sur_le_disque(tmp_path):
    chemin = _zip_de_base(tmp_path)
    avant = sorted(p.name for p in tmp_path.iterdir())
    lire_source(chemin)
    assert sorted(p.name for p in tmp_path.iterdir()) == avant


@pytest.mark.skipif(not (DOSSIER_REEL / "json").is_dir(), reason="données réelles absentes")
def test_ALG_01_dossier_reel_complet():
    acceptees, r = lire_source(str(DOSSIER_REEL))
    assert (r.entrees_vues, r.acceptees, r.refusees) == (8877, 8877, [])
    assert (r.numero_min, r.numero_max, r.trous) == (1, 8877, [])
    assert r.octets_lus == 180_527_979
    assert r.statut == "complet" and r.type_empreinte == "manifeste"
    assert len(acceptees) == 8877
