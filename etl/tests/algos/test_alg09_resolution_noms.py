"""Tests ALG-09 : cas limites de la fiche, extraits réels du référentiel AMO30 et archive réelle."""

import copy
import sqlite3
from pathlib import Path

import pytest

from etl.algos.alg01_archive import PROFIL_REFERENTIELS
from etl.algos.alg09_resolution_noms import resoudre_noms
from etl.io.db import (
    appliquer_migrations,
    ecrire_noms,
    lire_anciens_noms,
    lire_references_noms,
    version_schema_attendue,
)
from etl.models import EntreeAcceptee

RACINE = Path(__file__).parents[3]
AMO_REEL = RACINE / "data" / "referentiels_dl_amo30" / "amo30.zip"
DOSSIER_REEL = RACINE / "Scrutins.json"

# Extraits réels du référentiel officiel AMO30 (champs lus seulement)
ORGANE_UDR_ANCIEN = {
    "uid": "PO847173", "codeType": "GP", "libelle": "UDR", "libelleAbrege": "UDR",
    "viMoDe": {"dateDebut": "2024-09-12", "dateFin": "2025-09-04"},
}  # fmt: skip
ORGANE_UDR_NOUVEAU = {
    "uid": "PO872880", "codeType": "GP", "libelle": "Union des droites pour la République",
    "libelleAbrege": "UDR", "viMoDe": {"dateDebut": "2025-09-05", "dateFin": None},
}  # fmt: skip
ORGANE_COMMISSION = {"uid": "PO59047", "codeType": "COMPER", "libelle": "Commission", "libelleAbrege": "C"}


def _entree(racine: str, contenu: dict, nom: str) -> EntreeAcceptee:
    return EntreeAcceptee(nom, 1, "a" * 64, 1, {racine: contenu})


def _organe(o: dict) -> EntreeAcceptee:
    return _entree("organe", o, f"json/organe/{o['uid']}.json")


def _acteur(uid: str, nom="Dasseux", prenom="Michel", civ="M.") -> EntreeAcceptee:
    acteur = {"uid": {"#text": uid}, "etatCivil": {"ident": {"civ": civ, "prenom": prenom, "nom": nom}}}
    return _entree("acteur", acteur, f"json/acteur/{uid}.json")


def test_ALG_09_groupes_udr_deux_organes_distincts_meme_sigle():
    r = resoudre_noms(
        [_organe(ORGANE_UDR_ANCIEN), _organe(ORGANE_UDR_NOUVEAU)],
        {"PO847173": 3041, "PO872880": 5824},
        {},
    )
    assert [(g.id, g.libelle, g.sigle) for g in r.groupes] == [
        ("PO847173", "UDR", "UDR"),
        ("PO872880", "Union des droites pour la République", "UDR"),
    ]
    assert (r.rapport.groupes_references, r.rapport.groupes_resolus) == (2, 2)
    assert r.rapport.groupes_non_resolus == []


def test_ALG_09_depute_nom_prenom_civilite():
    r = resoudre_noms([_acteur("PA999")], {}, {"PA999": 4})
    assert [(d.id, d.nom, d.prenom, d.civilite) for d in r.deputes] == [
        ("PA999", "Dasseux", "Michel", "M.")]  # fmt: skip
    assert (r.rapport.deputes_references, r.rapport.deputes_resolus) == (1, 1)


def test_ALG_09_identifiants_absents_non_resolus_avec_occurrences():
    r = resoudre_noms([], {"PO1": 5}, {"PA1": 7})
    assert r.groupes == [] and r.deputes == []
    assert r.rapport.groupes_non_resolus == [{"id": "PO1", "raison": "absent", "occurrences": 5}]
    assert r.rapport.deputes_non_resolus == [{"id": "PA1", "raison": "absent", "occurrences": 7}]
    assert r.rapport.groupes_resolus + len(r.rapport.groupes_non_resolus) == (
        r.rapport.groupes_references)


def test_ALG_09_po0_jamais_resolu_ni_compte():
    r = resoudre_noms([_organe(ORGANE_UDR_ANCIEN)], {"PO0": 146, "PO847173": 1}, {})
    assert r.rapport.groupes_references == 1
    assert [g.id for g in r.groupes] == ["PO847173"]
    assert r.rapport.groupes_non_resolus == []


def test_ALG_09_organe_qui_n_est_pas_un_groupe():
    r = resoudre_noms([_organe(ORGANE_COMMISSION)], {"PO59047": 2}, {})
    assert r.groupes == []
    assert r.rapport.groupes_non_resolus[0]["raison"] == "organe_pas_un_groupe"
    assert any("organe_pas_un_groupe" in a for a in r.rapport.avertissements)


def test_ALG_09_identifiant_ambigu_deux_contenus_differents():
    autre = dict(ORGANE_UDR_ANCIEN, libelle="Autre libellé")
    entrees = [_organe(ORGANE_UDR_ANCIEN), _entree("organe", autre, "json/organe/PO847173.json")]
    r = resoudre_noms(entrees, {"PO847173": 1}, {})
    assert r.groupes == [] and r.rapport.groupes_non_resolus[0]["raison"] == "identifiant_ambigu"


