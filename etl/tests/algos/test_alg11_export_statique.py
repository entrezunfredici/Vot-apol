"""Tests ALG-11 : documents, déterminisme, schémas, limites, refus, publication et archive réelle."""

import copy
import dataclasses
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import normaliser_scrutin
from etl.algos.alg04_extraction_scrutin import extraire_scrutin
from etl.algos.alg06_mises_au_point import rattacher
from etl.algos.alg08_classification import VERSION_REGLES
from etl.algos.alg11_export_statique import (
    _verifier_echantillon,
    calculer_diff,
    empreinte_chiffres,
    exporter,
    lien_officiel,
    serialiser,
)
from etl.algos.alg11_schemas import valider
from etl.cli import main
from etl.io.db import (
    appliquer_migrations,
    lire_contexte_base,
    lire_referentiels_export,
    lire_scrutins_export,
)
from etl.io.fs import (
    ErreurPublication,
    publier_fichiers,
    recuperer_publication_interrompue,
)
from etl.models import ContexteExport, LigneMiseAuPoint, ParametresExport, ReferentielsExport

RACINE = Path(__file__).parents[2]
FIXTURES = Path(__file__).parents[1] / "fixtures"
DOSSIER_REEL = RACINE.parent / "Scrutins.json"
HASH = "a" * 64
ARCHIVE = "b" * 64


def _lot(n: int):
    doc = json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))
    s = normaliser_scrutin(doc).scrutin
    return rattacher(extraire_scrutin(s, f"json/{s.id}.json", HASH, None, "t", "v"))


def _lots(numeros=(1, 2, 3, 489, 1017, 1302)):
    return [_lot(n) for n in numeros]


def _contexte(**sur) -> ContexteExport:
    base = dict(
        archive_sha256=ARCHIVE, type_empreinte="fichier", donnees_du="2026-11-18T00:00:00+00:00",
        version_etl="etl-test", version_regles_classification=VERSION_REGLES,
        statut_reconciliation="ecarts_connus", nombre_scrutins_base=6,
    )  # fmt: skip
    return ContexteExport(**(base | sur))


REFERENTIELS = ReferentielsExport(
    groupes={"PO845407": ("Ensemble pour la République", "EPR"), "PO845401": ("Rassemblement National", "RN")},
    deputes={},
)


def _exporter(lots=None, referentiels=REFERENTIELS, contexte=None, params=ParametresExport()):
    return exporter(_lots() if lots is None else lots, referentiels, contexte or _contexte(), params)


def _json(fichiers, chemin):
    return json.loads(fichiers[chemin].decode("utf-8"))


# --- contenu ------------------------------------------------------------------------------------------


def test_ALG_11_export_des_six_fixtures_valide():
    fichiers, r = _exporter()
    assert (r.statut, r.cause_echec) == ("ok", None)
    assert r.nombre_scrutins == 6 and r.nombre_fichiers == len(fichiers)
    assert sorted(f for f in fichiers if f.startswith("scrutins/")) == sorted(
        f"scrutins/VTANR5L17V{n}.json" for n in (1, 2, 3, 489, 1017, 1302))
    for chemin, octets in fichiers.items():
        assert valider(chemin, json.loads(octets)) == [], chemin


def test_ALG_11_scrutin_489_groupes_non_identifies():
    fichiers, _ = _exporter()
    d = _json(fichiers, "scrutins/VTANR5L17V489.json")
    assert len(d["groupes"]) == 12
    assert all(g["groupe_id"] is None and g["ventilation_disponible"] is False for g in d["groupes"])
    assert all(g["position_majoritaire"] is None and g["sans_vote_enregistre"] is None for g in d["groupes"])
    assert d["totaux"]["sans_vote_enregistre"] is None
    assert [g["rang"] for g in d["groupes"]] == sorted(
        (g["rang"] for g in d["groupes"]), key=lambda r: (-next(x["membres"] for x in d["groupes"] if x["rang"] == r), r))
    assert all(v[1] in range(1, 13) for v in d["votes"])  # les votes gardent leur rang de groupe


