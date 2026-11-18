"""Tests ALG-12 : un test par cas de la fiche, par règle, et les invariants (rapports construits)."""

import dataclasses
import itertools
import json
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import normaliser_scrutin
from etl.algos.alg04_extraction_scrutin import extraire_scrutin
from etl.algos.alg06_mises_au_point import rattacher
from etl.algos.alg11_export_statique import calculer_diff, empreinte_entrees, exporter
from etl.algos.alg12_garde_fou_deploiement import (
    decider,
    deploiement_autorise,
    doit_traiter,
    serialiser_decision,
    verifier_deploiement,
)
from etl.models import (
    ContexteExport,
    EntreesDecision,
    ParametresDecision,
    RapportExport,
    RapportImport,
    RapportLecture,
    RapportReconciliation,
    RapportTelechargement,
    ReferentielsExport,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
ENTREES = {"archive_sha256": "a" * 64, "version_etl": "v1", "version_regles_classification": "r1"}
D = "d" * 64


def _manifeste(entrees=ENTREES, donnees=D, scrutins=None):
    return {
        "empreinte_entrees": empreinte_entrees(entrees),
        "donnees_sha256": donnees,
        "scrutins": scrutins if scrutins is not None else {},
    }


def _entrees(**sur) -> EntreesDecision:
    """Cas courant : tout est ok, version publiée existante, aucune modification, mode sûr levé."""
    base = dict(
        lecture=RapportLecture(statut="complet"),
        importation=RapportImport(statut="termine"),
        reconciliation=RapportReconciliation(niveau="base", statut="ecarts_connus"),
        export=RapportExport(statut="ok", nombre_groupes=13),
        tests_ok=True,
        verification="ok",
        telechargement=RapportTelechargement(statut="nouvelle"),
        manifeste_courant=_manifeste(donnees="e" * 64),
        manifeste_precedent=_manifeste(entrees={**ENTREES, "archive_sha256": "z" * 64}),
        diff={"nouveaux": 12, "nombre_supprimes": 0, "nombre_modifies_chiffres": 0, "nombre_modifies_autres": 0},
        nombre_groupes_precedent=13,
        mode_sur=False,
    )  # fmt: skip
    return EntreesDecision(**(base | sur))


def _ids(decision):
    return [r["id"] for r in decision.raisons]


# --- table des cas limites de la fiche -----------------------------------------------------------------


def test_ALG_12_meme_archive_versions_referentiels_et_regles_rien_a_faire():
    e = _entrees(manifeste_precedent=_manifeste(donnees="x" * 64))  # mêmes entrées
    d = decider(e)
    assert (d.decision, d.raisons) == ("rien_a_faire", ())


def test_ALG_12_meme_archive_mais_version_d_algorithme_differente_poursuit():
    changees = {**ENTREES, "version_etl": "v2"}
    e = _entrees(manifeste_precedent=_manifeste(entrees=changees))  # archive identique, algorithme changé
    assert decider(e).decision == "publier"


def test_ALG_12_douze_nouveaux_scrutins_tout_ok_publier():
    d = decider(_entrees())
    assert (d.decision, _ids(d)) == ("publier", [])


def test_ALG_12_meme_cas_mode_sur_attente_validation_V00():
    d = decider(_entrees(mode_sur=True))
    assert (d.decision, _ids(d)) == ("attente_validation", ["V00"])


def test_ALG_12_un_chiffre_publie_modifie_V03():
    diff = {"nouveaux": 0, "nombre_supprimes": 0, "nombre_modifies_chiffres": 1, "nombre_modifies_autres": 0}
    d = decider(_entrees(diff=diff))
    assert (d.decision, _ids(d)) == ("attente_validation", ["V03"])


def test_ALG_12_vingt_cinq_modifies_sans_chiffre_V04():
    diff = {"nouveaux": 0, "nombre_supprimes": 0, "nombre_modifies_chiffres": 0, "nombre_modifies_autres": 25}
    d = decider(_entrees(diff=diff))
    assert (d.decision, _ids(d)) == ("attente_validation", ["V04"])
    # au seuil exact (20) : pas de V04
    diff["nombre_modifies_autres"] = 20
    assert decider(_entrees(diff=diff)).decision == "publier"


def test_ALG_12_un_scrutin_disparait_V02():
    diff = {"nouveaux": 0, "nombre_supprimes": 1, "nombre_modifies_chiffres": 0, "nombre_modifies_autres": 0}
    assert _ids(decider(_entrees(diff=diff))) == ["V02"]
    absent = _entrees(importation=RapportImport(statut="termine", absents_de_l_archive=["VTANR5L17V5"]))
    assert _ids(decider(absent)) == ["V02"]  # signalé par ALG-07 sans différence de manifeste


def test_ALG_12_ecart_de_reconciliation_nouveau_bloque_meme_si_V03_est_vraie():
    diff = {"nouveaux": 0, "nombre_supprimes": 0, "nombre_modifies_chiffres": 3, "nombre_modifies_autres": 0}
    e = _entrees(reconciliation=RapportReconciliation(niveau="base", statut="ecarts_nouveaux"), diff=diff)
    d = decider(e)
    assert d.decision == "bloquer" and _ids(d) == ["G03"]  # le blocage prime : pas de V dans les raisons


def test_ALG_12_archive_partielle_bloque_G01():
    d = decider(_entrees(lecture=RapportLecture(statut="partiel")))
    assert (d.decision, _ids(d)) == ("bloquer", ["G01"])


def test_ALG_12_premiere_publication_V01():
    d = decider(_entrees(manifeste_precedent=None, diff=None, nombre_groupes_precedent=None))
    assert (d.decision, _ids(d)) == ("attente_validation", ["V01"])


def test_ALG_12_six_cents_nouveaux_V05():
    diff = {"nouveaux": 600, "nombre_supprimes": 0, "nombre_modifies_chiffres": 0, "nombre_modifies_autres": 0}
    assert _ids(decider(_entrees(diff=diff))) == ["V05"]
    diff["nouveaux"] = 500  # au seuil exact : pas de V05
    assert decider(_entrees(diff=diff)).decision == "publier"


def test_ALG_12_forcer_avec_archive_identique_V08():
    e = _entrees(manifeste_precedent=_manifeste(donnees="x" * 64), forcer=True)
    d = decider(e)
    assert (d.decision, _ids(d)) == ("attente_validation", ["V08"])


def test_ALG_12_deploiement_dont_meta_en_ligne_differe():
    assert verifier_deploiement({"archive_sha256": "a" * 64, "nombre_scrutins": 9}, "a" * 64, 9) == []
    assert len(verifier_deploiement({"archive_sha256": "b" * 64, "nombre_scrutins": 9}, "a" * 64, 9)) == 1
    assert len(verifier_deploiement({"archive_sha256": "a" * 64, "nombre_scrutins": 8}, "a" * 64, 9)) == 1
    assert len(verifier_deploiement({"archive_sha256": "x", "nombre_scrutins": 1}, "a" * 64, 9)) == 2
    assert verifier_deploiement(None, "a" * 64, 9) == ["meta.json en ligne illisible"]


# --- règles bloquantes -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sur, regle",
    [
        ({"telechargement": RapportTelechargement(statut="echec", cause_echec="http_erreur")}, "G01"),
        ({"lecture": RapportLecture(statut="echec")}, "G01"),
        ({"importation": RapportImport(statut="echoue")}, "G02"),
        ({"importation": RapportImport(statut="interrompu")}, "G02"),
        ({"importation": RapportImport(statut="termine_avec_erreurs")}, "G02"),
        ({"importation": RapportImport(statut="simulation")}, "G02"),  # une simulation n'autorise rien
        ({"reconciliation": RapportReconciliation(niveau="base", statut="ecarts_nouveaux")}, "G03"),
        ({"reconciliation": RapportReconciliation(niveau="base", statut="inconnu")}, "G03"),
        ({"export": RapportExport(statut="echec", cause_echec="trop_de_fichiers")}, "G04"),
        ({"tests_ok": False}, "G05"),
        ({"verification": None}, "G06"),
        ({"verification": "echec"}, "G06"),
    ],
)
def test_ALG_12_chaque_regle_bloquante(sur, regle):
    d = decider(_entrees(**sur))
    assert d.decision == "bloquer" and regle in _ids(d)


