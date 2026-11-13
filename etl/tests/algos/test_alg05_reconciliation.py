"""Tests ALG-05 : cas limites et exemples chiffrés de la fiche."""

import dataclasses
import json
import sqlite3
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import normaliser_scrutin
from etl.algos.alg04_extraction_scrutin import extraire_scrutin
from etl.algos.alg05_reconciliation import (
    MAX_ECARTS_DETAILLES,
    ErreurEcartsConnus,
    charger_ecarts_connus,
    controler,
    depuis_lot,
)
from etl.io.db import appliquer_migrations, lire_pour_controle

RACINE = Path(__file__).parents[2]
FIXTURES = Path(__file__).parents[1] / "fixtures"
DOSSIER_REEL = RACINE.parent / "Scrutins.json"
CONNUS = RACINE / "ecarts_connus.json"


def _normalise(n: int):
    doc = json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))
    return normaliser_scrutin(doc).scrutin


def _a_controler(scrutin):
    lot = extraire_scrutin(scrutin, f"json/{scrutin.id}.json", "a" * 64, None, "t", "v1")
    return depuis_lot(scrutin, lot), lot


def _rapport_lot(scrutin, connus=None):
    a, _ = _a_controler(scrutin)
    return controler([a], charger_ecarts_connus(CONNUS) if connus is None else connus, "lot")


def _ids(rapport):
    return sorted({e.controle for e in rapport.ecarts})


# --- fichier des écarts connus -------------------------------------------------------------


def test_ALG_05_fichier_des_ecarts_connus_valide():
    connus = charger_ecarts_connus(CONNUS)
    assert sorted((e.controle, e.scrutin_id, e.detail) for e in connus) == [
        ("R07", "VTANR5L17V1", None),
        ("R08", "VTANR5L17V1", "non_votant"),
    ]


@pytest.mark.parametrize(
    "contenu",
    [
        "pas du json",
        "{}",
        '[{"controle": "R07"}]',
        '[{"controle": "R99", "scrutin_id": "x", "groupe_rang": null, "detail": null,'
        ' "attendu": 1, "obtenu": 2, "motif": "m", "valide_le": "d", "valide_par": "p"}]',
        '[{"controle": "R07", "scrutin_id": "x", "groupe_rang": null, "detail": null,'
        ' "attendu": "1", "obtenu": 2, "motif": "m", "valide_le": "d", "valide_par": "p"}]',
        '[{"controle": "R07", "scrutin_id": "x", "groupe_rang": null, "detail": null,'
        ' "attendu": 1, "obtenu": 2, "motif": "", "valide_le": "d", "valide_par": "p"}]',
    ],
)
def test_ALG_05_fichier_mal_forme_arret(tmp_path, contenu):
    f = tmp_path / "c.json"
    f.write_text(contenu, encoding="utf-8")
    with pytest.raises(ErreurEcartsConnus):
        charger_ecarts_connus(f)
    with pytest.raises(ErreurEcartsConnus):
        charger_ecarts_connus(tmp_path / "absent.json")


# --- niveau lot -----------------------------------------------------------------------------


@pytest.mark.parametrize("n", [2, 3, 489, 1017, 1302])
def test_ALG_05_fixtures_sans_ecart(n):
    r = _rapport_lot(_normalise(n))
    assert r.ecarts == [] and r.statut == "ecarts_connus" or r.statut == "ok"
    assert r.ecarts == []


def test_ALG_05_scrutin_1_deux_ecarts_connus():
    r = _rapport_lot(_normalise(1))
    assert sorted((e.controle, e.detail, e.attendu, e.obtenu, e.connu) for e in r.ecarts) == [
        ("R07", None, 10, 21, True),
        ("R08", "non_votant", 10, 21, True),
    ]
    assert r.statut == "ecarts_connus" and r.avertissements == []
    assert r.controles["R09"] == {"nb_verifies": 12 * 4, "nb_ecarts": 0}  # indépendant de R07/R08


