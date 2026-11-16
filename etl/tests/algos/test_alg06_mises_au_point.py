"""Tests ALG-06 : cas limites et exemples chiffrés de la fiche (cas construits)."""

import pytest

from etl.algos.alg03_position_majoritaire import ErreurDonnee
from etl.algos.alg06_mises_au_point import corriger_effectifs, rattacher
from etl.models import (
    Comptages,
    LigneGroupe,
    LigneMiseAuPoint,
    LigneScrutin,
    LigneTotaux,
    LigneVote,
    LotScrutin,
)


def _lot(groupe, votes, mises, groupe_id="PO1"):
    """Lot minimal : un groupe de rang 1 (p, c, a) ; votes = [(depute, position)]."""
    p, c, a = groupe
    scrutin = LigneScrutin(
        "S1", 1, 17, "2024-01-01", "t", "o", "SPS", "x", "adopte", None, "h", "t", "v"
    )
    return LotScrutin(
        scrutin=scrutin,
        totaux=LigneTotaux("S1", p, c, a, 0, p + c + a, p + c + a),
        groupes=[LigneGroupe("S1", 1, groupe_id, p + c + a + 5, p, c, a, 0, "pour")],
        votes=[LigneVote("S1", d, 1, groupe_id, "M" + d, pos, 0, None) for d, pos in votes],
        mises_au_point=[LigneMiseAuPoint("S1", d, origine, decl, 0) for d, decl, origine in mises],
        groupes_vus=[],
        deputes_vus=[],
        comptages=Comptages({}, {}),
    )


def _corriger(groupe, votes, mises, groupe_id="PO1"):
    return corriger_effectifs(rattacher(_lot(groupe, votes, mises, groupe_id)))


@pytest.mark.parametrize(
    "groupe, initiale, declaree, corrige, officielle, corrigee, change",
    [
        ((5, 5, 0), "contre", "pour", (6, 4, 0), "aucune", "pour", True),
        ((12, 2, 0), "contre", "pour", (13, 1, 0), "pour", "pour", False),
        ((3, 2, 0), "pour", "non_votant_volontaire", (2, 2, 0), "pour", "aucune", True),
        ((3, 2, 2), "non_votant", "contre", (3, 3, 2), "pour", "aucune", True),
        ((1, 0, 0), "pour", "contre", (0, 1, 0), "pour", "contre", True),
    ],
)
def test_ALG_06_exemples_de_la_fiche(
    groupe, initiale, declaree, corrige, officielle, corrigee, change
):
    p, c, a = groupe
    votes = [(f"p{i}", "pour") for i in range(p)] + [(f"c{i}", "contre") for i in range(c)]
    votes += [(f"a{i}", "abstention") for i in range(a)] + [("x", initiale)]
    # le député concerné est l'un des votants (ou un non-votant en plus)
    cible = {"pour": "p0", "contre": "c0", "non_votant": "x"}[initiale]
    votes = [v for v in votes if v[0] != "x"] if initiale != "non_votant" else votes
    (corr,) = _corriger(groupe, votes, [(cible, declaree, "mise_au_point")])
    assert (corr.pour_corrige, corr.contre_corrige, corr.abstentions_corrigees) == corrige
    assert (corr.position_officielle, corr.position_corrigee) == (officielle, corrigee)
    assert corr.change_position_majoritaire is change
    assert corr.nb_mises_au_point == 1


def test_ALG_06_sans_effet_aucune_correction():
    lot = rattacher(_lot((4, 0, 0), [("p0", "pour")], [("p0", "pour", "mise_au_point")]))
    (m,) = lot.mises_au_point
    assert (m.statut_rattachement, m.effet) == ("rattachee", "sans_effet")
    assert corriger_effectifs(lot) == []


def test_ALG_06_introuvable_reste_sans_groupe():
    lot = rattacher(_lot((4, 0, 0), [("p0", "pour")], [("zz", "contre", "mise_au_point")]))
    (m,) = lot.mises_au_point
    assert (m.statut_rattachement, m.effet) == ("introuvable", None)
    assert (m.groupe_rang, m.groupe_id, m.position_initiale) == (None, None, None)
    assert corriger_effectifs(lot) == []


def test_ALG_06_dysfonctionnement_rattache_jamais_applique():
    lot = rattacher(_lot((3, 2, 0), [("p0", "pour")], [("p0", "contre", "dysfonctionnement")]))
    (m,) = lot.mises_au_point
    assert (m.groupe_rang, m.groupe_id, m.position_initiale) == (1, "PO1", "pour")
    assert m.effet == "modifie_position"
    assert corriger_effectifs(lot) == []


def test_ALG_06_groupe_non_identifie_aucune_correction():
    lot = rattacher(_lot((3, 2, 0), [("p0", "pour")], [("p0", "contre", "mise_au_point")], None))
    (m,) = lot.mises_au_point
    assert (m.statut_rattachement, m.groupe_rang, m.groupe_id) == ("rattachee", 1, None)
    assert corriger_effectifs(lot) == []


def test_ALG_06_plusieurs_mises_au_point_cumulees():
    votes = [("p0", "pour"), ("p1", "pour"), ("c0", "contre")]
    mises = [("p0", "contre", "mise_au_point"), ("p1", "abstention", "mise_au_point")]
    (corr,) = _corriger((2, 1, 0), votes, mises)
    assert (corr.pour_corrige, corr.contre_corrige, corr.abstentions_corrigees) == (0, 2, 1)
    assert corr.nb_mises_au_point == 2


def test_ALG_06_scrutin_sans_mise_au_point():
    lot = _lot((3, 2, 0), [("p0", "pour")], [])
    assert rattacher(lot) == lot
    assert corriger_effectifs(lot) == []


def test_ALG_06_effectif_negatif_erreur_de_donnee():
    # compteurs officiels incohérents avec le rattachement : (0, 0, 0) mais un « pour » à retirer
    with pytest.raises(ErreurDonnee):
        _corriger((0, 0, 0), [("p0", "pour")], [("p0", "contre", "mise_au_point")])


def test_ALG_06_compteurs_officiels_jamais_modifies():
    lot = _lot((5, 5, 0), [("c0", "contre")], [("c0", "pour", "mise_au_point")])
    apres = rattacher(lot)
    assert apres.groupes == lot.groupes and apres.totaux == lot.totaux and apres.votes == lot.votes


def test_ALG_06_invariants_rattachee_plus_introuvable():
    lot = rattacher(
        _lot(
            (3, 2, 0),
            [("p0", "pour")],
            [("p0", "contre", "mise_au_point"), ("zz", "pour", "dysfonctionnement")],
        )
    )
    statuts = [m.statut_rattachement for m in lot.mises_au_point]
    assert sorted(statuts) == ["introuvable", "rattachee"]
