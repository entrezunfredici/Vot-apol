"""Tests ALG-04 : cas limites et exemples chiffrés de la fiche."""

import dataclasses
import json
from collections import Counter
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import normaliser_scrutin
from etl.algos.alg04_extraction_scrutin import ErreurExtraction, extraire_scrutin
from etl.models import GroupeNormalise, LigneCorrection, Votant

FIXTURES = Path(__file__).parents[1] / "fixtures"
DOSSIER_REEL = Path(__file__).parents[3] / "Scrutins.json"
HASH = "a" * 64
DATE = "2026-11-13T10:00:00Z"


def _scrutin(n: int):
    doc = json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))
    r = normaliser_scrutin(doc)
    assert r.scrutin is not None and not r.erreurs
    return r.scrutin


def _lot(s, nom=None):
    return extraire_scrutin(s, nom or f"json/{s.id}.json", HASH, None, DATE, "v1")


@pytest.mark.parametrize("n", [1, 2, 3, 489, 1017, 1302])
def test_ALG_04_fixtures_coherentes(n):
    s = _scrutin(n)
    lot = _lot(s)
    assert (lot.scrutin.id, lot.scrutin.source_hash, lot.scrutin.imported_at) == (s.id, HASH, DATE)
    assert lot.scrutin.etl_version == "v1" and lot.scrutin.source_url is None
    assert lot.scrutin.resultat_code == s.sort_code and lot.scrutin.objet == s.objet_libelle
    assert (lot.totaux.pour, lot.totaux.non_votants) == (s.pour, s.non_votants)
    assert [g.rang for g in lot.groupes] == [g.rang for g in s.groupes]
    assert len(lot.votes) == sum(len(g.votants) for g in s.groupes)
    # tri par clé primaire
    assert [v.depute_id for v in lot.votes] == sorted(v.depute_id for v in lot.votes)
    assert lot.deputes_vus == sorted(set(lot.deputes_vus))
    # chaque identifiant des lignes figure dans les « vus »
    assert {g.groupe_id for g in lot.groupes if g.groupe_id} <= set(lot.groupes_vus)
    assert {v.depute_id for v in lot.votes} | {m.depute_id for m in lot.mises_au_point} == set(
        lot.deputes_vus
    )


def test_ALG_04_comptages_sont_les_lignes_produites():
    s = _scrutin(1)
    lot = _lot(s)
    compte = Counter(v.position for v in lot.votes)
    assert lot.comptages.scrutin == {
        "pour": compte["pour"],
        "contre": 0,
        "abstention": 0,
        "non_votant": compte["non_votant"],
    }
    # scrutin n° 1 : 21 non-votants nominatifs pour 10 au total (voir ALG-05, R07 et R08)
    assert lot.comptages.scrutin["non_votant"] == 21 and lot.totaux.non_votants == 10
    for g in lot.groupes:
        assert sum(lot.comptages.par_groupe[g.rang].values()) == len(
            [v for v in lot.votes if v.groupe_rang == g.rang]
        )


def test_ALG_04_groupes_po0_ont_un_rang_et_pas_d_identifiant():
    lot = _lot(_scrutin(489))
    assert [g.rang for g in lot.groupes] == list(range(1, 13))
    assert all(g.groupe_id is None for g in lot.groupes)
    assert lot.groupes_vus == []
    assert all(v.groupe_id is None and v.groupe_rang in range(1, 13) for v in lot.votes)


def test_ALG_04_vote_non_votant_avec_cause():
    lot = _lot(_scrutin(1017))
    g = next(g for g in lot.groupes if g.groupe_id == "PO845407")
    nv = [v for v in lot.votes if v.groupe_rang == g.rang and v.position == "non_votant"]
    assert len(nv) == 1 and nv[0].cause == "PAN"
    assert all(isinstance(v.par_delegation, int) and v.par_delegation in (0, 1) for v in lot.votes)


def test_ALG_04_groupe_sans_vote_nominatif():
    s = _scrutin(1)
    lot = _lot(s)
    sans = [g for g in s.groupes if not g.votants]
    assert sans, "le scrutin n° 1 a des groupes sans votant"
    for g in sans:
        assert lot.comptages.par_groupe[g.rang] == dict.fromkeys(
            ("pour", "contre", "abstention", "non_votant"), 0
        )