def test_ALG_05_scrutin_1_sans_fichier_les_ecarts_sont_nouveaux():
    r = _rapport_lot(_normalise(1), connus=[])
    assert r.statut == "ecarts_nouveaux" and not any(e.connu for e in r.ecarts)


def test_ALG_05_valeur_obtenue_changee_redevient_nouvelle():
    s = _normalise(1)
    s = dataclasses.replace(s, non_votants=11)  # N = 11 au lieu de 10
    r = _rapport_lot(s)
    assert r.statut == "ecarts_nouveaux"
    assert {(e.controle, e.connu) for e in r.ecarts} >= {("R07", False), ("R08", False)}
    # 197 + 0 + 0 = V ? N n'entre pas dans R03 : pas d'écart supplémentaire attendu
    assert "R03" not in _ids(r)


def test_ALG_05_un_pour_modifie_plusieurs_controles_distincts():
    s = _normalise(2)
    r = _rapport_lot(dataclasses.replace(s, pour=s.pour + 1), connus=[])
    assert {"R02", "R03", "R04", "R08"} <= set(_ids(r))
    assert r.statut == "ecarts_nouveaux" and not any(e.connu for e in r.ecarts)


def test_ALG_05_groupe_trop_grand_r10_et_compteur_incoherent_r09():
    s = _normalise(2)
    g = dataclasses.replace(s.groupes[0], membres=0)
    r = _rapport_lot(dataclasses.replace(s, groupes=[g, *s.groupes[1:]]), connus=[])
    assert "R10" in _ids(r) and r.statut == "ecarts_nouveaux"
    g = dataclasses.replace(s.groupes[0], pour=s.groupes[0].pour + 1)
    r = _rapport_lot(dataclasses.replace(s, groupes=[g, *s.groupes[1:]]), connus=[])
    assert {"R04", "R09"} <= set(_ids(r))


def test_ALG_05_r11_resultat_incoherent_bloque_r12_informatif():
    s = _normalise(2)
    inverse = "rejete" if s.sort_code == "adopte" else "adopte"
    r = _rapport_lot(dataclasses.replace(s, sort_code=inverse), connus=[])
    assert "R11" in _ids(r) and r.statut == "ecarts_nouveaux"
    # seuil de majorité modifié : R12 est informatif (ne bloque pas) ; R11 reste cohérent
    r = _rapport_lot(dataclasses.replace(s, nbr_suffrages_requis=s.nbr_suffrages_requis + 1))
    assert "R12" in _ids(r)
    if "R11" not in _ids(r):
        assert r.statut == "ecarts_informatifs"


def test_ALG_05_r12_non_applique_aux_motions_de_censure():
    s = _normalise(1)  # type MOC
    r = _rapport_lot(dataclasses.replace(s, nbr_suffrages_requis=1))
    assert "R12" not in r.controles


def test_ALG_05_r13_et_r14():
    s = _normalise(2)
    r = _rapport_lot(dataclasses.replace(s, non_votants_volontaires=3), connus=[])
    assert "R13" in _ids(r) and r.statut == "ecarts_informatifs"
    g = dataclasses.replace(s.groupes[0], abstentions_doublon_source=s.groupes[0].abstentions + 1)
    r = _rapport_lot(dataclasses.replace(s, groupes=[g, *s.groupes[1:]]), connus=[])
    assert "R14" in _ids(r) and r.statut == "ecarts_nouveaux"


def test_ALG_05_numero_different_du_suffixe_r01():
    s = _normalise(2)
    r = _rapport_lot(dataclasses.replace(s, numero=99), connus=[])
    assert [(e.controle, e.attendu, e.obtenu) for e in r.ecarts] == [("R01", 99, 2)]