def test_ALG_09_identifiant_en_double_identique_avertissement():
    entrees = [_organe(ORGANE_UDR_ANCIEN), _organe(copy.deepcopy(ORGANE_UDR_ANCIEN))]
    r = resoudre_noms(entrees, {"PO847173": 1}, {})
    assert [g.id for g in r.groupes] == ["PO847173"]
    assert any("en_double_identique" in a for a in r.rapport.avertissements)


@pytest.mark.parametrize("valeur", ["", "   ", None, {"@xsi:nil": "true"}, 12])
def test_ALG_09_libelle_vide_ou_invalide_non_resolu(valeur):
    r = resoudre_noms([_organe(dict(ORGANE_UDR_ANCIEN, libelle=valeur))], {"PO847173": 1}, {})
    assert r.groupes == [] and r.rapport.groupes_non_resolus[0]["raison"] == "libelle_vide"


def test_ALG_09_sigle_vide_accepte_en_null():
    r = resoudre_noms([_organe(dict(ORGANE_UDR_ANCIEN, libelleAbrege=" "))], {"PO847173": 1}, {})
    assert [(g.libelle, g.sigle) for g in r.groupes] == [("UDR", None)]


def test_ALG_09_nom_vide_depute_non_resolu_prenom_vide_accepte():
    r = resoudre_noms([_acteur("PA1", nom="  ")], {}, {"PA1": 1})
    assert r.deputes == [] and r.rapport.deputes_non_resolus[0]["raison"] == "nom_vide"
    r = resoudre_noms([_acteur("PA2", prenom="")], {}, {"PA2": 1})
    assert [(d.nom, d.prenom) for d in r.deputes] == [("Dasseux", None)]


def test_ALG_09_texte_normalise_nfc_et_bords_sans_toucher_l_interieur():
    decompose = "Régis"  # « Régis » avec accent combinant
    r = resoudre_noms([_acteur("PA3", nom="  Dupont  Martin ", prenom=decompose)], {}, {"PA3": 1})
    d = r.deputes[0]
    assert d.prenom == "Régis" and d.prenom == "Régis"
    assert d.nom == "Dupont  Martin"  # l'intérieur (deux espaces) n'est pas réécrit


def test_ALG_09_homonymes_deux_lignes_distinctes():
    r = resoudre_noms([_acteur("PA10", "Martin", "Paul"), _acteur("PA11", "Martin", "Paul")],
                      {}, {"PA10": 1, "PA11": 1})  # fmt: skip
    assert [d.id for d in r.deputes] == ["PA10", "PA11"]


def test_ALG_09_nom_modifie_signale():
    r = resoudre_noms(
        [_organe(ORGANE_UDR_ANCIEN), _acteur("PA999")],
        {"PO847173": 1},
        {"PA999": 1},
        anciens_groupes={"PO847173": ("Ancien libellé", "UDR")},
        anciens_deputes={"PA999": ("Dasseux", "Michel", "M.")},
    )
    assert r.rapport.noms_modifies == [
        {"id": "PO847173", "ancien": "Ancien libellé", "nouveau": "UDR"}]  # fmt: skip
    # nom identique : rien à signaler ; nom absent en base : pas une modification
    r = resoudre_noms([_acteur("PA999")], {}, {"PA999": 1},
                      anciens_deputes={"PA999": (None, None, None)})  # fmt: skip
    assert r.rapport.noms_modifies == []


def test_ALG_09_aucun_appariement_par_nom_ou_sigle():
    # le sigle « UDR » existe, mais l'identifiant demandé n'est pas dans le référentiel
    r = resoudre_noms([_organe(ORGANE_UDR_ANCIEN)], {"PO999999": 1}, {})
    assert r.groupes == [] and r.rapport.groupes_non_resolus[0]["raison"] == "absent"


def test_ALG_09_deterministe():
    args = ([_organe(ORGANE_UDR_NOUVEAU), _acteur("PA999")], {"PO872880": 2}, {"PA999": 3})
    assert resoudre_noms(*args) == resoudre_noms(*args)


# --- base SQLite ---------------------------------------------------------------------------------


def _base() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    appliquer_migrations(conn)
    return conn


def test_ALG_09_migration_civilite_et_version_de_schema():
    conn = _base()
    colonnes = [c[1] for c in conn.execute("PRAGMA table_info(deputes)")]
    assert "civilite" in colonnes
    assert conn.execute("PRAGMA user_version").fetchone()[0] == version_schema_attendue() >= 2
    appliquer_migrations(conn)  # rejouable : une base à jour ne rejoue rien
    assert [c[1] for c in conn.execute("PRAGMA table_info(deputes)")] == colonnes