def test_ALG_11_scrutin_1_chiffres_officiels_et_source_non_exportee():
    fichiers, _ = _exporter()
    d = _json(fichiers, "scrutins/VTANR5L17V1.json")
    assert (d["numero"], d["date"], d["resultat"]) == (1, "2024-10-08", "rejete")
    assert (d["totaux"]["pour"], d["totaux"]["non_votants"]) == (197, 10)  # chiffres officiels
    assert d["categorie"] == {"valeur": "motion_censure", "methode": "metadonnee_officielle",
                              "confiance": "haute", "a_verifier": False}  # fmt: skip
    assert d["source"]["lien_officiel"] == lien_officiel(1) == "https://www.assemblee-nationale.fr/dyn/17/scrutins/1"
    assert d["source"]["archive_sha256"] == ARCHIVE and d["source"]["sha256"] == HASH
    assert d["source"]["fichier"] == "json/VTANR5L17V1.json"
    assert len(d["votes"]) == 197 + 21  # 21 non-votants nominatifs (écart connu d'ALG-05)
    assert "position_majoritaire_source" not in fichiers["scrutins/VTANR5L17V1.json"].decode()
    assert d["totaux"]["sans_vote_enregistre"] == sum(g["sans_vote_enregistre"] for g in d["groupes"])


def test_ALG_11_ordres_groupes_et_votes():
    fichiers, _ = _exporter()
    d = _json(fichiers, "scrutins/VTANR5L17V1.json")
    cles = [(-g["membres"], g["groupe_id"] or "", g["rang"]) for g in d["groupes"]]
    assert cles == sorted(cles)
    ordre = {"pour": 0, "contre": 1, "abstention": 2, "non_votant": 3}
    votes = [(v[1], ordre[v[2]], v[0]) for v in d["votes"]]
    assert votes == sorted(votes)


def test_ALG_11_groupes_et_deputes_references_par_identifiant():
    fichiers, _ = _exporter()
    g = _json(fichiers, "groupes.json")["groupes"]
    libelles = [(x["libelle"] is None, (x["libelle"] or "").casefold(), x["id"]) for x in g]
    assert libelles == sorted(libelles)  # alphabétique, non résolus à la fin
    assert [x["nombre_scrutins"] for x in g] and all(x["nombre_scrutins"] >= 1 for x in g)
    par_id = {x["id"]: x for x in g}
    assert par_id["PO845407"]["libelle"] == "Ensemble pour la République"
    assert any(x["libelle"] is None for x in g)  # non résolu : null, jamais inventé
    d = _json(fichiers, "deputes.json")["deputes"]
    assert [x["id"] for x in d] == sorted(x["id"] for x in d)
    assert all(x["nom"] is None for x in d)  # référentiel de députés vide : aucun nom inventé
    fichier_groupe = _json(fichiers, "groupes/PO845407.json")
    assert fichier_groupe["groupe_id"] == "PO845407" and fichier_groupe["libelle"] == "Ensemble pour la République"
    numeros = [ligne[1] for ligne in fichier_groupe["scrutins"]]
    assert numeros == sorted(numeros) and fichier_groupe["colonnes"][1] == "numero"


def test_ALG_11_fichier_de_groupe_compact_sans_perte_de_donnee():
    """Chaque ligne compacte redonne exactement les valeurs du scrutin (rien n'est perdu)."""
    from etl.algos.alg11_schemas import COLONNES_GROUPE

    fichiers, _ = _exporter()
    for chemin in (c for c in fichiers if c.startswith("groupes/")):
        g = _json(fichiers, chemin)
        assert g["colonnes"] == list(COLONNES_GROUPE)  # les colonnes sont nommées une seule fois
        for ligne in g["scrutins"]:
            assert len(ligne) == len(COLONNES_GROUPE)
            valeurs = dict(zip(COLONNES_GROUPE, ligne, strict=True))
            doc = _json(fichiers, f"scrutins/{valeurs['scrutin_id']}.json")
            attendu = next(x for x in doc["groupes"] if x["groupe_id"] == g["groupe_id"])
            assert (valeurs["numero"], valeurs["date"], valeurs["categorie"]) == (
                doc["numero"], doc["date"], doc["categorie"]["valeur"])  # fmt: skip
            for cle in ("membres", "pour", "contre", "abstentions", "non_votants", "sans_vote_enregistre"):
                assert valeurs[cle] == attendu[cle], (chemin, cle)
            pm = attendu["position_majoritaire"]
            assert (valeurs["position"], valeurs["raison_absence"], valeurs["exprimes"], valeurs["m"],
                    valeurs["majorite_absolue"]) == (pm["position"], pm["raison_absence"], pm["exprimes"],
                                                     pm["m"], pm["majorite_absolue"])  # fmt: skip