def test_ALG_05_ecart_connu_disparu_avertissement():
    r = _rapport_lot(_normalise(2))  # le scrutin 1 n'est pas dans le lot
    assert r.avertissements == []  # le scrutin 1 n'a pas été examiné : rien n'a « disparu »
    a, _ = _a_controler(_normalise(1))
    a_corrige = dataclasses.replace(a, non_votants=21)
    r = controler([a_corrige], charger_ecarts_connus(CONNUS), "lot")
    assert r.ecarts == [] and r.statut == "ok"
    assert len(r.avertissements) == 2 and all("ecart_connu_disparu" in w for w in r.avertissements)


def test_ALG_05_lot_vide_jamais_ok():
    r = controler([], [], "lot")
    assert r.scrutins_controles == 0 and r.statut == "ecarts_nouveaux"


def test_ALG_05_plafond_des_ecarts_detailles_compte_exact():
    s = _normalise(2)
    a, _ = _a_controler(s)
    mauvais = [dataclasses.replace(a, id=f"VTANR5L17V{n}", numero=n + 1) for n in range(2000)]
    r = controler(mauvais, [], "lot")
    assert r.controles["R01"]["nb_ecarts"] == 2000
    assert len([e for e in r.ecarts if e.controle == "R01"]) == MAX_ECARTS_DETAILLES


def test_ALG_05_niveau_inconnu():
    with pytest.raises(ValueError):
        controler([], [], "autre")


def test_ALG_05_deterministe_et_ne_modifie_rien():
    s = _normalise(1)
    assert _rapport_lot(s) == _rapport_lot(s)


# --- niveau base ----------------------------------------------------------------------------