def test_ALG_12_telechargement_absent_exécution_locale_n_est_pas_un_blocage():
    assert decider(_entrees(telechargement=None)).decision == "publier"


def test_ALG_12_toutes_les_raisons_bloquantes_sont_donnees_d_un_coup():
    e = _entrees(
        lecture=RapportLecture(statut="partiel"),
        importation=RapportImport(statut="echoue"),
        tests_ok=False,
        verification=None,
        reconciliation=RapportReconciliation(niveau="base", statut="ecarts_nouveaux"),
    )
    d = decider(e)
    assert d.decision == "bloquer"
    assert sorted(set(_ids(d))) == ["G01", "G02", "G03", "G05", "G06"]


# --- règles de validation et avertissements -------------------------------------------------------------


def test_ALG_12_noms_modifies_et_nombre_de_groupes_V06_V07():
    assert _ids(decider(_entrees(noms_modifies=[{"id": "PO1", "ancien": "a", "nouveau": "b"}]))) == ["V06"]
    assert _ids(decider(_entrees(nombre_groupes_precedent=12))) == ["V07"]
    assert decider(_entrees(nombre_groupes_precedent=None)).decision == "publier"


def test_ALG_12_toutes_les_validations_sont_relevees():
    diff = {"nouveaux": 600, "nombre_supprimes": 2, "nombre_modifies_chiffres": 30, "nombre_modifies_autres": 5}
    e = _entrees(diff=diff, mode_sur=True, forcer=True, nombre_groupes_precedent=11,
                 noms_modifies=[{"id": "x"}])  # fmt: skip
    d = decider(e)
    assert d.decision == "attente_validation"
    assert _ids(d) == ["V00", "V02", "V03", "V04", "V05", "V06", "V07", "V08"]


