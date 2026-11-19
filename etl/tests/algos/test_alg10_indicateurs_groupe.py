"""Tests ALG-10 : exemples chiffrés de la fiche, bornes réglables, comparaison et archive réelle."""

from pathlib import Path

import pytest

from etl.algos.alg03_position_majoritaire import ErreurDonnee
from etl.algos.alg10_indicateurs_groupe import (
    BORNES_PAR_DEFAUT,
    ErreurParametre,
    calculer_indicateurs,
    comparer_groupes,
    indice_tranche,
    libelles_tranches,
    valider_bornes,
)
from etl.models import LigneGroupeScrutin, LigneVoteSelection

DOSSIER_REEL = Path(__file__).parents[2].parent / "Scrutins.json"


def _l(sid, g, membres, p, c, a, n, categorie="amendement"):
    return LigneGroupeScrutin(sid, "2025-01-01", categorie, "adopte", "SPO", g, membres, p, c, a, n)


# Exemple de la fiche : cinq lignes d'un groupe (arithmétique construite)
CINQ = [
    _l("s1", "G", 20, 12, 2, 0, 1),
    _l("s2", "G", 70, 5, 6, 49, 0),
    _l("s3", "G", 15, 6, 6, 1, 0),
    _l("s4", "G", 8, 3, 2, 2, 0),
    _l("s5", "G", 10, 0, 0, 0, 2),
]


def test_ALG_10_exemple_de_la_fiche_cinq_lignes():
    (i,) = calculer_indicateurs(CINQ)
    assert (i.nb_scrutins, i.membres_scrutins) == (5, 123)
    assert (i.pour, i.contre, i.abstentions, i.non_votants, i.sans_vote_enregistre) == (
        26, 16, 52, 3, 26)  # fmt: skip
    assert i.exprimes == 94 and i.exprimes + i.non_votants + i.sans_vote_enregistre == 123
    assert i.scrutins_par_position_majoritaire == {
        "pour": 2, "contre": 0, "abstention": 1, "egalite": 1, "aucun_vote_exprime": 1}  # fmt: skip
    # tranches par défaut : P1 0, P2 0, P3 1, P4 0, P5 2, P6 0
    assert i.repartition_part_majoritaire == (0, 0, 1, 0, 2, 0)
    assert i.bornes == (20, 40, 60, 80) and len(i.libelles_tranches) == 6


def test_ALG_10_relations_et_somme_des_tranches():
    (i,) = calculer_indicateurs(CINQ)
    assert i.pour + i.contre + i.abstentions == i.exprimes
    assert sum(i.scrutins_par_position_majoritaire.values()) == i.nb_scrutins
    avec_position = sum(i.scrutins_par_position_majoritaire[k] for k in ("pour", "contre", "abstention"))
    assert sum(i.repartition_part_majoritaire) == avec_position == 3


def test_ALG_10_bornes_reglables():
    (i,) = calculer_indicateurs(CINQ, bornes=[50])
    # trois tranches : moins de 50 %, de 50 % à moins de 100 %, 100 %
    assert i.libelles_tranches == ("moins de 50 %", "de 50 % à moins de 100 %", "100 % (unanime)")
    assert i.repartition_part_majoritaire == (1, 2, 0)  # s4 : 3/7 ; s1 et s2


def test_ALG_10_cas_unanime_et_bornes_incluses():
    assert indice_tranche(1, 1, BORNES_PAR_DEFAUT) == 5  # 100 % : dernière tranche
    assert indice_tranche(4, 5, BORNES_PAR_DEFAUT) == 4  # 80 % exactement : tranche qui commence à 80
    assert indice_tranche(2, 5, BORNES_PAR_DEFAUT) == 2  # 40 % exactement : tranche 40-60
    assert indice_tranche(7, 20, BORNES_PAR_DEFAUT) == 1  # 35 % : de 20 à moins de 40
    with pytest.raises(ErreurDonnee):
        indice_tranche(0, 0, BORNES_PAR_DEFAUT)


def test_ALG_10_premiere_tranche_toujours_vide_avec_bornes_par_defaut():
    # une position majoritaire stricte a m > E/3 : aucune part inférieure à 33,4 %
    for p in range(1, 40):
        for c in range(40):
            for a in range(40):
                e = p + c + a
                m = max(p, c, a)
                if [p, c, a].count(m) == 1:
                    assert indice_tranche(m, e, BORNES_PAR_DEFAUT) >= 1  # jamais « moins de 20 % »


@pytest.mark.parametrize("bornes", [[], [0], [100], [40, 40], [60, 20], [1.5], [True], ["20"]])
def test_ALG_10_bornes_invalides(bornes):
    with pytest.raises(ErreurParametre):
        valider_bornes(bornes)
    with pytest.raises(ErreurParametre):
        calculer_indicateurs(CINQ, bornes=bornes)


