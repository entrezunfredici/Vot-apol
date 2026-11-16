"""Tests ALG-07 : cas limites et exemples de la fiche, sur une vraie base SQLite temporaire."""

import dataclasses
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from etl.algos.alg02_normalisation import normaliser_scrutin
from etl.algos.alg04_extraction_scrutin import extraire_scrutin
from etl.algos.alg06_mises_au_point import rattacher
from etl.algos.alg07_import_idempotent import (
    ErreurBase,
    calculer_version_etl,
    classer,
    importer,
)
from etl.io.db import DepotSqlite, appliquer_migrations, version_schema_attendue
from etl.io.fs import ecrire_journal_import
from etl.models import LotScrutin, RapportLecture, ScrutinRefuse

FIXTURES = Path(__file__).parents[1] / "fixtures"
NUMEROS = (1, 2, 3, 489, 1017, 1302)
VERSION = version_schema_attendue()


def _horloge():
    t = datetime(2026, 11, 14, 12, 0, 0)
    compteur = iter(range(10_000))
    return lambda: t + timedelta(seconds=next(compteur))


def _lot(n: int, hash_: str | None = None, version: str = "v1") -> LotScrutin:
    doc = json.loads((FIXTURES / f"VTANR5L17V{n}.json").read_text(encoding="utf-8"))
    scrutin = normaliser_scrutin(doc).scrutin
    lot = extraire_scrutin(
        scrutin,
        f"json/{scrutin.id}.json",
        hash_ or f"{n:064x}",
        None,
        "2026-11-14T12:00:00",
        version,
    )
    return rattacher(lot)


def _lecture(n: int, statut: str = "complet") -> RapportLecture:
    return RapportLecture(
        type_source="zip", empreinte_archive="e" * 64, type_empreinte="fichier",
        entrees_vues=n, acceptees=n, statut=statut,
    )  # fmt: skip


@pytest.fixture
def base(tmp_path):
    chemin = tmp_path / "t.db"
    conn = sqlite3.connect(chemin)
    appliquer_migrations(conn)
    conn.close()
    return chemin


def _importer(base, flux, lecture=None, **kw):
    depot = DepotSqlite(base)
    try:
        return importer(
            depot,
            flux,
            lecture or _lecture(len(flux)),
            "2026-11-14T12:00:00",
            _horloge(),
            VERSION,
            **kw,
        )
    finally:
        depot.fermer()


def _etat(base) -> dict:
    """Contenu complet des tables de scrutins (somme de contrôle de la fiche)."""
    conn = sqlite3.connect(base)
    try:
        return {
            t: conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall()
            for t in (
                "scrutins", "scrutin_totals", "scrutin_group_votes",
                "scrutin_individual_votes", "scrutin_mises_au_point", "groupes", "deputes",
            )
        }  # fmt: skip
    finally:
        conn.close()


def _n(base, table) -> int:
    conn = sqlite3.connect(base)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_ALG_07_classement():
    assert classer(None, "h", "v") == "nouveau"
    assert classer(("h", "v"), "h", "v") == "inchange"
    assert classer(("h", "v"), "autre", "v") == "modifie"
    assert classer(("h", "v"), "autre", "w") == "modifie"
    assert classer(("h", "v"), "h", "w") == "retraite"


def test_ALG_07_version_etl_calculee_normalise_les_fins_de_ligne():
    assert calculer_version_etl(["a\nb"]) == calculer_version_etl(["a\r\nb"])
    assert calculer_version_etl(["a"]) != calculer_version_etl(["b"])


def test_ALG_07_base_vide_puis_rejeu_identique(base):
    lots = [_lot(n) for n in NUMEROS]
    r1 = _importer(base, lots)
    assert (r1.nouveaux, r1.inchanges, len(r1.modifies), r1.statut) == (6, 0, 0, "termine")
    avant = _etat(base)
    assert _n(base, "scrutins") == 6 and _n(base, "scrutin_individual_votes") > 0

    r2 = _importer(base, lots)
    assert (r2.nouveaux, r2.inchanges, len(r2.modifies), r2.statut) == (0, 6, 0, "termine")
    assert _etat(base) == avant  # aucune ligne modifiée, imported_at compris
    assert _n(base, "imports") == 2


