"""Tests ALG-08 : un test par règle (titre réel) et par cas limite de la fiche."""

import json
from collections import Counter
from pathlib import Path

import pytest

from etl.algos.alg08_classification import (
    VERSION_REGLES,
    ErreurCorrections,
    charger_corrections,
    classifier,
    normaliser_titre,
)
from etl.models import CATEGORIES, CorrectionTitre

RACINE = Path(__file__).parents[2]
DOSSIER_REEL = RACINE.parent / "Scrutins.json"
CORRECTIONS = RACINE / "corrections_classification.json"

# Débuts de titres réels (les expressions sont ancrées au début du titre)
T_AMENDEMENT = (
    "l'amendement n° 1762 de M. Le Coq et l'amendement identique suivant à l'article 2 du "
    "projet de loi de finances"
)
T_SOUS_AMENDEMENT = (
    "le sous-amendement n° 48 de M. Jean-Philippe Tanguy à l'amendement n° 22 de M. de Courson "
    "à l'article 2 de la"
)
T_ARTICLE = (
    "l'article 2 de la proposition de loi visant à lutter contre les fermetures abusives de "
    "comptes bancaires (première lecture)."
)
T_ENSEMBLE = (
    "l'ensemble de la proposition de résolution tendant à la création d'une commission "
    "d'enquête sur les effets psy"
)
T_REJET = "la motion de rejet préalable, déposée par Mme Mathilde Panot, de la proposition de loi"
T_PROCEDURE = (
    "la demande de seconde délibération de M. Jean-Philippe Tanguy sur l'amendement n° 2 de "
    "M. Fabrice Brun et les"
)
T_DECLARATION = (
    "la déclaration de politique générale du Gouvernement de M. François Bayrou (application "
    "de l'article 49, aliné"
)
T_PARTIE = "la deuxième partie du projet de loi de financement de la sécurité sociale pour 2026."
T_MOTION = (
    "la motion de censure déposée en application de l'article 49, alinéa 2, de la Constitution "
    "par M. Boris Vallaud"
)


def _c(titre, type_vote="SPO", scrutin_id="VTANR5L17V10", corrections=()):
    return classifier(scrutin_id, type_vote, titre, corrections)


@pytest.mark.parametrize(
    "titre, categorie, regle",
    [
        (T_REJET, "motion_rejet", "R1"),
        (T_DECLARATION, "declaration_gouvernement", "R2"),
        (T_PROCEDURE, "procedure", "R3"),
        (T_SOUS_AMENDEMENT, "sous_amendement", "R4"),
        (T_AMENDEMENT, "amendement", "R5"),
        (T_ARTICLE, "article", "R6"),
        (T_PARTIE, "partie_loi_finances", "R7"),
        (T_ENSEMBLE, "texte_ensemble", "R8"),
        ("l'ensemble du projet de loi de finances pour 2026 (nouvelle lecture).",
         "texte_ensemble", "R8"),
        ("la proposition de loi apportant une réponse à l'urgence (première lecture).",
         "texte_ensemble", "R8"),
    ],
)  # fmt: skip
def test_ALG_08_chaque_regle_sur_un_titre_reel(titre, categorie, regle):
    r = _c(titre)
    assert (r.categorie, r.regle_id, r.methode) == (categorie, regle, "regle_titre")
    assert (r.confiance, r.a_verifier, r.version_regles) == ("moyenne", True, VERSION_REGLES)
    assert r.avertissements == ()


def test_ALG_08_motion_de_censure_metadonnee_officielle():
    r = _c(T_MOTION, type_vote="MOC")
    assert (r.categorie, r.methode, r.confiance, r.a_verifier) == (
        "motion_censure", "metadonnee_officielle", "haute", False)  # fmt: skip
    assert r.avertissements == ()


def test_ALG_08_moc_avec_titre_incoherent_est_signale():
    r = _c("l'amendement n° 1 de M. X", type_vote="MOC")
    assert r.categorie == "motion_censure" and r.a_verifier is True
    assert r.avertissements == ("incoherence_metadonnee",)