def test_ALG_12_avertissements_sans_effet_sur_la_decision():
    e = _entrees(
        telechargement=RapportTelechargement(statut="nouvelle", avertissements=["archive_ancienne"]),
        export=RapportExport(statut="ok", nombre_groupes=13, avertissements=["fichier_volumineux : x"]),
        indetermines_precedent=0,
        indetermines_courant=2,
    )
    d = decider(e)
    assert d.decision == "publier" and _ids(d) == ["A01", "A02", "A03"]
    # fraîcheur inconnue = avertissement ; indéterminés stables ou en baisse = rien
    e = _entrees(telechargement=RapportTelechargement(statut="nouvelle", avertissements=["fraicheur_inconnue"]),
                 indetermines_precedent=3, indetermines_courant=3)  # fmt: skip
    assert _ids(decider(e)) == ["A01"]


def test_ALG_12_avertissements_joints_aussi_a_un_blocage():
    e = _entrees(tests_ok=False,
                 export=RapportExport(statut="ok", nombre_groupes=13, avertissements=["fichier_volumineux : x"]))  # fmt: skip
    assert _ids(decider(e)) == ["G05", "A03"]


def test_ALG_12_seuils_parametrables():
    diff = {"nouveaux": 30, "nombre_supprimes": 0, "nombre_modifies_chiffres": 0, "nombre_modifies_autres": 0}
    assert decider(_entrees(diff=diff), ParametresDecision(seuil_nouveaux=10)).decision == "attente_validation"
    assert decider(_entrees(diff=diff)).decision == "publier"


# --- invariants ---------------------------------------------------------------------------------------


def test_ALG_12_invariants_sur_toutes_les_combinaisons():
    cas_bloquants = [
        {"lecture": RapportLecture(statut="partiel")},
        {"importation": RapportImport(statut="echoue")},
        {"reconciliation": RapportReconciliation(niveau="base", statut="ecarts_nouveaux")},
        {"export": RapportExport(statut="echec", nombre_groupes=13)},
        {"tests_ok": False},
        {"verification": "echec"},
    ]
    cas_validation = [
        {"mode_sur": True},
        {"manifeste_precedent": None, "diff": None, "nombre_groupes_precedent": None},
        {"diff": {"nouveaux": 0, "nombre_supprimes": 1, "nombre_modifies_chiffres": 0, "nombre_modifies_autres": 0}},
        {"diff": {"nouveaux": 0, "nombre_supprimes": 0, "nombre_modifies_chiffres": 1, "nombre_modifies_autres": 0}},
        {"nombre_groupes_precedent": 11},
        {"noms_modifies": [{"id": "x"}]},
    ]
    for masque_b in itertools.product([False, True], repeat=len(cas_bloquants)):
        for masque_v in ((False,) * 6, (True,) * 6, (True, False, True, False, True, False)):
            sur: dict = {}
            for actif, cas in zip(masque_b, cas_bloquants, strict=True):
                if actif:
                    sur.update(cas)
            for actif, cas in zip(masque_v, cas_validation, strict=True):
                if actif:
                    sur.update(cas)
            d = decider(_entrees(**sur))
            ids = _ids(d)
            if any(masque_b):
                assert d.decision == "bloquer"  # une règle B vraie impose `bloquer`
                assert not any(i.startswith("V") for i in ids)  # une validation ne lève pas un blocage
            elif any(masque_v):
                assert d.decision == "attente_validation"
            else:
                assert d.decision == "publier" and not any(i[0] in "GV" for i in ids)


def test_ALG_12_deterministe_et_empreinte_de_la_decision():
    e = _entrees(mode_sur=True)
    assert decider(e) == decider(e)
    a, b = decider(e), decider(_entrees(mode_sur=True, manifeste_courant=_manifeste(donnees="f" * 64)))
    assert a.rapport_sha256 != b.rapport_sha256 and len(a.rapport_sha256) == 64
    assert a.decision == b.decision


