"""Accès SQLite et migrations (utilisé pour ALG-05 niveau base, puis ALG-07)."""

import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from ..algos.alg05_reconciliation import GroupeAControler, ScrutinAControler
from ..models import POSITIONS_VOTE

MIGRATIONS = Path(__file__).parents[4] / "db" / "migrations"


def ouvrir(chemin: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(chemin))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def appliquer_migrations(conn: sqlite3.Connection, dossier: Path = MIGRATIONS) -> None:
    for fichier in sorted(dossier.glob("*.sql")):
        conn.executescript(fichier.read_text(encoding="utf-8"))


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
