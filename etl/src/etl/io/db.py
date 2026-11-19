"""Accès SQLite et migrations (utilisé pour ALG-05 niveau base, puis ALG-07)."""

import dataclasses
import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from ..algos.alg07_import_idempotent import MAX_CAUSES_RESUME, ErreurBase
from ..models import (
    POSITIONS_VOTE,
    AncienScrutin,
    Comptages,
    GroupeAControler,
    LigneGroupe,
    LigneMiseAuPoint,
    LigneScrutin,
    LigneTotaux,
    LigneVote,
    LotScrutin,
    RapportImport,
    ReferentielsExport,
    ResolutionNoms,
    ScrutinAControler,
)

MIGRATIONS = Path(__file__).parents[4] / "db" / "migrations"


def ouvrir(chemin: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(chemin))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _numero_migration(fichier: Path) -> int:
    m = re.match(r"(\d+)_", fichier.name)
    if m is None:
        raise ValueError(f"migration mal nommée (NNN_nom.sql attendu) : {fichier.name}")
    return int(m.group(1))


def version_schema_attendue(dossier: Path = MIGRATIONS) -> int:
    """Numéro de la dernière migration (ALG-07, paramètre VERSION_SCHEMA_ATTENDUE)."""
    return max((_numero_migration(f) for f in dossier.glob("*.sql")), default=0)


def appliquer_migrations(conn: sqlite3.Connection, dossier: Path = MIGRATIONS) -> None:
    # une migration n'est appliquée qu'une fois : `user_version` porte la dernière appliquée
    # (une base à jour ne rejoue rien ; 002 « ALTER TABLE » n'est pas rejouable)
    deja = int(conn.execute("PRAGMA user_version").fetchone()[0])
    for fichier in sorted(dossier.glob("*.sql"), key=_numero_migration):
        if _numero_migration(fichier) > deja:
            conn.executescript(fichier.read_text(encoding="utf-8"))
    # `user_version` porte le numéro de la dernière migration : ALG-07.1 le compare au code
    conn.execute(f"PRAGMA user_version = {version_schema_attendue(dossier)}")


def _vide() -> dict[str, int]:
    return dict.fromkeys(POSITIONS_VOTE, 0)


def lire_pour_controle(conn: sqlite3.Connection) -> Iterator[ScrutinAControler]:
    """Relit la base par requêtes (ALG-05.9), sans réutiliser le code d'ALG-04.

    Les compteurs viennent des tables `scrutin_totals` et `scrutin_group_votes`, les lignes de
    vote sont **comptées** par SQL dans `scrutin_individual_votes`.
    """
    # lignes de vote : par scrutin, groupe et position
    lignes_groupe: dict[tuple[str, int | None], dict[str, int]] = defaultdict(_vide)
    lignes_scrutin: dict[str, dict[str, int]] = defaultdict(_vide)
    for sid, rang, position, n in conn.execute(
        "SELECT scrutin_id, groupe_rang, position, COUNT(*) FROM scrutin_individual_votes "
        "GROUP BY scrutin_id, groupe_rang, position"
    ):
        lignes_groupe[(sid, rang)][position] += n
        lignes_scrutin[sid][position] += n

    # références inconnues (R15) : groupes et députés absents de leurs tables
    orphelines: dict[str, int] = defaultdict(int)
    for sid, n in conn.execute(
        "SELECT v.scrutin_id, COUNT(*) FROM scrutin_individual_votes v "
        "LEFT JOIN deputes d ON d.id = v.depute_id "
        "LEFT JOIN groupes g ON g.id = v.groupe_id "
        "WHERE d.id IS NULL OR (v.groupe_id IS NOT NULL AND g.id IS NULL) "
        "GROUP BY v.scrutin_id"
    ):
        orphelines[sid] += n
    for sid, n in conn.execute(
        "SELECT s.scrutin_id, COUNT(*) FROM scrutin_group_votes s "
        "LEFT JOIN groupes g ON g.id = s.groupe_id "
        "WHERE s.groupe_id IS NOT NULL AND g.id IS NULL GROUP BY s.scrutin_id"
    ):
        orphelines[sid] += n

    # groupes de chaque scrutin
    groupes: dict[str, list[GroupeAControler]] = defaultdict(list)
    for sid, rang, membres, p, c, a, nv in conn.execute(
        "SELECT scrutin_id, rang, membres, pour, contre, abstentions, non_votants "
        "FROM scrutin_group_votes ORDER BY scrutin_id, rang"
    ):
        groupes[sid].append(
            GroupeAControler(
                rang=rang,
                membres=membres,
                compteurs={"pour": p, "contre": c, "abstention": a, "non_votant": nv},
                lignes=dict(lignes_groupe.get((sid, rang), _vide())),
            )
        )

    # scrutins, avec ou sans ligne de totaux (R17)
    for sid, numero, p, c, a, nv, x, v in conn.execute(
        "SELECT s.id, s.numero, t.pour, t.contre, t.abstentions, t.non_votants, "
        "t.suffrages_exprimes, t.nombre_votants "
        "FROM scrutins s LEFT JOIN scrutin_totals t ON t.scrutin_id = s.id ORDER BY s.id"
    ):
        a_totaux = p is not None
        yield ScrutinAControler(
            id=sid,
            numero=numero,
            pour=p or 0,
            contre=c or 0,
            abstentions=a or 0,
            non_votants=nv or 0,
            suffrages_exprimes=x or 0,
            nombre_votants=v or 0,
            lignes_scrutin=dict(lignes_scrutin.get(sid, _vide())),
            groupes=groupes.get(sid, []),
            a_totaux=a_totaux,
            references_orphelines=orphelines.get(sid, 0),
        )