def test_ALG_11_schema_du_fichier_de_groupe_refuse_les_colonnes_modifiees():
    fichiers, _ = _exporter()
    chemin = next(c for c in fichiers if c.startswith("groupes/"))
    g = _json(fichiers, chemin)
    assert valider(chemin, g) == []
    assert any("colonnes" in e for e in valider(chemin, {**g, "colonnes": list(reversed(g["colonnes"]))}))
    court = {**g, "scrutins": [g["scrutins"][0][:-1]]}
    assert any("éléments attendue" in e for e in valider(chemin, court))
    mauvais = {**g, "scrutins": [[*g["scrutins"][0][:10], "peut-etre", *g["scrutins"][0][11:]]]}
    assert any("valeur parmi" in e for e in valider(chemin, mauvais))


def test_ALG_11_avertissement_de_taille_ne_vise_pas_le_manifeste():
    # `manifeste.json` n'est pas chargé par le navigateur : jamais cité dans l'avertissement de taille
    fichiers, rapport = _exporter(params=ParametresExport(max_octets_fichier_avertissement=100))
    assert len(fichiers["manifeste.json"]) > 100  # il dépasserait le seuil s'il n'était pas exclu
    avert = [a for a in rapport.avertissements if a.startswith("fichier_volumineux")]
    assert len(avert) == 1 and "manifeste.json" not in avert[0]


def test_ALG_11_index_par_mois_sans_mois_vide():
    fichiers, _ = _exporter()
    idx = _json(fichiers, "scrutins-index.json")["fragments"]
    assert [f["mois"] for f in idx] == sorted(f["mois"] for f in idx)
    assert sum(f["nombre_scrutins"] for f in idx) == 6
    for f in idx:
        assert f["fichier"] == f"scrutins-index/{f['mois']}.json" and f["nombre_scrutins"] >= 1
        lignes = _json(fichiers, f["fichier"])["scrutins"]
        assert len(lignes) == f["nombre_scrutins"] and all(x["date"].startswith(f["mois"]) for x in lignes)
    assert not any(c.startswith("scrutins-index/") and c not in {f["fichier"] for f in idx} for c in fichiers)


def test_ALG_11_stats_toutes_categories_annees():
    fichiers, _ = _exporter()
    stats = _json(fichiers, "stats.json")
    ids = [s["id"] for s in stats["selections"]]
    assert ids[0] == "toutes" and any(i.startswith("categorie:") for i in ids)
    assert any(i.startswith("annee:") for i in ids)
    assert stats["bornes"] == [20, 40, 60, 80] and len(stats["libelles_tranches"]) == 6
    toutes = stats["selections"][0]
    assert toutes["nombre_scrutins"] == 6
    assert all(x["pour"] + x["contre"] + x["abstentions"] == x["exprimes"] for x in toutes["groupes"])


def test_ALG_11_meta_qualite_manifeste():
    fichiers, r = _exporter(contexte=_contexte(ecarts_connus=[{"controle": "R07", "scrutin_id": "VTANR5L17V1",
        "detail": None, "attendu": 10, "obtenu": 21, "motif": "m", "valide_le": "2026-11-13"}]))  # fmt: skip
    meta = _json(fichiers, "meta.json")
    assert (meta["nombre_scrutins"], meta["nombre_groupes"], meta["schema"]) == (6, r.nombre_groupes, "v1")
    assert (meta["premiere_date"], meta["archive_sha256"], meta["type_empreinte"]) == ("2024-10-08", ARCHIVE, "fichier")
    assert meta["version_donnees"] == r.version_donnees == r.donnees_sha256[:16]
    q = _json(fichiers, "qualite.json")
    assert q["statut_reconciliation"] == "ecarts_connus" and q["modifications"] is None
    assert len(q["ecarts_connus"]) == 1 and q["noms_non_resolus"]["deputes"] > 0
    assert sum(q["classification"]["par_categorie"].values()) == 6
    m = _json(fichiers, "manifeste.json")
    assert set(m["scrutins"]) == {f"VTANR5L17V{n}" for n in (1, 2, 3, 489, 1017, 1302)}
    assert all(set(v) == {"source_hash", "empreinte_chiffres"} for v in m["scrutins"].values())
    assert m["donnees_sha256"] == r.donnees_sha256 and len(m["empreinte_entrees"]) == 64
    # donnees_sha256 couvre tous les fichiers sauf manifeste.json et meta.json
    lignes = "".join(f"{c}\t{hashlib.sha256(o).hexdigest()}\n" for c, o in sorted(fichiers.items())
                     if c not in ("manifeste.json", "meta.json"))  # fmt: skip
    assert hashlib.sha256(lignes.encode()).hexdigest() == r.donnees_sha256