def _base(scrutins) -> sqlite3.Connection:
    """Base en mémoire remplie par des requêtes simples (rôle d'ALG-07, ici pour le test)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    appliquer_migrations(conn)
    for s in scrutins:
        _inserer(conn, *_a_controler(s)[1:], s)
    return conn


def _inserer(conn, lot, scrutin):
    conn.executemany("INSERT OR IGNORE INTO groupes (id) VALUES (?)", [(g,) for g in lot.groupes_vus])
    conn.executemany("INSERT OR IGNORE INTO deputes (id) VALUES (?)", [(d,) for d in lot.deputes_vus])
    s, t = lot.scrutin, lot.totaux
    conn.execute(
        "INSERT INTO scrutins (id, numero, legislature, resultat_code) VALUES (?,?,?,?)",
        (s.id, s.numero, s.legislature, s.resultat_code),
    )
    conn.execute(
        "INSERT INTO scrutin_totals VALUES (?,?,?,?,?,?,?)",
        (t.scrutin_id, t.pour, t.contre, t.abstentions, t.non_votants, t.suffrages_exprimes,
         t.nombre_votants),
    )  # fmt: skip
    conn.executemany(
        "INSERT INTO scrutin_group_votes VALUES (?,?,?,?,?,?,?,?,?)",
        [(g.scrutin_id, g.rang, g.groupe_id, g.membres, g.pour, g.contre, g.abstentions,
          g.non_votants, g.position_majoritaire_source) for g in lot.groupes],
    )  # fmt: skip
    conn.executemany(
        "INSERT INTO scrutin_individual_votes VALUES (?,?,?,?,?,?,?,?)",
        [(v.scrutin_id, v.depute_id, v.groupe_rang, v.groupe_id, v.mandat_id, v.position,
          v.par_delegation, v.cause) for v in lot.votes],
    )  # fmt: skip


def _rapport_base(conn, connus=None, attendu=None):
    c = charger_ecarts_connus(CONNUS) if connus is None else connus
    return controler(lire_pour_controle(conn), c, "base", attendu)


def test_ALG_05_base_scrutin_1_memes_deux_ecarts_connus():
    conn = _base([_normalise(1), _normalise(2), _normalise(489), _normalise(1017)])
    r = _rapport_base(conn, attendu=4)
    assert r.scrutins_controles == 4 and r.statut == "ecarts_connus"
    assert sorted((e.controle, e.scrutin_id, e.detail) for e in r.ecarts) == [
        ("R07", "VTANR5L17V1", None),
        ("R08", "VTANR5L17V1", "non_votant"),
    ]
    assert r.controles["R15"]["nb_ecarts"] == 0 and r.controles["R17"]["nb_verifies"] == 8


def test_ALG_05_base_ligne_de_vote_supprimee_r08_r09():
    conn = _base([_normalise(2)])
    conn.execute(
        "DELETE FROM scrutin_individual_votes WHERE depute_id = "
        "(SELECT depute_id FROM scrutin_individual_votes WHERE position = 'pour' LIMIT 1)"
    )
    r = _rapport_base(conn, connus=[])
    assert {"R08", "R09"} <= set(_ids(r)) and r.statut == "ecarts_nouveaux"


def test_ALG_05_base_reference_inconnue_r15():
    conn = _base([_normalise(2)])
    conn.commit()  # PRAGMA foreign_keys est sans effet dans une transaction ouverte
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "DELETE FROM deputes WHERE id = (SELECT depute_id FROM scrutin_individual_votes LIMIT 1)"
    )
    assert "R15" in _ids(_rapport_base(conn, connus=[]))


def test_ALG_05_base_scrutin_sans_groupe_ni_totaux_r17():
    conn = _base([_normalise(2)])
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM scrutin_totals")
    conn.execute("DELETE FROM scrutin_group_votes")
    conn.execute("DELETE FROM scrutin_individual_votes")
    r = _rapport_base(conn, connus=[])
    assert {(e.controle, e.detail) for e in r.ecarts} >= {("R17", "groupes"), ("R17", "totaux")}
    assert r.statut == "ecarts_nouveaux"


def test_ALG_05_base_vide_jamais_ok():
    r = _rapport_base(_base([]))
    assert r.scrutins_controles == 0 and r.statut == "ecarts_nouveaux"
    assert {"R16", "R17"} <= set(_ids(r))


def test_ALG_05_base_nombre_de_scrutins_attendu_r16():
    r = _rapport_base(_base([_normalise(2)]), attendu=5)
    assert [(e.controle, e.attendu, e.obtenu) for e in r.ecarts] == [("R16", 5, 1)]


# --- archive réelle complète ---------------------------------------------------------------


@pytest.mark.skipif(not DOSSIER_REEL.exists(), reason="archive réelle absente")
def test_ALG_05_archive_complete_lot_et_base():
    from etl.pipeline import lire_source

    acceptees, rapport = lire_source(str(DOSSIER_REEL))
    assert len(acceptees) == 8877
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    appliquer_migrations(conn)
    controles = []
    for a in acceptees:
        s = normaliser_scrutin(a.document_json).scrutin
        assert s is not None
        lot = extraire_scrutin(s, a.nom, a.sha256_fichier, None, "t", "v1")
        controles.append(depuis_lot(s, lot))
        _inserer(conn, lot, s)
    connus = charger_ecarts_connus(CONNUS)

    r_lot = controler(controles, connus, "lot")
    r_base = controler(lire_pour_controle(conn), connus, "base", nb_scrutins_attendu=8877)
    for r in (r_lot, r_base):
        assert r.scrutins_controles == 8877 and r.statut == "ecarts_connus"
        assert sorted((e.controle, e.scrutin_id) for e in r.ecarts) == [
            ("R07", "VTANR5L17V1"),
            ("R08", "VTANR5L17V1"),
        ]
        assert r.controles["R09"] == {"nb_verifies": 106_524 * 4, "nb_ecarts": 0}
        assert r.avertissements == []
    # R12 et R13/R14 : informatifs ou propres au lot, sans écart sur les données réelles
    assert r_lot.controles["R14"] == {"nb_verifies": 106_524, "nb_ecarts": 0}
    assert r_lot.controles["R12"]["nb_ecarts"] == 0