def test_ALG_12_decision_json_canonique_sans_secret_ni_heure():
    d = decider(_entrees(mode_sur=True))
    octets = serialiser_decision(d)
    texte = octets.decode()
    assert json.loads(texte)["rapport_sha256"] == d.rapport_sha256 and texte.endswith("\n")
    for interdit in ("token", "secret", "CLOUDFLARE", "password", "T00:"):
        assert interdit.lower() not in texte.lower()
    assert octets == serialiser_decision(decider(_entrees(mode_sur=True)))


@pytest.mark.parametrize(
    "decision, approuvee, attendu",
    [
        ("publier", False, True),
        ("publier", True, True),
        ("attente_validation", False, False),
        ("attente_validation", True, True),
        ("bloquer", True, False),  # une validation humaine ne lève jamais un blocage
        ("rien_a_faire", True, False),
    ],
)
def test_ALG_12_deploiement_autorise(decision, approuvee, attendu):
    d = dataclasses.replace(decider(_entrees()), decision=decision, rapport_sha256="h" * 64)
    assert deploiement_autorise(d, approuvee, "h" * 64) is attendu


def test_ALG_12_le_deploiement_ne_publie_que_l_artefact_decide():
    d = decider(_entrees())
    assert deploiement_autorise(d, False, d.rapport_sha256) is True
    assert deploiement_autorise(d, True, "autre-artefact") is False  # empreinte différente : refusé


def test_ALG_12_doit_traiter_avant_de_telecharger_tout_le_pipeline():
    publie = _manifeste()
    assert doit_traiter(ENTREES, publie, forcer=False) is False  # rien n'a changé
    assert doit_traiter(ENTREES, publie, forcer=True) is True
    assert doit_traiter(ENTREES, None, forcer=False) is True  # aucune publication
    assert doit_traiter({**ENTREES, "archive_sha256": "n" * 64}, publie, False) is True  # nouvelle archive
    # archive identique, mais version des règles différente : on traite
    assert doit_traiter({**ENTREES, "version_regles_classification": "r2"}, publie, False) is True
    # un référentiel qui change fait traiter
    assert doit_traiter({**ENTREES, "referentiels_sha256": "r" * 64}, publie, False) is True


# --- avec le vrai manifeste d'ALG-11 ----------------------------------------------------------------------


def _lots():
    lots = []
    for n in (1, 2, 3, 489, 1017, 1302):
        doc = json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))
        s = normaliser_scrutin(doc).scrutin
        lots.append(rattacher(extraire_scrutin(s, f"json/{s.id}.json", "a" * 64, None, "t", "v")))
    return lots


def _contexte(**sur):
    base = dict(archive_sha256="b" * 64, type_empreinte="fichier", donnees_du="d", version_etl="e",
                version_regles_classification="r", statut_reconciliation="ecarts_connus",
                nombre_scrutins_base=6)  # fmt: skip
    return ContexteExport(**(base | sur))


def test_ALG_12_avec_le_manifeste_exporte_par_alg11():
    fichiers, rapport = exporter(_lots(), ReferentielsExport({}, {}), _contexte())
    assert rapport.statut == "ok"
    manifeste = json.loads(fichiers["manifeste.json"])
    base = dict(
        lecture=RapportLecture(statut="complet"), importation=RapportImport(statut="termine"),
        reconciliation=RapportReconciliation(niveau="base", statut="ecarts_connus"),
        export=rapport, tests_ok=True, verification="ok", manifeste_courant=manifeste, mode_sur=False,
    )  # fmt: skip
    # première publication : validation humaine
    d = decider(EntreesDecision(**base))
    assert (d.decision, _ids(d)) == ("attente_validation", ["V01"])
    # même exécution rejouée sur la version publiée : rien à faire
    d = decider(EntreesDecision(**base, manifeste_precedent=manifeste, diff=calculer_diff(manifeste["scrutins"], manifeste),
                                nombre_groupes_precedent=rapport.nombre_groupes))  # fmt: skip
    assert d.decision == "rien_a_faire"
    # un chiffre officiel d'un scrutin publié a changé : attente de validation (V03)
    precedent = json.loads(json.dumps(manifeste))
    precedent["empreinte_entrees"] = "autre"  # entrées différentes : on poursuit
    precedent["scrutins"]["VTANR5L17V2"]["empreinte_chiffres"] = "0" * 64
    diff = calculer_diff(manifeste["scrutins"], precedent)
    d = decider(EntreesDecision(**base, manifeste_precedent=precedent, diff=diff,
                                nombre_groupes_precedent=rapport.nombre_groupes))  # fmt: skip
    assert (d.decision, _ids(d)) == ("attente_validation", ["V03"])
    assert d.diff["modifies_chiffres"] == ["VTANR5L17V2"] and d.donnees_sha256 == manifeste["donnees_sha256"]