def test_ALG_11_mise_au_point_rattachee_correction_sans_toucher_aux_chiffres():
    lot = _lot(2)
    g = next(g for g in lot.groupes if g.pour >= 1 and g.groupe_id)
    vote = next(v for v in lot.votes if v.groupe_rang == g.rang and v.position == "pour")
    mise = LigneMiseAuPoint(lot.scrutin.id, vote.depute_id, "mise_au_point", "contre", 0, g.rang,
                            g.groupe_id, "pour", "rattachee", "modifie_position")  # fmt: skip
    lot2 = dataclasses.replace(lot, mises_au_point=[mise])
    fichiers, _ = _exporter(lots=[lot2], contexte=_contexte(nombre_scrutins_base=1))
    d = _json(fichiers, f"scrutins/{lot.scrutin.id}.json")
    groupe = next(x for x in d["groupes"] if x["rang"] == g.rang)
    assert groupe["pour"] == g.pour  # le chiffre officiel n'est jamais modifié
    c = groupe["correction_mise_au_point"]
    assert (c["pour_corrige"], c["contre_corrige"]) == (g.pour - 1, g.contre + 1)
    assert d["mises_au_point"][0]["statut"] == "rattachee" and d["dysfonctionnements"] == []


def test_ALG_11_mise_au_point_introuvable_et_dysfonctionnement_a_part():
    lot = _lot(2)
    mises = [
        LigneMiseAuPoint(lot.scrutin.id, "PA-inconnu", "mise_au_point", "pour", 0),
        LigneMiseAuPoint(lot.scrutin.id, "PA-autre", "dysfonctionnement", "contre", 1),
    ]
    lot2 = dataclasses.replace(lot, mises_au_point=mises)
    fichiers, r = _exporter(lots=[lot2], contexte=_contexte(nombre_scrutins_base=1))
    assert r.statut == "ok"
    d = _json(fichiers, f"scrutins/{lot.scrutin.id}.json")
    assert [(m["depute_id"], m["statut"]) for m in d["mises_au_point"]] == [("PA-inconnu", "introuvable")]
    assert [m["depute_id"] for m in d["dysfonctionnements"]] == ["PA-autre"]
    assert all(g["correction_mise_au_point"] is None for g in d["groupes"])


# --- déterminisme ---------------------------------------------------------------------------------------


def test_ALG_11_meme_entree_memes_octets():
    a, ra = _exporter()
    b, rb = _exporter(lots=copy.deepcopy(_lots()))
    assert a == b and ra.donnees_sha256 == rb.donnees_sha256


def test_ALG_11_ordre_d_entree_sans_effet():
    a, _ = _exporter(lots=_lots())
    b, _ = _exporter(lots=list(reversed(_lots())))
    assert a == b


def test_ALG_11_serialisation_canonique():
    assert serialiser({"b": 1, "a": "é"}) == '{"a":"é","b":1}\n'.encode()
    assert not serialiser({"a": 1}).startswith(b"\xef\xbb\xbf")
    with pytest.raises(ValueError):
        serialiser({"a": float("nan")})
    with pytest.raises(ValueError):
        serialiser({"a": float("inf")})


def test_ALG_11_aucune_heure_d_horloge_ni_couleur_ni_score():
    fichiers, _ = _exporter(contexte=_contexte(donnees_du="2000-01-01T00:00:00+00:00"))
    for octets in fichiers.values():
        texte = octets.decode()
        assert "couleur" not in texte and "score" not in texte and "rang_groupe" not in texte
    assert "2000-01-01T00:00:00+00:00" in fichiers["meta.json"].decode()  # valeur lue, non calculée


# --- refus ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("statut", ["ecarts_nouveaux", "ecarts_informatifs", "inconnu"])
def test_ALG_11_reconciliation_non_admise_refuse_d_exporter(statut):
    fichiers, r = _exporter(contexte=_contexte(statut_reconciliation=statut))
    assert (r.statut, r.cause_echec, fichiers) == ("echec", "reconciliation_refusee", {})