def test_ALG_07_invariant_comptes(base):
    lots = [_lot(n) for n in NUMEROS]
    r = _importer(base, [*lots[:4], ScrutinRefuse("VTANR5L17V999", "x")], _lecture(5))
    total = r.nouveaux + r.inchanges + len(r.modifies) + len(r.retraites) + len(r.refuses)
    assert total == 5 and r.fichiers_ok == 4 and r.fichiers_en_echec == 1


def test_ALG_07_fichier_modifie_reecrit_entierement(base):
    lot = _lot(1)
    _importer(base, [lot])
    nb_votes = _n(base, "scrutin_individual_votes")
    # même scrutin, hash différent, un votant en moins et un compteur différent
    modifie = dataclasses.replace(
        lot,
        scrutin=dataclasses.replace(lot.scrutin, source_hash="f" * 64, titre="Titre modifié"),
        votes=lot.votes[:-1],
    )
    r = _importer(base, [modifie])
    assert len(r.modifies) == 1 and r.statut == "termine"
    assert "titre" in r.modifies[0]["champs_modifies"]
    assert "votes" in r.modifies[0]["champs_modifies"]
    assert r.modifies[0]["nouveau_hash"] == "f" * 64
    assert _n(base, "scrutin_individual_votes") == nb_votes - 1
    assert _n(base, "scrutins") == 1


def test_ALG_07_depute_disparu_ne_survit_pas(base):
    lot = _lot(1)
    _importer(base, [lot])
    retire = lot.votes[0].depute_id
    modifie = dataclasses.replace(
        lot,
        scrutin=dataclasses.replace(lot.scrutin, source_hash="f" * 64),
        votes=lot.votes[1:],
        mises_au_point=[m for m in lot.mises_au_point if m.depute_id != retire],
    )
    _importer(base, [modifie])
    conn = sqlite3.connect(base)
    n = conn.execute(
        "SELECT COUNT(*) FROM scrutin_individual_votes WHERE depute_id = ?", (retire,)
    ).fetchone()[0]
    conn.close()
    assert n == 0


def test_ALG_07_version_etl_changee_donne_retraite(base):
    _importer(base, [_lot(1, version="v1")])
    r = _importer(base, [_lot(1, version="v2")])
    assert (r.nouveaux, r.inchanges, len(r.modifies), len(r.retraites)) == (0, 0, 0, 1)


def test_ALG_07_refuse_conserve_l_ancien_scrutin(base):
    lot = _lot(1)
    _importer(base, [lot])
    avant = _etat(base)
    r = _importer(base, [ScrutinRefuse(lot.scrutin.id, "erreur_normalisation")])
    assert r.refuses == [{"id": lot.scrutin.id, "cause": "erreur_normalisation"}]
    assert r.statut == "termine_avec_erreurs" and r.absents_de_l_archive == []
    assert _etat(base) == avant


def test_ALG_07_absent_de_l_archive_signale_jamais_supprime(base):
    _importer(base, [_lot(1), _lot(2)])
    r = _importer(base, [_lot(1)])
    assert r.absents_de_l_archive == ["VTANR5L17V2"]
    assert r.statut == "termine_avec_erreurs"
    assert _n(base, "scrutins") == 2


def test_ALG_07_lecture_partielle_donne_termine_avec_erreurs(base):
    r = _importer(base, [_lot(1)], _lecture(1, "partiel"))
    assert r.statut == "termine_avec_erreurs" and r.nouveaux == 1


def test_ALG_07_lecture_en_echec_rien_ecrit(base):
    lecture = RapportLecture(statut="echec", motif_echec="source_introuvable")
    r = _importer(base, [_lot(1)], lecture)
    assert r.statut == "echoue" and r.motif_echec == "source_introuvable"
    assert _n(base, "scrutins") == 0 and _n(base, "imports") == 0