# --- ALG-07 : adaptateur SQLite du dépôt -------------------------------------------------------

_COLONNES_MISES_AU_POINT = (
    "scrutin_id", "depute_id", "origine", "groupe_rang", "groupe_id", "position_initiale",
    "position_declaree", "par_delegation",
)  # fmt: skip


def _motif(exc: sqlite3.Error) -> ErreurBase:
    texte = str(exc)
    if "locked" in texte or "busy" in texte:
        return ErreurBase("base_verrouillee", texte)
    if "full" in texte:
        return ErreurBase("disque_plein", texte)
    return ErreurBase("erreur_base", texte)


def _noms(objet: Any) -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(objet))


class DepotSqlite:
    """Implémente `Depot` (ALG-07) ; transactions explicites, requêtes toujours paramétrées."""

    def __init__(self, chemin: str | Path, lecture_seule: bool = False):
        try:
            if lecture_seule:
                uri = Path(chemin).resolve().as_uri() + "?mode=ro"
                self.conn = sqlite3.connect(uri, uri=True, timeout=0, isolation_level=None)
            else:
                self.conn = sqlite3.connect(str(chemin), timeout=0, isolation_level=None)
            self.conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as exc:
            raise _motif(exc) from exc

    def fermer(self) -> None:
        self.conn.close()

    def _exec(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        try:
            return self.conn.execute(sql, tuple(params))
        except sqlite3.Error as exc:
            raise _motif(exc) from exc

    def _plusieurs(self, sql: str, lignes: list[tuple]) -> None:
        try:
            self.conn.executemany(sql, lignes)
        except sqlite3.Error as exc:
            raise _motif(exc) from exc

    def _dict(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        cur = self._exec(sql, params)
        noms = [d[0] for d in cur.description]
        return [dict(zip(noms, ligne, strict=True)) for ligne in cur.fetchall()]

    def version_schema(self) -> int:
        return int(self._exec("PRAGMA user_version").fetchone()[0])

    def debut_import(self, importe_le: str, archive_sha256: str) -> int:
        # ALG-07.3 : validée immédiatement (autocommit hors transaction explicite)
        cur = self._exec(
            "INSERT INTO imports (started_at, archive_sha256, status) VALUES (?, ?, 'en_cours')",
            (importe_le, archive_sha256),
        )
        return int(cur.lastrowid or 0)

    def debut_lot(self) -> None:
        self._exec("BEGIN IMMEDIATE")

    def valider_lot(self) -> None:
        self._exec("COMMIT")

    def annuler_lot(self) -> None:
        self._exec("ROLLBACK")

    def lire_empreinte(self, scrutin_id: str) -> tuple[str, str] | None:
        ligne = self._exec(
            "SELECT source_hash, etl_version FROM scrutins WHERE id = ?", (scrutin_id,)
        ).fetchone()
        return None if ligne is None else (ligne[0], ligne[1])

    def lire_ancien(self, scrutin_id: str) -> AncienScrutin:
        p = (scrutin_id,)
        scrutin = self._dict("SELECT * FROM scrutins WHERE id = ?", p)
        totaux = self._dict("SELECT * FROM scrutin_totals WHERE scrutin_id = ?", p)
        groupes = self._dict("SELECT * FROM scrutin_group_votes WHERE scrutin_id = ?", p)
        nb_votes = self._exec(
            "SELECT COUNT(*) FROM scrutin_individual_votes WHERE scrutin_id = ?", p
        ).fetchone()[0]
        nb_mises = self._exec(
            "SELECT COUNT(*) FROM scrutin_mises_au_point WHERE scrutin_id = ?", p
        ).fetchone()[0]
        return AncienScrutin(
            scrutin=scrutin[0] if scrutin else {},
            totaux=totaux[0] if totaux else {},
            groupes={g["rang"]: g for g in groupes},
            nb_votes=nb_votes,
            nb_mises_au_point=nb_mises,
        )

    def inserer_references(self, groupes: list[str], deputes: list[str]) -> None:
        self._plusieurs("INSERT OR IGNORE INTO groupes (id) VALUES (?)", [(g,) for g in groupes])
        self._plusieurs("INSERT OR IGNORE INTO deputes (id) VALUES (?)", [(d,) for d in deputes])

    def supprimer_enfants(self, scrutin_id: str) -> None:
        # noms de tables : constantes du code, jamais des données
        for table in (
            "scrutin_mises_au_point",
            "scrutin_individual_votes",
            "scrutin_group_votes",
            "scrutin_totals",
        ):
            self._exec(f"DELETE FROM {table} WHERE scrutin_id = ?", (scrutin_id,))

    def _inserer(self, table: str, lignes: list[Any], colonnes: tuple[str, ...]) -> None:
        marques = ", ".join("?" * len(colonnes))
        sql = f"INSERT INTO {table} ({', '.join(colonnes)}) VALUES ({marques})"
        self._plusieurs(sql, [tuple(getattr(x, c) for c in colonnes) for x in lignes])

    def ecrire_scrutin(self, lot: LotScrutin) -> None:
        # ALG-07.10 : UPSERT de scrutins, puis insertion des lignes enfants
        cols = _noms(lot.scrutin)
        marques = ", ".join("?" * len(cols))
        maj = ", ".join(f"{c} = excluded.{c}" for c in cols if c != "id")
        self._exec(
            f"INSERT INTO scrutins ({', '.join(cols)}) VALUES ({marques}) "
            f"ON CONFLICT(id) DO UPDATE SET {maj}",
            tuple(getattr(lot.scrutin, c) for c in cols),
        )
        self._inserer("scrutin_totals", [lot.totaux], _noms(lot.totaux))
        if lot.groupes:
            self._inserer("scrutin_group_votes", lot.groupes, _noms(lot.groupes[0]))
        if lot.votes:
            self._inserer("scrutin_individual_votes", lot.votes, _noms(lot.votes[0]))
        self._inserer("scrutin_mises_au_point", lot.mises_au_point, _COLONNES_MISES_AU_POINT)

    def ids_en_base(self) -> set[str]:
        return {ligne[0] for ligne in self._exec("SELECT id FROM scrutins")}

    def terminer_import(self, import_id: int, termine_le: str, rapport: RapportImport) -> None:
        # ALG-07.15 : compteurs, statut et 20 premières causes de refus
        causes = [f"{x['id']} : {x['cause']}" for x in rapport.refuses]
        if rapport.motif_echec:
            causes.insert(0, rapport.motif_echec)
        self._exec(
            "UPDATE imports SET finished_at = ?, files_seen = ?, files_ok = ?, files_failed = ?, "
            "status = ?, error_summary = ? WHERE id = ?",
            (
                termine_le,
                rapport.fichiers_vus,
                rapport.fichiers_ok,
                rapport.fichiers_en_echec,
                rapport.statut,
                "\n".join(causes[:MAX_CAUSES_RESUME]) or None,
                import_id,
            ),
        )


# --- ALG-09 : lecture des identifiants référencés et écriture des noms ---------------------------


def lire_references_noms(
    conn: sqlite3.Connection,
) -> tuple[dict[str, int], dict[str, int]]:
    """Identifiants référencés (ALG-09.5) avec leur nombre d'occurrences.

    Groupes : nombre de scrutins où le groupe figure (`groupe_id` non nul). Députés : nombre de
    lignes dans les votes et les mises au point.
    """
    groupes = {
        gid: n
        for gid, n in conn.execute(
            "SELECT groupe_id, COUNT(*) FROM scrutin_group_votes "
            "WHERE groupe_id IS NOT NULL GROUP BY groupe_id"
        )
    }
    deputes: dict[str, int] = {}
    for table in ("scrutin_individual_votes", "scrutin_mises_au_point"):
        # noms de tables : constantes du code, jamais des données
        for did, n in conn.execute(f"SELECT depute_id, COUNT(*) FROM {table} GROUP BY depute_id"):
            deputes[did] = deputes.get(did, 0) + n
    return groupes, deputes


def lire_anciens_noms(
    conn: sqlite3.Connection,
) -> tuple[dict[str, tuple[str | None, str | None]], dict[str, tuple[str | None, str | None, str | None]]]:
    """Noms déjà en base (ALG-09.8) : groupes (libellé, sigle), députés (nom, prénom, civilité)."""
    groupes = {g: (lib, sig) for g, lib, sig in conn.execute("SELECT id, libelle, sigle FROM groupes")}
    deputes = {
        d: (nom, prenom, civ)
        for d, nom, prenom, civ in conn.execute("SELECT id, nom, prenom, civilite FROM deputes")
    }
    return groupes, deputes


def ecrire_noms(conn: sqlite3.Connection, resolution: ResolutionNoms) -> None:
    """ALG-09.7 : UPDATE paramétré des seuls identifiants résolus ; jamais de création de ligne."""
    conn.executemany(
        "UPDATE groupes SET libelle = ?, sigle = ? WHERE id = ?",
        [(g.libelle, g.sigle, g.id) for g in resolution.groupes],
    )
    conn.executemany(
        "UPDATE deputes SET nom = ?, prenom = ?, civilite = ? WHERE id = ?",
        [(d.nom, d.prenom, d.civilite, d.id) for d in resolution.deputes],
    )


# --- ALG-11 : lecture de la base pour l'export ----------------------------------------------------


def lire_referentiels_export(conn: sqlite3.Connection) -> ReferentielsExport:
    """Noms résolus par ALG-09 (None tant qu'un identifiant n'est pas résolu)."""
    groupes = {g: (lib, sig) for g, lib, sig in conn.execute("SELECT id, libelle, sigle FROM groupes")}
    deputes = {
        d: (nom, prenom, civ)
        for d, nom, prenom, civ in conn.execute("SELECT id, nom, prenom, civilite FROM deputes")
    }
    return ReferentielsExport(groupes, deputes)


def lire_contexte_base(conn: sqlite3.Connection) -> dict[str, Any]:
    """Provenance lue dans la base (aucune horloge) : dernier import terminé, nombre de scrutins."""
    ligne = conn.execute(
        "SELECT archive_sha256, finished_at FROM imports "
        "WHERE status LIKE 'termine%' AND finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    nombre = conn.execute("SELECT COUNT(*) FROM scrutins").fetchone()[0]
    return {
        "archive_sha256": ligne[0] if ligne else "",
        "donnees_du": ligne[1] if ligne else "",
        "nombre_scrutins": nombre,
    }


def _noms_classe(classe: type) -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(classe))


def _construire(classe: type, ligne: tuple | None, colonnes: tuple[str, ...]) -> Any:
    if ligne is None:
        raise ErreurBase("donnees_incompletes", f"ligne absente pour {classe.__name__}")
    return classe(**dict(zip(colonnes, ligne, strict=True)))


def lire_scrutins_export(conn: sqlite3.Connection) -> Iterator[LotScrutin]:
    """Un `LotScrutin` par scrutin, par numéro croissant, relu dans la base (ALG-11.3).

    Le rattachement des mises au point (ALG-06 A) est déjà stocké ; le statut (`rattachee` ou
    `introuvable`) et l'effet (`sans_effet` ou `modifie_position`) en sont déduits comme à l'import.
    Les lots sont produits un à un : la mémoire ne grossit pas avec le nombre de scrutins.
    """
    cols_s, cols_t = _noms_classe(LigneScrutin), _noms_classe(LigneTotaux)
    cols_g, cols_v = _noms_classe(LigneGroupe), _noms_classe(LigneVote)
    # noms de colonnes : constantes du code (champs de dataclasses), jamais des données
    req_s = f"SELECT {', '.join(cols_s)} FROM scrutins WHERE id = ?"
    req_t = f"SELECT {', '.join(cols_t)} FROM scrutin_totals WHERE scrutin_id = ?"
    req_g = f"SELECT {', '.join(cols_g)} FROM scrutin_group_votes WHERE scrutin_id = ? ORDER BY rang"
    req_v = f"SELECT {', '.join(cols_v)} FROM scrutin_individual_votes WHERE scrutin_id = ?"
    req_m = (
        "SELECT depute_id, origine, position_declaree, par_delegation, groupe_rang, groupe_id, "
        "position_initiale FROM scrutin_mises_au_point WHERE scrutin_id = ? ORDER BY depute_id"
    )
    ids = [r[0] for r in conn.execute("SELECT id FROM scrutins ORDER BY numero")]
    for sid in ids:
        p = (sid,)
        scrutin = _construire(LigneScrutin, conn.execute(req_s, p).fetchone(), cols_s)
        totaux = _construire(LigneTotaux, conn.execute(req_t, p).fetchone(), cols_t)
        groupes = [_construire(LigneGroupe, r, cols_g) for r in conn.execute(req_g, p)]
        votes = [_construire(LigneVote, r, cols_v) for r in conn.execute(req_v, p)]
        mises = []
        for r in conn.execute(req_m, p):
            rattachee = r[4] is not None
            effet = None if not rattachee else ("sans_effet" if r[2] == r[6] else "modifie_position")
            mises.append(
                LigneMiseAuPoint(
                    sid, r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                    "rattachee" if rattachee else "introuvable", effet,
                )
            )
        par_scrutin = dict.fromkeys(POSITIONS_VOTE, 0)
        par_groupe: dict[int, dict[str, int]] = {g.rang: dict.fromkeys(POSITIONS_VOTE, 0) for g in groupes}
        for v in votes:
            par_scrutin[v.position] += 1
            par_groupe.setdefault(v.groupe_rang, dict.fromkeys(POSITIONS_VOTE, 0))[v.position] += 1
        yield LotScrutin(
            scrutin=scrutin,
            totaux=totaux,
            groupes=groupes,
            votes=votes,
            mises_au_point=mises,
            groupes_vus=sorted({g.groupe_id for g in groupes if g.groupe_id}),
            deputes_vus=sorted({v.depute_id for v in votes} | {m.depute_id for m in mises}),
            comptages=Comptages(par_groupe=par_groupe, scrutin=par_scrutin),
        )