def test_ALG_11_base_vide_echec():
    fichiers, r = _exporter(lots=[], contexte=_contexte(nombre_scrutins_base=0))
    assert (r.statut, r.cause_echec, fichiers) == ("echec", "aucun_scrutin", {})


def test_ALG_11_flux_non_trie_refuse():
    flux = iter(list(reversed(_lots())))
    fichiers, r = exporter(flux, REFERENTIELS, _contexte())
    assert (r.statut, r.cause_echec) == ("echec", "ordre_invalide")


def test_ALG_11_trop_de_fichiers_echec_et_avertissement():
    _, r = _exporter(params=ParametresExport(max_fichiers_echec=10))
    assert (r.statut, r.cause_echec) == ("echec", "trop_de_fichiers")
    fichiers, r = _exporter(params=ParametresExport(max_fichiers_avertissement=10))
    assert r.statut == "ok" and any(a.startswith("nombre_fichiers_eleve") for a in r.avertissements)


def test_ALG_11_fichier_trop_gros_echec_et_avertissement():
    _, r = _exporter(params=ParametresExport(max_octets_fichier_echec=1000))
    assert (r.statut, r.cause_echec) == ("echec", "fichier_trop_gros")
    _, r = _exporter(params=ParametresExport(max_octets_fichier_avertissement=1000))
    assert r.statut == "ok" and any(a.startswith("fichier_volumineux") for a in r.avertissements)


def test_ALG_11_meta_different_des_comptes_de_la_base_echec():
    _, r = _exporter(contexte=_contexte(nombre_scrutins_base=7))
    assert (r.statut, r.cause_echec) == ("echec", "references_invalides")


def test_ALG_11_effectif_incoherent_erreur_de_donnee():
    lot = _lot(2)
    g = dataclasses.replace(lot.groupes[0], membres=0)
    lot2 = dataclasses.replace(lot, groupes=[g, *lot.groupes[1:]])
    _, r = _exporter(lots=[lot2], contexte=_contexte(nombre_scrutins_base=1))
    assert (r.statut, r.cause_echec) == ("echec", "erreur_donnee")


def test_ALG_11_echantillon_detecte_un_chiffre_different():
    lot = _lot(2)
    fichiers, _ = _exporter(lots=[lot], contexte=_contexte(nombre_scrutins_base=1))
    assert _verifier_echantillon(fichiers, {lot.scrutin.id: lot}) is None
    doc = json.loads(fichiers[f"scrutins/{lot.scrutin.id}.json"])
    doc["totaux"]["pour"] += 1
    fichiers[f"scrutins/{lot.scrutin.id}.json"] = serialiser(doc)
    assert "totaux.pour" in _verifier_echantillon(fichiers, {lot.scrutin.id: lot})
    doc["totaux"]["pour"] -= 1
    doc["votes"].pop()
    fichiers[f"scrutins/{lot.scrutin.id}.json"] = serialiser(doc)
    assert "votes" in _verifier_echantillon(fichiers, {lot.scrutin.id: lot})


# --- schémas --------------------------------------------------------------------------------------------


def test_ALG_11_validateur_de_schema():
    fichiers, _ = _exporter()
    meta = _json(fichiers, "meta.json")
    assert valider("meta.json", meta) == []
    assert any("champ manquant" in e for e in valider("meta.json", {k: v for k, v in meta.items() if k != "schema"}))
    assert any("champ inattendu" in e for e in valider("meta.json", {**meta, "extra": 1}))
    assert any("entier attendu" in e for e in valider("meta.json", {**meta, "nombre_scrutins": "6"}))
    assert any("entier attendu" in e for e in valider("meta.json", {**meta, "nombre_scrutins": True}))
    doc = _json(fichiers, "scrutins/VTANR5L17V2.json")
    doc["votes"][0][2] = "peut-etre"
    assert any("valeur parmi" in e for e in valider("scrutins/VTANR5L17V2.json", doc))
    doc["votes"][0] = ["x"]
    assert any("éléments attendue" in e for e in valider("scrutins/VTANR5L17V2.json", doc))
    assert valider("inconnu.json", {}) == ["inconnu.json : aucun schéma pour ce fichier"]


# --- manifeste et différences ----------------------------------------------------------------------------