def test_ALG_10_libelles_sans_qualificatif():
    libelles = libelles_tranches(BORNES_PAR_DEFAUT)
    assert libelles == (
        "moins de 20 %",
        "de 20 % à moins de 40 %",
        "de 40 % à moins de 60 %",
        "de 60 % à moins de 80 %",
        "de 80 % à moins de 100 %",
        "100 % (unanime)",
    )
    interdits = ("faible", "élevé", "moyen", "fort", "bon", "mauvais")
    assert not any(m in lib for lib in libelles for m in interdits)


def test_ALG_10_selection_vide_et_groupe_sans_vote_exprime():
    assert calculer_indicateurs([]) == []
    (i,) = calculer_indicateurs([_l("s1", "G", 10, 0, 0, 0, 2), _l("s2", "G", 10, 0, 0, 0, 0)])
    assert i.exprimes == 0 and i.scrutins_par_position_majoritaire["aucun_vote_exprime"] == 2
    assert i.repartition_part_majoritaire == (0,) * 6 and i.sans_vote_enregistre == 18


def test_ALG_10_groupe_non_identifie_exclu_et_compte():
    lignes = [_l("s1", "G", 10, 5, 0, 0, 0), _l("s1", None, 10, 1, 0, 0, 0),
              _l("s1", None, 10, 2, 0, 0, 0), _l("s2", None, 10, 3, 0, 0, 0)]  # fmt: skip
    (i,) = calculer_indicateurs(lignes)
    assert i.groupe_id == "G" and i.nb_scrutins == 1
    assert i.nb_scrutins_exclus_groupe_non_identifie == 2  # deux scrutins distincts concernés


@pytest.mark.parametrize(
    "ligne",
    [_l("s", "G", 0, 0, 0, 0, 0), _l("s", "G", 5, -1, 0, 0, 0), _l("s", "G", 5, 3, 2, 1, 0)],
)
def test_ALG_10_ligne_absurde_erreur_de_donnee(ligne):
    with pytest.raises(ErreurDonnee):
        calculer_indicateurs([ligne])


def test_ALG_10_ligne_en_double_erreur_de_donnee():
    with pytest.raises(ErreurDonnee):
        calculer_indicateurs([_l("s1", "G", 10, 1, 0, 0, 0), _l("s1", "G", 10, 1, 0, 0, 0)])


def test_ALG_10_personnes_distinctes_exemple_de_la_fiche():
    lignes = [_l("s1", "G", 5, 2, 1, 0, 0), _l("s2", "G", 5, 0, 1, 1, 0), _l("s3", "G", 5, 0, 0, 0, 1)]
    votes = [
        LigneVoteSelection("s1", "G", "d1", "pour"),
        LigneVoteSelection("s1", "G", "d2", "pour"),
        LigneVoteSelection("s1", "G", "d3", "contre"),
        LigneVoteSelection("s2", "G", "d1", "contre"),
        LigneVoteSelection("s2", "G", "d4", "abstention"),
        LigneVoteSelection("s3", "G", "d2", "non_votant"),
        LigneVoteSelection("s3", "H", "d9", "pour"),  # autre groupe : ne compte pas
        LigneVoteSelection("s3", None, "d8", "pour"),  # groupe non identifié : ne compte pas
    ]
    (i,) = calculer_indicateurs(lignes, votes)
    assert i.exprimes == 5 and (i.personnes_exprimees, i.personnes_avec_vote) == (4, 4)
    assert i.personnes_exprimees <= i.exprimes and i.personnes_avec_vote <= i.membres_scrutins


def test_ALG_10_un_depute_dans_deux_groupes_compte_dans_chacun():
    lignes = [_l("s1", "G", 5, 1, 0, 0, 0), _l("s2", "H", 5, 1, 0, 0, 0)]
    votes = [LigneVoteSelection("s1", "G", "d1", "pour"), LigneVoteSelection("s2", "H", "d1", "pour")]
    par_id = {i.groupe_id: i for i in calculer_indicateurs(lignes, votes)}
    assert par_id["G"].personnes_exprimees == par_id["H"].personnes_exprimees == 1


def test_ALG_10_ordre_alphabetique_jamais_selon_un_indicateur():
    lignes = [_l("s1", "G2", 10, 9, 0, 0, 0), _l("s1", "G1", 10, 1, 0, 0, 0),
              _l("s1", "G3", 10, 5, 0, 0, 0)]  # fmt: skip
    sans = calculer_indicateurs(lignes)
    assert [i.groupe_id for i in sans] == ["G1", "G2", "G3"]
    avec = calculer_indicateurs(lignes, libelles_groupes={"G1": "Zèbre", "G2": "Abeille", "G3": None})
    assert [i.groupe_id for i in avec] == ["G2", "G1", "G3"]  # libellé non résolu en dernier


def test_ALG_10_independant_de_l_ordre_des_lignes():
    assert calculer_indicateurs(CINQ) == calculer_indicateurs(list(reversed(CINQ)))


# --- comparaison de deux groupes -------------------------------------------------------------