def test_ALG_07_schema_ancien_echoue_sans_ecriture(tmp_path):
    chemin = tmp_path / "vide.db"
    sqlite3.connect(chemin).close()  # user_version = 0
    r = _importer(chemin, [_lot(1)])
    assert r.statut == "echoue" and "schema_incompatible" in (r.motif_echec or "")
    conn = sqlite3.connect(chemin)
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    conn.close()


def test_ALG_07_simulation_n_ecrit_rien(base):
    _importer(base, [_lot(1)])
    avant, nb_imports = _etat(base), _n(base, "imports")
    nouveau = dataclasses.replace(
        _lot(1), scrutin=dataclasses.replace(_lot(1).scrutin, source_hash="f" * 64)
    )
    depot = DepotSqlite(base, lecture_seule=True)
    r = importer(depot, [nouveau, _lot(2)], _lecture(2), "t", _horloge(), VERSION, simulation=True)
    depot.fermer()
    assert r.statut == "simulation" and (r.nouveaux, len(r.modifies)) == (1, 1)
    assert _etat(base) == avant and _n(base, "imports") == nb_imports


def test_ALG_07_deux_imports_simultanes_le_second_echoue(base):
    bloqueur = DepotSqlite(base)
    bloqueur.debut_lot()  # verrou d'écriture tenu
    try:
        r = _importer(base, [_lot(1)])
    finally:
        bloqueur.annuler_lot()
        bloqueur.fermer()
    assert r.statut == "echoue" and r.motif_echec == "base_verrouillee"


def test_ALG_07_erreur_de_base_annule_le_lot_en_cours(base):
    class DepotQuiPlante(DepotSqlite):
        appels = 0

        def ecrire_scrutin(self, lot):
            DepotQuiPlante.appels += 1
            if DepotQuiPlante.appels == 3:
                raise ErreurBase("disque_plein")
            super().ecrire_scrutin(lot)

    depot = DepotQuiPlante(base)
    r = importer(
        depot, [_lot(n) for n in NUMEROS[:4]], _lecture(4), "t", _horloge(), VERSION, taille_lot=2
    )
    depot.fermer()
    assert r.statut == "echoue" and r.motif_echec == "disque_plein"
    assert _n(base, "scrutins") == 2  # lot 1 validé, lot 2 annulé
    assert r.nouveaux == 2  # un lot annulé n'est pas compté
    # reprise : rejouer suffit
    r2 = _importer(base, [_lot(n) for n in NUMEROS[:4]])
    assert (r2.inchanges, r2.nouveaux) == (2, 2)


def test_ALG_07_interruption_valide_le_lot_en_cours(base):
    appels = iter([False, True])
    r = _importer(base, [_lot(n) for n in NUMEROS[:4]], interruption=lambda: next(appels))
    assert r.statut == "interrompu" and r.nouveaux == 2
    assert _n(base, "scrutins") == 2


def test_ALG_07_journal_et_table_imports(base, tmp_path):
    r = _importer(base, [_lot(1), ScrutinRefuse("VTANR5L17V9", "cause")], _lecture(2))
    chemin = ecrire_journal_import(r, tmp_path / "journaux")
    assert chemin.name == f"import-{r.import_id}.json"
    journal = json.loads(chemin.read_text(encoding="utf-8"))
    assert journal["statut"] == "termine_avec_erreurs" and journal["refuses"][0]["id"].endswith(
        "V9"
    )
    conn = sqlite3.connect(base)
    ligne = conn.execute(
        "SELECT status, files_seen, files_ok, files_failed, finished_at, error_summary FROM imports"
    ).fetchone()
    conn.close()
    assert ligne[:4] == ("termine_avec_erreurs", 2, 1, 1) and ligne[4] and "V9" in ligne[5]