def test_ALG_11_empreinte_chiffres_sensible_aux_chiffres_pas_aux_autres_champs():
    fichiers, _ = _exporter()
    doc = _json(fichiers, "scrutins/VTANR5L17V2.json")
    e0 = empreinte_chiffres(doc)
    doc2 = copy.deepcopy(doc)
    doc2["titre"] = "autre titre"
    doc2["categorie"]["valeur"] = "autre"
    assert empreinte_chiffres(doc2) == e0  # un titre ou une catégorie ne sont pas des chiffres
    for modif in (
        lambda d: d["totaux"].__setitem__("pour", d["totaux"]["pour"] + 1),
        lambda d: d["groupes"][0].__setitem__("pour", d["groupes"][0]["pour"] + 1),
        lambda d: d["votes"].pop(),
        lambda d: d.__setitem__("resultat", "autre"),
    ):
        d = copy.deepcopy(doc)
        modif(d)
        assert empreinte_chiffres(d) != e0


def test_ALG_11_diff_avec_le_manifeste_publie():
    fichiers, _ = _exporter()
    courant = _json(fichiers, "manifeste.json")["scrutins"]
    assert calculer_diff(courant, None) is None  # aucune publication
    precedent = {"scrutins": copy.deepcopy(courant)}
    d = calculer_diff(courant, precedent)
    assert (d["nouveaux"], d["nombre_supprimes"], d["nombre_modifies_chiffres"], d["nombre_modifies_autres"]) == (0, 0, 0, 0)
    precedent["scrutins"]["VTANR5L17V1"]["empreinte_chiffres"] = "0" * 64
    precedent["scrutins"]["VTANR5L17V2"]["source_hash"] = "0" * 64
    precedent["scrutins"]["VTANR5L17V99"] = {"source_hash": "x", "empreinte_chiffres": "y"}
    del precedent["scrutins"]["VTANR5L17V3"]
    d = calculer_diff(courant, precedent)
    assert d["modifies_chiffres"] == ["VTANR5L17V1"] and d["modifies_autres"] == ["VTANR5L17V2"]
    assert d["supprimes"] == ["VTANR5L17V99"] and d["nouveaux"] == 1


def test_ALG_11_qualite_porte_les_modifications_depuis_la_publication():
    fichiers, _ = _exporter()
    precedent = {"scrutins": copy.deepcopy(_json(fichiers, "manifeste.json")["scrutins"])}
    precedent["scrutins"]["VTANR5L17V1"]["empreinte_chiffres"] = "0" * 64
    _, r = _exporter(contexte=_contexte(manifeste_precedent=precedent))
    assert r.statut == "ok"
    fichiers2, _ = _exporter(contexte=_contexte(manifeste_precedent=precedent))
    assert _json(fichiers2, "qualite.json")["modifications"]["modifies_chiffres"] == ["VTANR5L17V1"]


# --- publication du répertoire --------------------------------------------------------------------------


def test_ALG_11_publication_premiere_puis_remplacement(tmp_path):
    sortie = tmp_path / "data"
    publier_fichiers({"a.json": b"1", "d/b.json": b"2"}, sortie)
    assert (sortie / "a.json").read_bytes() == b"1" and (sortie / "d" / "b.json").read_bytes() == b"2"
    publier_fichiers({"c.json": b"3"}, sortie)
    assert sorted(p.name for p in sortie.iterdir()) == ["c.json"]  # aucun fichier périmé
    assert not (tmp_path / "data.tmp").exists() and not (tmp_path / "data.precedent").exists()


def test_ALG_11_echec_de_publication_conserve_l_ancienne_version(tmp_path):
    sortie = tmp_path / "data"
    publier_fichiers({"a.json": b"1"}, sortie)
    # « a.json » est à la fois un fichier et un dossier : l'écriture échoue sur toute plateforme
    with pytest.raises(ErreurPublication):
        publier_fichiers({"a.json": b"x", "a.json/b.json": b"y"}, sortie)
    assert (sortie / "a.json").read_bytes() == b"1"  # l'ancienne version est intacte
    assert sorted(p.name for p in sortie.iterdir()) == ["a.json"]
    assert not (tmp_path / "data.tmp").exists() and not (tmp_path / "data.precedent").exists()


def test_ALG_11_publication_interrompue_restauree(tmp_path):
    sortie = tmp_path / "data"
    precedent = tmp_path / "data.precedent"
    precedent.mkdir()
    (precedent / "a.json").write_bytes(b"ancienne")
    assert recuperer_publication_interrompue(sortie) is True  # sortie absente : on restaure
    assert (sortie / "a.json").read_bytes() == b"ancienne" and not precedent.exists()
    # nouvelle version en place et ancienne orpheline : l'ancienne est supprimée
    precedent.mkdir()
    assert recuperer_publication_interrompue(sortie) is False and not precedent.exists()
    assert (sortie / "a.json").exists()


