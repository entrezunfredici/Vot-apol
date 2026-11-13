"""Tests ALG-02 : cas limites et exemples chiffrés de la fiche (fixtures = vrais scrutins)."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import (
    _Contexte,
    aplatir_votants,
    booleen,
    date_iso,
    entier,
    enum_ferme,
    normaliser_scrutin,
    reference,
    texte,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
DOSSIER_REEL = Path(__file__).parents[3] / "Scrutins.json"


def _doc(n: int) -> dict:
    return json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))


def _groupes(doc: dict) -> list[dict]:
    g = doc["scrutin"]["ventilationVotes"]["organe"]["groupes"]["groupe"]
    return g if isinstance(g, list) else [g]


def _codes(anomalies) -> set[str]:
    return {a.code for a in anomalies}


# --- fonctions de base -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "valeur, attendu",
    [("0", 0), ("12", 12), (12, 12), (0, 0)],
)
def test_ALG_02_entier_valide(valeur, attendu):
    ctx = _Contexte()
    assert entier(valeur, ctx, "x") == attendu and ctx.nb_erreurs == 0


@pytest.mark.parametrize("valeur", ["012", "", "1.0", " 1", "-1", "+1", None, True, 1.5, -1, "１", "9" * 5000])
def test_ALG_02_entier_invalide(valeur):
    ctx = _Contexte()
    assert entier(valeur, ctx, "x") is None and ctx.nb_erreurs == 1


@pytest.mark.parametrize("valeur, attendu", [("true", True), ("false", False)])
def test_ALG_02_booleen_valide(valeur, attendu):
    assert booleen(valeur, _Contexte(), "x") is attendu


@pytest.mark.parametrize("valeur", ["True", "FALSE", 1, True, None, ""])
def test_ALG_02_booleen_invalide(valeur):
    ctx = _Contexte()
    assert booleen(valeur, ctx, "x") is None and ctx.nb_erreurs == 1


@pytest.mark.parametrize("valeur", ["2026-02-30", "2026-2-3", "20260203", "0000-01-01", None, 5])
def test_ALG_02_date_invalide(valeur):
    ctx = _Contexte()
    assert date_iso(valeur, ctx, "x") is None and ctx.nb_erreurs == 1


def test_ALG_02_date_valide_conservee_telle_quelle():
    assert date_iso("2024-02-29", _Contexte(), "x") == "2024-02-29"


def test_ALG_02_texte_nfc_trim_et_vide():
    ctx = _Contexte()
    assert texte("  éte  ", ctx, "x") == "éte"
    assert _codes(ctx.avertissements) == {"espaces_retires"}
    assert texte("", _Contexte(), "x", requis=False) is None
    assert texte(None, _Contexte(), "x", requis=False) is None
    ctx = _Contexte()
    assert texte(None, ctx, "x") is None and ctx.nb_erreurs == 1
    ctx = _Contexte()
    assert texte(5, ctx, "x", requis=False) is None and ctx.nb_erreurs == 1


def test_ALG_02_texte_ne_modifie_pas_l_interieur():
    assert texte("a  b", _Contexte(), "x") == "a  b"


def test_ALG_02_reference_po0_non_resolue_sans_erreur():
    ctx = _Contexte()
    assert reference("PO0", "PO", ctx, "x") == (None, False) and ctx.nb_erreurs == 0
    assert reference("PO845401", "PO", ctx, "x") == ("PO845401", True) and ctx.nb_erreurs == 0


@pytest.mark.parametrize("valeur, prefixe", [("po845401", "PO"), ("", "PO"), ("PA0", "PA"),
                                              ("PA012", "PA"), ("PO1", "PA"), (None, "PO")])
def test_ALG_02_reference_invalide(valeur, prefixe):
    ctx = _Contexte()
    reference(valeur, prefixe, ctx, "x")
    assert ctx.nb_erreurs == 1


def test_ALG_02_enum_ferme():
    ctx = _Contexte()
    assert enum_ferme("adopté", {"adopté": "adopte"}, ctx, "x") == "adopte"
    assert enum_ferme("XYZ", {"adopté": "adopte"}, ctx, "x") is None
    assert _codes(ctx.erreurs) == {"valeur_inconnue"}


@pytest.mark.parametrize(
    "noeud, attendu",
    [
        (None, 0),
        ({"votant": {"a": 1}}, 1),
        ({"votant": [{"a": 1}, {"a": 2}]}, 2),
        ([None, None], 0),
        ([None, {"votant": [{"a": 1}, {"a": 2}]}], 2),
        ([{"votant": {"a": 1}}, {"votant": {"a": 2}}], 2),
    ],
)
def test_ALG_02_aplatir_votants(noeud, attendu):
    ctx = _Contexte()
    assert len(aplatir_votants(noeud, ctx, "x")) == attendu and ctx.nb_erreurs == 0


@pytest.mark.parametrize(
    "noeud",
    [{"votant": None}, {"votant": [1]}, {"autre": {}}, {"votant": {}, "x": 1}, "texte", 5],
)
def test_ALG_02_aplatir_votants_forme_invalide(noeud):
    ctx = _Contexte()
    assert aplatir_votants(noeud, ctx, "x") == [] and ctx.nb_erreurs == 1


# --- exemples chiffrés sur de vrais scrutins ------------------------------------------------


def test_ALG_02_scrutin_1017_listes_objet_unique_et_cause():
    r = normaliser_scrutin(_doc(1017))
    assert r.scrutin is not None and r.erreurs == []
    g = next(g for g in r.scrutin.groupes if g.organe_ref == "PO845407")
    pours = [v for v in g.votants if v.position == "pour"]
    assert len(pours) >= 2 and any(v.par_delegation for v in pours)
    assert not [v for v in g.votants if v.position == "contre"]  # contres: null -> liste vide
    nv = [v for v in g.votants if v.position == "non_votant"]
    assert len(nv) == 1 and nv[0].cause == "PAN"


def test_ALG_02_scrutin_489_groupes_po0():
    r = normaliser_scrutin(_doc(489))
    assert r.scrutin is not None
    assert [g.rang for g in r.scrutin.groupes] == list(range(1, 13))
    assert all(g.organe_ref is None for g in r.scrutin.groupes)
    assert [a.code for a in r.avertissements].count("groupe_non_identifie") == 12


def test_ALG_02_scrutin_1302_un_seul_groupe_non_identifie():
    r = normaliser_scrutin(_doc(1302))
    assert r.scrutin is not None
    sans_ref = [g for g in r.scrutin.groupes if g.organe_ref is None]
    assert [g.rang for g in sans_ref] == [sans_ref[0].rang] and len(sans_ref) == 1


def test_ALG_02_scrutin_1_motion_de_censure():
    r = normaliser_scrutin(_doc(1))
    s = r.scrutin
    assert s is not None
    assert (s.numero, s.legislature, s.date_scrutin) == (1, 17, "2024-10-08")
    assert (s.type_vote_code, s.sort_code) == ("MOC", "rejete")
    assert (s.pour, s.contre, s.abstentions, s.non_votants, s.non_votants_volontaires) == (
        197, 0, 0, 10, 0)
    assert s.demandeur_texte is None and s.dossier_ref is None
    assert len(s.groupes) == 12


def test_ALG_02_deterministe_et_votants_tries():
    a, b = normaliser_scrutin(_doc(1017)), normaliser_scrutin(_doc(1017))
    assert a == b
    for g in a.scrutin.groupes:
        cles = [({"pour": 0, "contre": 1, "abstention": 2, "non_votant": 3}[v.position],
                 v.acteur_ref) for v in g.votants]
        assert cles == sorted(cles)


# --- cas limites sur des copies modifiées de vrais scrutins -----------------------------------


def _modifier(n, fonction):
    doc = copy.deepcopy(_doc(n))
    fonction(doc["scrutin"])
    return normaliser_scrutin(doc)


def _un_groupe_avec(s, cle):
    return next(g for g in _groupes({"scrutin": s}) if g["vote"]["decompteNominatif"][cle])


def test_ALG_02_groupe_en_dictionnaire_unique():
    def f(s):
        s["ventilationVotes"]["organe"]["groupes"]["groupe"] = _groupes({"scrutin": s})[0]

    r = _modifier(1017, f)
    assert r.scrutin is not None and len(r.scrutin.groupes) == 1


def test_ALG_02_groupe_vide_ou_null():
    for valeur in ([], None):
        r = _modifier(1017, lambda s, v=valeur: s["ventilationVotes"]["organe"]["groupes"]
                      .__setitem__("groupe", v))
        assert r.scrutin is None and r.erreurs


def test_ALG_02_nombre_en_entier_json_accepte():
    r = _modifier(1, lambda s: s["syntheseVote"]["decompte"].__setitem__("pour", 197))
    assert r.scrutin is not None and r.scrutin.pour == 197


@pytest.mark.parametrize("valeur", ["012", "", "1.0", True])
def test_ALG_02_compteur_mal_forme(valeur):
    r = _modifier(1, lambda s: s["syntheseVote"]["decompte"].__setitem__("pour", valeur))
    assert r.scrutin is None and _codes(r.erreurs) == {"format_entier"}
    assert r.erreurs[0].chemin == "scrutin.syntheseVote.decompte.pour"


def test_ALG_02_par_delegation_mal_forme():
    def f(s):
        _un_groupe_avec(s, "pours")["vote"]["decompteNominatif"]["pours"]["votant"][0][
            "parDelegation"] = "True"

    r = _modifier(1017, f)
    assert r.scrutin is None and _codes(r.erreurs) == {"format_booleen"}


def test_ALG_02_date_impossible():
    r = _modifier(1, lambda s: s.__setitem__("dateScrutin", "2026-02-30"))
    assert r.scrutin is None and _codes(r.erreurs) == {"format_date"}


@pytest.mark.parametrize("valeur", ["po845401", ""])
def test_ALG_02_reference_de_groupe_mal_formee(valeur):
    r = _modifier(1017, lambda s: _groupes({"scrutin": s})[0].__setitem__("organeRef", valeur))
    assert r.scrutin is None and _codes(r.erreurs) == {"format_reference"}


def test_ALG_02_valeurs_inconnues_de_champs_fermes():
    for chemin, valeur in [("typeVote.codeTypeVote", "XYZ"), ("sort.code", "annulé")]:
        a, b = chemin.split(".")
        r = _modifier(1, lambda s, a=a, b=b, v=valeur: s[a].__setitem__(b, v))
        assert r.scrutin is None and _codes(r.erreurs) == {"valeur_inconnue"}


def _premier_votant(s, position_cle):
    v = _un_groupe_avec(s, position_cle)["vote"]["decompteNominatif"][position_cle]["votant"]
    return v if isinstance(v, dict) else v[0]


def test_ALG_02_cause_inconnue():
    r = _modifier(1017, lambda s: _premier_votant(s, "nonVotants").__setitem__(
        "causePositionVote", "ABC"))
    assert r.scrutin is None and _codes(r.erreurs) == {"valeur_inconnue"}


def test_ALG_02_non_votant_sans_cause_est_un_avertissement():
    def f(s):
        v = _un_groupe_avec(s, "nonVotants")["vote"]["decompteNominatif"]["nonVotants"]["votant"]
        (v if isinstance(v, dict) else v[0]).pop("causePositionVote")

    r = _modifier(1017, f)
    assert r.scrutin is not None and "non_votant_sans_cause" in _codes(r.avertissements)


def test_ALG_02_cause_sur_un_votant_pour():
    def f(s):
        v = _un_groupe_avec(s, "pours")["vote"]["decompteNominatif"]["pours"]["votant"]
        (v if isinstance(v, dict) else v[0])["causePositionVote"] = "MG"

    r = _modifier(1017, f)
    assert r.scrutin is None and _codes(r.erreurs) == {"cause_incoherente"}


def test_ALG_02_depute_dans_deux_groupes():
    def f(s):
        gs = _groupes({"scrutin": s})
        src = gs[0]["vote"]["decompteNominatif"]
        autre = next(g for g in gs[1:] if g["vote"]["decompteNominatif"]["pours"])
        v = autre["vote"]["decompteNominatif"]["pours"]["votant"]
        un = v if isinstance(v, dict) else v[0]
        src["pours"] = {"votant": [copy.deepcopy(un)]}

    r = _modifier(1017, f)
    assert r.scrutin is None and _codes(r.erreurs) == {"depute_en_double"}


def test_ALG_02_cle_inconnue_est_un_avertissement():
    r = _modifier(1, lambda s: s.__setitem__("foo", 1))
    assert r.scrutin is not None
    assert [(a.chemin, a.code) for a in r.avertissements] == [("scrutin.foo", "champ_inconnu")]


def test_ALG_02_cle_requise_absente():
    r = _modifier(1, lambda s: s.pop("titre"))
    assert r.scrutin is None and [(e.chemin, e.code) for e in r.erreurs] == [
        ("scrutin.titre", "champ_requis")]


def test_ALG_02_num_place_ignore_sans_avertissement():
    r = normaliser_scrutin(_doc(1017))
    assert "numPlace" not in " ".join(a.chemin for a in r.avertissements)
    assert r.avertissements == []


def test_ALG_02_position_majoritaire_casse_et_inconnue():
    r = _modifier(1017, lambda s: _groupes({"scrutin": s})[0]["vote"].__setitem__(
        "positionMajoritaire", "Pour"))
    assert r.scrutin.groupes[0].position_majoritaire_source == "pour" and not r.avertissements
    r = _modifier(1017, lambda s: _groupes({"scrutin": s})[0]["vote"].__setitem__(
        "positionMajoritaire", "inconnue"))
    assert r.scrutin.groupes[0].position_majoritaire_source == "inconnue"
    assert _codes(r.avertissements) == {"position_majoritaire_inconnue"}


def test_ALG_02_mode_de_publication_autre():
    r = _modifier(1, lambda s: s.__setitem__("modePublicationDesVotes", "Autre"))
    assert r.scrutin is None and _codes(r.erreurs) == {"mode_publication_non_gere"}


def test_ALG_02_espace_de_noms_modifie():
    r = _modifier(1, lambda s: s.__setitem__("@xmlns", "http://exemple.org"))
    assert r.scrutin is not None and _codes(r.avertissements) == {"schema_modifie"}


def test_ALG_02_racine_invalide():
    assert normaliser_scrutin({"autre": {}}).scrutin is None
    assert normaliser_scrutin([]).erreurs[0].code == "structure"


def test_ALG_02_erreurs_plafonnees_a_50_mais_scrutin_refuse():
    def f(s):
        for g in _groupes({"scrutin": s}):
            g["nombreMembresGroupe"] = "x"
            for cle in g["vote"]["decompteVoix"]:
                g["vote"]["decompteVoix"][cle] = "x"
        for cle in s["syntheseVote"]["decompte"]:
            s["syntheseVote"]["decompte"][cle] = "x"

    r = _modifier(1017, f)
    assert r.scrutin is None and len(r.erreurs) == 50


def test_ALG_02_mises_au_point_et_dysfonctionnements_distincts():
    n = next(
        n for n in range(1, 8878)
        if json.loads((DOSSIER_REEL / "json" / f"VTANR5L17V{n}.json").read_text("utf-8"))[
            "scrutin"]["miseAuPoint"]["pours"] is not None
    ) if (DOSSIER_REEL / "json").is_dir() else None
    if n is None:
        pytest.skip("données réelles absentes")
    doc = json.loads((DOSSIER_REEL / "json" / f"VTANR5L17V{n}.json").read_text("utf-8"))
    r = normaliser_scrutin(doc)
    assert r.scrutin is not None
    assert r.scrutin.mises_au_point and all(
        m.origine == "mise_au_point" for m in r.scrutin.mises_au_point)
    assert all(d.origine == "dysfonctionnement" for d in r.scrutin.dysfonctionnements)


# --- intégration : les 8 877 scrutins réels ---------------------------------------------------


@pytest.mark.skipif(not (DOSSIER_REEL / "json").is_dir(), reason="données réelles absentes")
def test_ALG_02_les_8877_scrutins_reels():
    c: Counter[str] = Counter()
    avertissements: Counter[str] = Counter()
    for f in sorted((DOSSIER_REEL / "json").glob("*.json")):
        r = normaliser_scrutin(json.loads(f.read_text(encoding="utf-8")))
        assert r.scrutin is not None, (f.name, r.erreurs[:3])
        s = r.scrutin
        c["scrutins"] += 1
        c["groupes"] += len(s.groupes)
        c["sans_reference"] += sum(g.organe_ref is None for g in s.groupes)
        c.update(f"vote_{v.position}" for g in s.groupes for v in g.votants)
        c.update(f"mp_{m.position_declaree}" for m in s.mises_au_point)
        c.update(f"dys_{m.position_declaree}" for m in s.dysfonctionnements)
        c[f"type_{s.type_vote_code}"] += 1
        c[f"sort_{s.sort_code}"] += 1
        avertissements.update(a.code for a in r.avertissements)
    assert c["scrutins"] == 8877 and c["groupes"] == 106_524 and c["sans_reference"] == 146
    assert (c["vote_pour"], c["vote_contre"], c["vote_abstention"], c["vote_non_votant"]) == (
        580_652, 643_533, 75_754, 24_039)
    assert sum(v for k, v in c.items() if k.startswith("vote_")) == 1_323_978
    assert (c["mp_pour"], c["mp_contre"], c["mp_abstention"], c["mp_non_votant"],
            c["mp_non_votant_volontaire"]) == (1283, 1224, 281, 450, 5)
    assert sum(v for k, v in c.items() if k.startswith("mp_")) == 3243
    assert (c["dys_pour"], c["dys_contre"], c["dys_abstention"],
            c["dys_non_votant_volontaire"]) == (82, 57, 9, 15)
    assert (c["type_SPO"], c["type_SPS"], c["type_MOC"]) == (8780, 74, 23)
    assert (c["sort_adopte"], c["sort_rejete"]) == (3031, 5846)
    assert avertissements == Counter({"groupe_non_identifie": 146})
