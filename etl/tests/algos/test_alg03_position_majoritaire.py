"""Tests ALG-03 : cas limites et exemples chiffrés de la fiche."""

import json
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import normaliser_scrutin
from etl.algos.alg03_position_majoritaire import (
    ErreurDonnee,
    calculer_position,
    position_majoritaire_groupe,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.parametrize(
    "p, c, a, position, raison, e, m, absolue",
    [
        (12, 2, 0, "pour", None, 14, 12, True),
        (5, 6, 49, "abstention", None, 60, 49, True),
        (6, 6, 1, "aucune", "egalite", 13, 6, False),
        (0, 0, 0, "aucune", "aucun_vote_exprime", 0, 0, False),
        (3, 2, 2, "pour", None, 7, 3, False),
        (4, 4, 4, "aucune", "egalite", 12, 4, False),
        (1, 0, 0, "pour", None, 1, 1, True),
        (0, 7, 0, "contre", None, 7, 7, True),
        (2, 2, 0, "aucune", "egalite", 4, 2, False),
        (2, 4, 0, "contre", None, 6, 4, True),
        (2, 3, 1, "contre", None, 6, 3, False),  # 2m = E : pas strictement plus de la moitié
    ],
)
def test_ALG_03_cas_de_la_fiche(p, c, a, position, raison, e, m, absolue):
    r = calculer_position(p, c, a, membres=100)
    assert (r.position, r.raison_absence, r.exprimes, r.effectif_majoritaire) == (
        position,
        raison,
        e,
        m,
    )
    assert r.majorite_absolue is absolue
    assert (r.participation_num, r.participation_den) == (e, 100)


def test_ALG_03_exemple_scrutin_2066_la_source_se_trompe():
    r = calculer_position(12, 2, 0, membres=14, position_source="contre")
    assert r.position == "pour" and (r.effectif_majoritaire, r.exprimes) == (12, 14)
    assert r.position_source == "contre"  # conservée pour audit seulement


def test_ALG_03_position_source_n_influence_pas_le_calcul():
    a = calculer_position(3, 2, 2, 10, position_source="contre")
    b = calculer_position(3, 2, 2, 10, position_source=None)
    assert (a.position, a.majorite_absolue) == (b.position, b.majorite_absolue)


@pytest.mark.parametrize(
    "p, c, a",
    [(-1, 0, 0), (0, -1, 0), (0, 0, -1), (None, 0, 0), (0, "1", 0), (0, 0, 1.5), (True, 0, 0)],
)
def test_ALG_03_valeur_invalide_erreur_de_donnee(p, c, a):
    with pytest.raises(ErreurDonnee):
        calculer_position(p, c, a, membres=10)


@pytest.mark.parametrize("n", [1, 2, 3, 489, 1017, 1302])
def test_ALG_03_invariants_sur_les_fixtures_reelles(n):
    doc = json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))
    scrutin = normaliser_scrutin(doc).scrutin
    assert scrutin is not None
    for g in scrutin.groupes:
        r = position_majoritaire_groupe(g)
        assert r.exprimes == g.pour + g.contre + g.abstentions
        assert r.effectif_majoritaire <= r.exprimes
        assert (r.effectif_majoritaire == 0) == (r.exprimes == 0)
        assert (r.position == "aucune") == (r.raison_absence is not None)
        assert r.exprimes <= g.membres  # sinon alerte de réconciliation (ALG-05 R10)
        assert r.participation_den == g.membres
        assert r.position_source == g.position_majoritaire_source


def test_ALG_03_scrutin_1_vrais_groupes():
    doc = json.loads((FIXTURES / "VTANR5L17V1.json").read_text(encoding="utf-8"))
    scrutin = normaliser_scrutin(doc).scrutin
    assert scrutin is not None
    par_membres = {g.membres: position_majoritaire_groupe(g) for g in scrutin.groupes}
    # groupe de 95 membres : 10 non-votants, aucune position exprimée
    assert par_membres[95].raison_absence == "aucun_vote_exprime"
    # groupe de 72 membres : 72 pour
    r = par_membres[72]
    assert (r.position, r.exprimes, r.effectif_majoritaire, r.majorite_absolue) == (
        "pour",
        72,
        72,
        True,
    )
    # groupe de 22 membres : 4 pour exprimés sur 22, à ne jamais présenter sans l'effectif
    r = par_membres[22]
    assert (r.position, r.exprimes, r.participation_den) == ("pour", 4, 22)