def test_ALG_11_temporaire_perime_vide_au_depart(tmp_path):
    sortie = tmp_path / "data"
    (tmp_path / "data.tmp").mkdir()
    (tmp_path / "data.tmp" / "perime.json").write_bytes(b"x")
    publier_fichiers({"a.json": b"1"}, sortie)
    assert sorted(p.name for p in sortie.iterdir()) == ["a.json"]


# --- de bout en bout : import des fixtures puis export (CLI) ----------------------------------------------


@pytest.fixture
def base_importee(tmp_path):
    archive = tmp_path / "archive"
    (archive / "json").mkdir(parents=True)
    for f in FIXTURES.glob("VTANR5L17V*.json"):
        shutil.copy(f, archive / "json" / f.name)
    db = tmp_path / "v.db"
    conn = sqlite3.connect(db)
    appliquer_migrations(conn)
    conn.close()
    main(["import", "--zip", str(archive), "--db", str(db), "--journal-dir", str(tmp_path / "j")])
    return db


def _octets_du_repertoire(dossier: Path) -> dict[str, bytes]:
    return {p.relative_to(dossier).as_posix(): p.read_bytes() for p in sorted(dossier.rglob("*")) if p.is_file()}


def test_ALG_11_cli_export_de_bout_en_bout_et_deterministe(base_importee, tmp_path, capsys):
    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    assert main(["export", "--db", str(base_importee), "--out", str(out1)]) == 0
    assert main(["export", "--db", str(base_importee), "--out", str(out2)]) == 0
    a, b = _octets_du_repertoire(out1), _octets_du_repertoire(out2)
    assert a == b and len(a) >= 20
    meta = json.loads(a["meta.json"])
    assert meta["nombre_scrutins"] == 6 and meta["nombre_groupes"] >= 12
    entrees = json.loads(a["manifeste.json"])["entrees"]
    # l'empreinte des entrées couvre l'archive, le code des algorithmes et les règles (ALG-12.1)
    assert len(entrees["versions_algorithmes"]) == 64 and len(entrees["archive_sha256"]) == 64
    assert entrees["version_regles_classification"] == VERSION_REGLES
    qualite = json.loads(a["qualite.json"])
    assert qualite["statut_reconciliation"] == "ecarts_connus"
    assert sorted((e["controle"], e["detail"]) for e in qualite["ecarts_connus"]) == [("R07", None), ("R08", "non_votant")]
    for chemin, octets in a.items():
        assert valider(chemin, json.loads(octets)) == [], chemin
    assert '"statut": "ok"' in capsys.readouterr().out


def test_ALG_11_cli_ecart_nouveau_refuse_et_conserve_la_version_publiee(base_importee, tmp_path):
    out = tmp_path / "out"
    assert main(["export", "--db", str(base_importee), "--out", str(out)]) == 0
    avant = _octets_du_repertoire(out)
    conn = sqlite3.connect(base_importee)
    conn.execute("UPDATE scrutin_totals SET pour = pour + 1 WHERE scrutin_id = 'VTANR5L17V2'")
    conn.commit()
    conn.close()
    assert main(["export", "--db", str(base_importee), "--out", str(out)]) == 1
    assert _octets_du_repertoire(out) == avant  # la version précédente est intacte
    assert not (tmp_path / "out.tmp").exists()


def test_ALG_11_cli_manifeste_precedent_et_entrees_illisibles(base_importee, tmp_path):
    out = tmp_path / "out"
    assert main(["export", "--db", str(base_importee), "--out", str(out)]) == 0
    manifeste = out / "manifeste.json"
    out2 = tmp_path / "out2"
    assert main(["export", "--db", str(base_importee), "--out", str(out2), "--manifeste-precedent", str(manifeste)]) == 0
    q = json.loads((out2 / "qualite.json").read_text(encoding="utf-8"))
    assert q["modifications"]["nouveaux"] == 0 and q["modifications"]["nombre_modifies_chiffres"] == 0
    assert main(["export", "--db", str(base_importee), "--out", str(out2), "--manifeste-precedent", str(tmp_path / "absent.json")]) == 2
    assert main(["export", "--db", str(tmp_path / "absente.db"), "--out", str(out2)]) == 2