def test_ALG_04_deterministe():
    s = _scrutin(1017)
    assert _lot(s) == _lot(s)


def test_ALG_04_identite_nom_different():
    with pytest.raises(ErreurExtraction) as e:
        _lot(_scrutin(1), nom="json/VTANR5L17V2.json")
    assert e.value.motif == "identite"


def test_ALG_04_importe_le_obligatoire():
    s = _scrutin(1)
    with pytest.raises(ValueError):
        extraire_scrutin(s, f"{s.id}.json", HASH, None, "", "v1")


def _avec_groupes(s, groupes):
    return dataclasses.replace(s, groupes=groupes)


def _votant(acteur: str, position: str = "pour") -> Votant:
    return Votant(acteur, "M1", position, False, None)


def test_ALG_04_depute_en_double_dans_les_votes():
    s = _scrutin(1)
    g0 = dataclasses.replace(s.groupes[0], votants=[_votant("PA1"), _votant("PA1")])
    with pytest.raises(ErreurExtraction) as e:
        _lot(_avec_groupes(s, [g0]))
    assert e.value.motif == "cle_dupliquee"


def test_ALG_04_rang_en_double():
    s = _scrutin(1)
    with pytest.raises(ErreurExtraction) as e:
        _lot(_avec_groupes(s, [s.groupes[0], s.groupes[0]]))
    assert e.value.motif == "cle_dupliquee"


def test_ALG_04_mises_au_point_et_dysfonctionnements_reunis():
    s = _scrutin(1)
    mp = LigneCorrection("PA9", "M9", "pour", True, "mise_au_point")
    dy = LigneCorrection("PA8", "M8", "contre", False, "dysfonctionnement")
    lot = _lot(dataclasses.replace(s, mises_au_point=[mp], dysfonctionnements=[dy]))
    assert [(m.depute_id, m.origine, m.par_delegation) for m in lot.mises_au_point] == [
        ("PA8", "dysfonctionnement", 0),
        ("PA9", "mise_au_point", 1),
    ]
    assert all(
        m.groupe_rang is None and m.groupe_id is None and m.position_initiale is None
        for m in lot.mises_au_point
    )
    assert {"PA8", "PA9"} <= set(lot.deputes_vus)
    # même député dans les deux listes : clé dupliquée
    dy2 = LigneCorrection("PA9", "M9", "contre", False, "dysfonctionnement")
    with pytest.raises(ErreurExtraction):
        _lot(dataclasses.replace(s, mises_au_point=[mp], dysfonctionnements=[dy2]))


def test_ALG_04_scrutin_sans_mise_au_point():
    assert _lot(_scrutin(1)).mises_au_point == []


def test_ALG_04_groupe_normalise_minimal():
    s = _scrutin(1)
    g = GroupeNormalise(1, None, 5, 0, 0, 0, 0, "pour", 0, [])
    lot = _lot(_avec_groupes(s, [g]))
    assert lot.votes == [] and lot.groupes_vus == []


@pytest.mark.skipif(not DOSSIER_REEL.exists(), reason="archive réelle absente")
def test_ALG_04_archive_complete_chiffres_de_la_fiche():
    from etl.pipeline import lire_source

    acceptees, rapport = lire_source(str(DOSSIER_REEL))
    assert rapport.statut == "complet" and len(acceptees) == 8877
    nb_groupes = nb_po0 = nb_mises = nb_dys = 0
    positions: Counter = Counter()
    for a in acceptees:
        r = normaliser_scrutin(a.document_json)
        assert r.scrutin is not None, a.nom
        lot = extraire_scrutin(r.scrutin, a.nom, a.sha256_fichier, None, DATE, "v1")
        nb_groupes += len(lot.groupes)
        nb_po0 += sum(g.groupe_id is None for g in lot.groupes)
        nb_mises += sum(m.origine == "mise_au_point" for m in lot.mises_au_point)
        nb_dys += sum(m.origine == "dysfonctionnement" for m in lot.mises_au_point)
        positions.update(v.position for v in lot.votes)
    assert (nb_groupes, nb_po0) == (106_524, 146)
    assert (nb_mises, nb_dys) == (3243, 163)
    assert dict(positions) == {
        "pour": 580_652,
        "contre": 643_533,
        "abstention": 75_754,
        "non_votant": 24_039,
    }