def test_ALG_08_apostrophes_courbes():
    r = _c("l’amendement n° 1972 de M. Davi à l’article 15 du projet de loi")
    assert (r.categorie, r.regle_id) == ("amendement", "R5")
    assert _c("l’ensemble de la proposition de loi contre les fraudes").categorie == (
        "texte_ensemble"
    )


def test_ALG_08_amendement_a_un_article_n_est_pas_un_article():
    t = "l'amendement n° 19 de M. X à l'article 2 de la proposition de loi relative à Y"
    assert _c(t).categorie == "amendement"


def test_ALG_08_sous_amendement_n_est_pas_un_amendement():
    assert _c(T_SOUS_AMENDEMENT).categorie == "sous_amendement"
    assert _c("le sous-amendement n° 2 à l'amendement n° 1").regle_id == "R4"


def test_ALG_08_proposition_du_gouvernement_n_est_pas_un_texte():
    t = "la proposition du Gouvernement de prolonger la séance jusqu'à minuit"
    r = _c(t)
    assert (r.categorie, r.regle_id) == ("procedure", "R3")


def test_ALG_08_motion_de_rejet_prealable_non_ancree():
    t = "sur la motion de rejet préalable, déposée par M. Y, de la proposition de loi"
    assert _c(t).categorie == "motion_rejet"


def test_ALG_08_regles_en_conflit_indetermine():
    # cas construit : R1 (non ancrée) et R8 correspondent ; aucun cas réel n'existe
    t = "l'ensemble de la proposition de loi et la motion de rejet préalable"
    r = _c(t)
    assert (r.categorie, r.methode, r.confiance, r.a_verifier) == (
        "indetermine", "aucune", "aucune", True)  # fmt: skip
    assert r.avertissements == ("regles_en_conflit",)


@pytest.mark.parametrize(
    "titre",
    [
        "l'aticle 6 du projet de loi sur la justice criminelle (première lecture).",
        "le sous-amendmeent n° 776 de Mme Mansouri à l'amendement n° 609",
        "l'amenedement n° 187 de M. Renault à l'article 35",
        "",
    ],
)
def test_ALG_08_faute_de_frappe_sans_correction_indetermine(titre):
    r = _c(titre)
    assert (r.categorie, r.methode, r.confiance, r.a_verifier) == (
        "indetermine", "aucune", "aucune", True)  # fmt: skip
    assert r.regle_id is None


# --- corrections manuelles --------------------------------------------------------------------


def _correction(titre="l'aticle 6 du projet de loi", categorie="article"):
    return CorrectionTitre("VTANR5L17V7950", titre, categorie, "faute de frappe", "2026-11-18", "x")


def test_ALG_08_correction_validee_s_applique_au_titre_exact():
    titre = "l'aticle 6 du projet de loi"
    r = _c(titre, scrutin_id="VTANR5L17V7950", corrections=[_correction(titre)])
    assert (r.categorie, r.methode, r.confiance, r.a_verifier, r.regle_id) == (
        "article", "correction_manuelle", "haute", False, None)  # fmt: skip


def test_ALG_08_correction_obsolete_ignoree_avec_avertissement():
    r = _c("l'article 6 du projet de loi (titre corrigé par la source)",
           scrutin_id="VTANR5L17V7950", corrections=[_correction()])  # fmt: skip
    assert r.methode == "regle_titre" and r.categorie == "article"
    assert r.avertissements == ("correction_obsolete",)


def test_ALG_08_correction_d_un_autre_scrutin_ignoree():
    r = _c("l'aticle 6 du projet de loi", scrutin_id="VTANR5L17V1", corrections=[_correction()])
    assert r.categorie == "indetermine" and r.avertissements == ()


def test_ALG_08_fichier_de_corrections_reel_valide():
    corrections = charger_corrections(CORRECTIONS)
    assert {c.id: c.categorie for c in corrections} == {
        "VTANR5L17V1633": "sous_amendement",
        "VTANR5L17V6214": "sous_amendement",
        "VTANR5L17V4988": "amendement",
        "VTANR5L17V7432": "motion_rejet",
        "VTANR5L17V7950": "article",
        "VTANR5L17V918": "texte_ensemble",
    }
    assert all(c.valide_par and c.valide_le for c in corrections)