def test_ALG_11_lecture_de_la_base(base_importee):
    conn = sqlite3.connect(base_importee)
    try:
        lots = list(lire_scrutins_export(conn))
        assert [lot.scrutin.numero for lot in lots] == sorted(lot.scrutin.numero for lot in lots) == [1, 2, 3, 489, 1017, 1302]
        base = lire_contexte_base(conn)
        assert base["nombre_scrutins"] == 6 and len(base["archive_sha256"]) == 64 and base["donnees_du"]
        assert isinstance(lire_referentiels_export(conn), ReferentielsExport)
    finally:
        conn.close()


# --- archive réelle complète ------------------------------------------------------------------------------


@pytest.mark.skipif(not DOSSIER_REEL.exists(), reason="archive réelle absente")
def test_ALG_11_archive_complete_chiffres_de_la_fiche(tmp_path):
    db = tmp_path / "reel.db"
    conn = sqlite3.connect(db)
    appliquer_migrations(conn)
    conn.close()
    main(["import", "--zip", str(DOSSIER_REEL), "--db", str(db), "--journal-dir", str(tmp_path / "j")])
    out = tmp_path / "out"
    assert main(["export", "--db", str(db), "--out", str(out)]) == 0
    fichiers = _octets_du_repertoire(out)
    meta = json.loads(fichiers["meta.json"])
    assert (meta["nombre_scrutins"], meta["nombre_groupes"]) == (8877, 13)
    assert sum(1 for c in fichiers if c.startswith("scrutins/")) == 8877
    assert sum(1 for c in fichiers if c.startswith("groupes/")) == 13
    assert len(json.loads(fichiers["deputes.json"])["deputes"]) == 652
    assert len(fichiers) <= 8922
    index = json.loads(fichiers["scrutins-index.json"])["fragments"]
    assert len(index) <= 25 and sum(f["nombre_scrutins"] for f in index) == 8877
    total_votes = sum(len(json.loads(o)["votes"]) for c, o in fichiers.items() if c.startswith("scrutins/"))
    assert total_votes == 1_323_978
    d489 = json.loads(fichiers["scrutins/VTANR5L17V489.json"])
    assert len(d489["groupes"]) == 12 and all(g["groupe_id"] is None for g in d489["groupes"])
    assert d489["totaux"]["sans_vote_enregistre"] is None
    # lignes de groupe compactes (décision du 2026-11-18) : les fichiers `groupes/<id>.json` passent
    # d'environ 2,6 Mio à moins de 1 Mio ; `manifeste.json` (une empreinte par scrutin, environ 1,7 Mio)
    # n'est lu que par le garde-fou de déploiement, il est exclu de l'avertissement de taille
    assert len(fichiers["manifeste.json"]) < 3 * 1024 * 1024
    assert max(len(o) for c, o in fichiers.items() if c != "manifeste.json") < 1024 * 1024
    assert max(len(o) for c, o in fichiers.items() if c.startswith("groupes/")) < 1024 * 1024
    assert all(not c.endswith(".tmp") for c in fichiers)
    # ALG-14 sur toute l'archive : chaque scrutin publié est identique au fichier brut (script indépendant)
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "verifier_echantillon", RACINE.parent / "scripts" / "verifier_echantillon.py")
    verif = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verif)
    rapport = verif.verifier(DOSSIER_REEL, out, taille=10**9)
    assert rapport["ecarts"] == [] and rapport["statut"] == "ok"
    assert rapport["nb_verifies"] == 8877 and rapport["nb_champs_compares"] > 8877 * 20


def test_ALG_11_empreinte_entrees_composite():
    base, _ = _exporter()
    de = lambda f: _json(f, "manifeste.json")["empreinte_entrees"]  # noqa: E731
    assert de(base) == de(_exporter()[0])
    # l'archive, la version des algorithmes, celle des règles ou un référentiel la changent
    for sur in (
        {"archive_sha256": "c" * 64},
        {"version_etl": "autre"},
        {"version_regles_classification": "autre"},
        {"entrees": {"referentiels_sha256": "d" * 64}},
    ):
        assert de(_exporter(contexte=_contexte(**sur))[0]) != de(base), sur
    # mais pas un champ qui n'entre pas dans les entrées (date de synchronisation)
    assert de(_exporter(contexte=_contexte(donnees_du="2030-01-01T00:00:00+00:00"))[0]) == de(base)