def test_ALG_09_ecriture_ne_cree_aucune_ligne_et_nomme_les_resolus():
    conn = _base()
    conn.executemany("INSERT INTO groupes (id) VALUES (?)", [("PO847173",), ("PO1",)])
    conn.executemany("INSERT INTO deputes (id) VALUES (?)", [("PA999",), ("PA2",)])
    r = resoudre_noms(
        [_organe(ORGANE_UDR_ANCIEN), _acteur("PA999"), _acteur("PA777")],  # PA777 : pas en base
        {"PO847173": 1, "PO1": 1}, {"PA999": 1, "PA2": 1},
    )  # fmt: skip
    ecrire_noms(conn, r)
    assert conn.execute("SELECT COUNT(*) FROM groupes").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM deputes").fetchone()[0] == 2
    assert conn.execute("SELECT libelle, sigle FROM groupes WHERE id='PO847173'").fetchone() == (
        "UDR", "UDR")  # fmt: skip
    assert conn.execute("SELECT libelle FROM groupes WHERE id='PO1'").fetchone() == (None,)
    assert conn.execute("SELECT nom, prenom, civilite FROM deputes WHERE id='PA999'").fetchone() == (
        "Dasseux", "Michel", "M.")  # fmt: skip
    assert conn.execute("SELECT nom FROM deputes WHERE id='PA2'").fetchone() == (None,)
    # deuxième résolution des mêmes entrées : même base
    avant = conn.execute("SELECT * FROM deputes ORDER BY id").fetchall()
    anciens = lire_anciens_noms(conn)
    r2 = resoudre_noms(
        [_organe(ORGANE_UDR_ANCIEN), _acteur("PA999")], {"PO847173": 1}, {"PA999": 1}, *anciens)
    ecrire_noms(conn, r2)
    assert conn.execute("SELECT * FROM deputes ORDER BY id").fetchall() == avant
    assert r2.rapport.noms_modifies == []


def test_ALG_09_lecture_des_references_en_base():
    conn = _base()
    conn.execute("INSERT INTO scrutins (id, numero) VALUES ('S1', 1), ('S2', 2)")
    conn.execute("INSERT INTO groupes (id) VALUES ('PO1')")
    conn.executemany("INSERT INTO deputes (id) VALUES (?)", [("PA1",), ("PA2",)])
    for sid in ("S1", "S2"):
        conn.execute(
            "INSERT INTO scrutin_group_votes (scrutin_id, rang, groupe_id) VALUES (?, 1, 'PO1')",
            (sid,),
        )
        conn.execute(
            "INSERT INTO scrutin_group_votes (scrutin_id, rang, groupe_id) VALUES (?, 2, NULL)",
            (sid,),
        )
    conn.execute(
        "INSERT INTO scrutin_individual_votes (scrutin_id, depute_id, groupe_rang, position) "
        "VALUES ('S1', 'PA1', 1, 'pour'), ('S2', 'PA1', 1, 'pour')"
    )
    conn.execute(
        "INSERT INTO scrutin_mises_au_point (scrutin_id, depute_id, origine, position_declaree) "
        "VALUES ('S1', 'PA2', 'mise_au_point', 'pour'), ('S1', 'PA1', 'mise_au_point', 'contre')"
    )
    groupes, deputes = lire_references_noms(conn)
    assert groupes == {"PO1": 2}  # groupe_id nul (PO0) jamais référencé
    assert deputes == {"PA1": 3, "PA2": 1}


# --- référentiel et archive réels --------------------------------------------------------------


@pytest.mark.skipif(
    not (AMO_REEL.exists() and DOSSIER_REEL.exists()),
    reason="référentiel ou archive réels absents (ignorés par Git)",
)
def test_ALG_09_referentiel_reel_13_groupes_652_deputes():
    from collections import Counter

    from etl.algos.alg02_normalisation import normaliser_scrutin
    from etl.pipeline import lire_source

    entrees_ref, rapport_ref = lire_source(str(AMO_REEL), profil=PROFIL_REFERENTIELS)
    assert rapport_ref.statut == "complet"
    entrees, _ = lire_source(str(DOSSIER_REEL))
    groupes: Counter = Counter()
    deputes: Counter = Counter()
    for e in entrees:
        s = normaliser_scrutin(e.document_json).scrutin
        assert s is not None
        for g in s.groupes:
            if g.organe_ref is not None:
                groupes[g.organe_ref] += 1
            deputes.update(v.acteur_ref for v in g.votants)
    r = resoudre_noms(entrees_ref, groupes, deputes)
    assert (r.rapport.groupes_references, r.rapport.groupes_resolus) == (13, 13)
    assert (r.rapport.deputes_references, r.rapport.deputes_resolus) == (652, 652)
    assert r.rapport.groupes_non_resolus == [] and r.rapport.deputes_non_resolus == []
    par_id = {g.id: g for g in r.groupes}
    assert (par_id["PO847173"].libelle, par_id["PO847173"].sigle) == ("UDR", "UDR")
    assert par_id["PO872880"].libelle == "Union des droites pour la République"
    assert Counter(d.civilite for d in r.deputes) == {"M.": 406, "Mme": 246}
    assert all(d.nom and d.prenom for d in r.deputes)