@pytest.mark.parametrize(
    "contenu",
    [
        "pas du json",
        "{}",
        '[{"id": "x"}]',
        '[{"id": "x", "titre": "t", "categorie": "inconnue", "motif": "m", '
        '"valide_le": "d", "valide_par": "p"}]',
        '[{"id": "x", "titre": "t", "categorie": "indetermine", "motif": "m", '
        '"valide_le": "d", "valide_par": "p"}]',
        '[{"id": "x", "titre": "", "categorie": "article", "motif": "m", '
        '"valide_le": "d", "valide_par": "p"}]',
        '[{"id": "x", "titre": "t", "categorie": "article", "motif": "m", '
        '"valide_le": "d", "valide_par": "p"},'
        ' {"id": "x", "titre": "u", "categorie": "article", "motif": "m", '
        '"valide_le": "d", "valide_par": "p"}]',
    ],
)
def test_ALG_08_fichier_de_corrections_mal_forme_arret(tmp_path, contenu):
    f = tmp_path / "c.json"
    f.write_text(contenu, encoding="utf-8")
    with pytest.raises(ErreurCorrections):
        charger_corrections(f)
    with pytest.raises(ErreurCorrections):
        charger_corrections(tmp_path / "absent.json")


# --- propriétés -------------------------------------------------------------------------------


def test_ALG_08_normalisation():
    assert normaliser_titre("  L’Amendement   n° 1  ") == "l'amendement n° 1"
    # le titre affiché n'est jamais modifié : la fonction ne renvoie qu'une copie normalisée
    t = "L’Amendement"
    normaliser_titre(t)
    assert t == "L’Amendement"


def test_ALG_08_deterministe_et_categorie_dans_le_vocabulaire():
    for t in (T_AMENDEMENT, T_ARTICLE, "titre inconnu"):
        assert _c(t) == _c(t) and _c(t).categorie in CATEGORIES


def test_ALG_08_invariants_a_verifier():
    for t, tv in ((T_AMENDEMENT, "SPO"), (T_MOTION, "MOC"), ("???", "SPO")):
        r = _c(t, tv)
        if not r.a_verifier:
            assert r.methode in ("metadonnee_officielle", "correction_manuelle")
        if r.categorie == "indetermine":
            assert r.a_verifier and r.methode == "aucune"


# --- archive réelle complète --------------------------------------------------------------------


@pytest.mark.skipif(not DOSSIER_REEL.exists(), reason="archive réelle absente")
def test_ALG_08_archive_complete_sans_puis_avec_corrections():
    compte_sans: Counter = Counter()
    compte_avec: Counter = Counter()
    corrections = charger_corrections(CORRECTIONS)
    conflits = 0
    for fichier in (DOSSIER_REEL / "json").glob("*.json"):
        s = json.loads(fichier.read_text(encoding="utf-8"))["scrutin"]
        sans = classifier(s["uid"], s["typeVote"]["codeTypeVote"], s["titre"])
        avec = classifier(s["uid"], s["typeVote"]["codeTypeVote"], s["titre"], corrections)
        compte_sans[sans.categorie] += 1
        compte_avec[avec.categorie] += 1
        conflits += "regles_en_conflit" in sans.avertissements
        assert avec.avertissements == ()  # aucune correction obsolète
    assert conflits == 0
    assert sum(compte_sans.values()) == 8877
    assert dict(compte_sans) == {
        "amendement": 6931,
        "sous_amendement": 654,
        "article": 936,
        "texte_ensemble": 240,
        "motion_rejet": 58,
        "motion_censure": 23,
        "procedure": 18,
        "declaration_gouvernement": 4,
        "partie_loi_finances": 7,
        "indetermine": 6,
    }
    assert compte_avec["indetermine"] == 0 and sum(compte_avec.values()) == 8877
    assert compte_avec["sous_amendement"] == 656 and compte_avec["amendement"] == 6932
    assert compte_avec["motion_rejet"] == 59 and compte_avec["article"] == 937
    assert compte_avec["texte_ensemble"] == 241