def _paires():
    a = [_l("s1", "A", 10, 3, 0, 0, 0), _l("s2", "A", 10, 0, 1, 2, 0),
         _l("s3", "A", 10, 2, 2, 0, 0), _l("s4", "A", 10, 2, 0, 0, 0)]  # fmt: skip
    b = [_l("s1", "B", 10, 1, 0, 0, 0), _l("s2", "B", 10, 0, 2, 0, 0),
         _l("s3", "B", 10, 3, 1, 0, 0), _l("s4", "B", 10, 0, 0, 0, 0)]  # fmt: skip
    return a + b


def test_ALG_10_comparaison_exemple_de_la_fiche():
    c = comparer_groupes("A", "B", _paires(), filtres="test")
    assert c.scrutins_communs == 4 and c.scrutins_un_seul_present == 0 and c.filtres == "test"
    assert [s.scrutin_id for s in c.meme_position] == ["s1"]
    assert [s.scrutin_id for s in c.positions_differentes] == ["s2"]
    assert [(s.scrutin_id, s.raison_a, s.raison_b) for s in c.au_moins_une_sans_position] == [
        ("s3", "egalite", None), ("s4", None, "aucun_vote_exprime")]  # fmt: skip
    assert len(c.meme_position) + len(c.positions_differentes) + len(
        c.au_moins_une_sans_position) == c.scrutins_communs  # fmt: skip
    s2 = c.positions_differentes[0]
    assert (s2.position_a, s2.position_b) == ("abstention", "contre")
    assert (s2.exprimes_a, s2.majoritaire_a, s2.membres_a) == (3, 2, 10)


def test_ALG_10_comparaison_sans_scrutin_commun():
    lignes = [_l("s1", "A", 10, 1, 0, 0, 0), _l("s2", "B", 10, 1, 0, 0, 0)]
    c = comparer_groupes("A", "B", lignes)
    assert c.scrutins_communs == 0 and c.scrutins_un_seul_present == 2


def test_ALG_10_comparaison_ignore_les_autres_groupes_et_les_non_identifies():
    lignes = _paires() + [_l("s1", "C", 10, 9, 0, 0, 0), _l("s1", None, 10, 9, 0, 0, 0)]
    assert comparer_groupes("A", "B", lignes) == comparer_groupes("A", "B", _paires())


def test_ALG_10_comparaison_deux_groupes_distincts_obligatoires():
    with pytest.raises(ValueError):
        comparer_groupes("A", "A", _paires())


# --- archive réelle ------------------------------------------------------------------------------


@pytest.mark.skipif(not DOSSIER_REEL.exists(), reason="archive réelle absente")
def test_ALG_10_archive_complete_invariants_et_constats():
    from etl.algos.alg02_normalisation import normaliser_scrutin
    from etl.pipeline import lire_source

    entrees, _ = lire_source(str(DOSSIER_REEL))
    lignes, votes = [], []
    for e in entrees:
        s = normaliser_scrutin(e.document_json).scrutin
        assert s is not None
        for g in s.groupes:
            lignes.append(
                LigneGroupeScrutin(s.id, s.date_scrutin, "x", s.sort_code, s.type_vote_code,
                                   g.organe_ref, g.membres, g.pour, g.contre, g.abstentions,
                                   g.non_votants)
            )
            votes.extend(LigneVoteSelection(s.id, g.organe_ref, v.acteur_ref, v.position)
                         for v in g.votants)  # fmt: skip
    # le scrutin n° 1 contient des groupes dont E + N peut dépasser... : vérifié par ALG-05 (R10)
    resultats = calculer_indicateurs(lignes, votes)
    assert len(resultats) == 13
    assert sum(i.nb_scrutins for i in resultats) == 106_524 - 146
    assert resultats[0].nb_scrutins_exclus_groupe_non_identifie == 14
    for i in resultats:
        assert i.pour + i.contre + i.abstentions == i.exprimes
        assert i.exprimes + i.non_votants + i.sans_vote_enregistre == i.membres_scrutins
        assert sum(i.scrutins_par_position_majoritaire.values()) == i.nb_scrutins
        avec_position = sum(i.scrutins_par_position_majoritaire[k] for k in ("pour", "contre", "abstention"))
        assert sum(i.repartition_part_majoritaire) == avec_position
        assert i.repartition_part_majoritaire[0] == 0  # « moins de 20 % » toujours vide
        assert i.personnes_exprimees <= i.exprimes and i.personnes_avec_vote <= i.membres_scrutins
    # constats de la fiche (mesurés le 2026-11-03), sur les 106 524 groupes-scrutins
    from etl.algos.alg03_position_majoritaire import calculer_position

    positions = [calculer_position(l.pour, l.contre, l.abstentions, l.membres) for l in lignes]
    assert sum(p.raison_absence == "aucun_vote_exprime" for p in positions) == 9_547
    assert sum(p.raison_absence == "egalite" for p in positions) == 2_035
    # PO872880 et PO847173 n'ont aucun scrutin commun
    c = comparer_groupes("PO872880", "PO847173", lignes)
    assert c.scrutins_communs == 0 and c.scrutins_un_seul_present == 5_824 + 3_041
