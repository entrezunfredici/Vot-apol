"""ALG-05 : Contrôles de réconciliation (totaux, groupes, nominatif).

Spécification : docs/algorithmes/ALG-05-reconciliation.md.
Le module ne fait que lire et comparer : aucune écriture, aucune horloge, aucun SQL.
Les deux niveaux (`lot` avant écriture, `base` après relecture SQL) produisent la même structure
`ScrutinAControler` ; les contrôles sont écrits une seule fois sur cette structure. L'adaptateur
du niveau base est dans etl/io/db.py : il relit la base par requêtes, sans réutiliser ALG-04.
Chaque bloc de code est précédé de « # ALG-05.k : <résumé> ».
"""

import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..models import POSITIONS_VOTE, LotScrutin, ScrutinNormalise

MAX_ECARTS_DETAILLES = 1000  # par contrôle (le compte exact est toujours donné)

SEVERITE = {
    "R01": "B", "R02": "B", "R03": "B", "R04": "B", "R05": "B", "R06": "B", "R07": "B",
    "R08": "B", "R09": "B", "R10": "B", "R11": "B", "R12": "I", "R13": "I", "R14": "B",
    "R15": "B", "R16": "B", "R17": "B",
}  # fmt: skip
CONTROLES_LOT = {f"R{n:02d}" for n in range(1, 15)} | {"R16"}
CONTROLES_BASE = {f"R{n:02d}" for n in (*range(1, 11), 15, 16, 17)}

# Écart de la source : position -> (clé du compteur de groupe, nom côté total)
_POSITIONS = ("pour", "contre", "abstention", "non_votant")


@dataclass(frozen=True)
class GroupeAControler:
    rang: int
    membres: int
    compteurs: dict[str, int]  # position -> compteur du groupe (source)
    lignes: dict[str, int]  # position -> nombre de lignes de vote nominatif
    abstentions_doublon_source: int | None = None  # niveau lot seulement (R14)


@dataclass(frozen=True)
class ScrutinAControler:
    """Chiffres d'un scrutin, quelle que soit leur provenance (lot ou base)."""

    id: str
    numero: int
    pour: int
    contre: int
    abstentions: int
    non_votants: int
    suffrages_exprimes: int
    nombre_votants: int
    lignes_scrutin: dict[str, int]  # position -> lignes de vote du scrutin
    groupes: list[GroupeAControler]
    # niveau lot seulement (champs non stockés, ALG-04) :
    sort_code: str | None = None
    type_vote_code: str | None = None
    nbr_suffrages_requis: int | None = None
    non_votants_volontaires: int | None = None
    # niveau base seulement :
    a_totaux: bool = True
    references_orphelines: int = 0  # lignes dont groupe_id ou depute_id est inconnu (R15)


@dataclass(frozen=True)
class Ecart:
    controle: str
    scrutin_id: str | None
    groupe_rang: int | None
    detail: str | None  # position (R08, R09) ou objet vérifié (R17)
    attendu: int
    obtenu: int
    connu: bool = False


@dataclass(frozen=True)
class EcartConnu:
    controle: str
    scrutin_id: str | None
    groupe_rang: int | None
    detail: str | None
    attendu: int
    obtenu: int
    motif: str
    valide_le: str
    valide_par: str

    def cle(self) -> tuple:
        return (self.controle, self.scrutin_id, self.groupe_rang, self.detail, self.attendu,
                self.obtenu)  # fmt: skip


@dataclass
class RapportReconciliation:
    niveau: str
    scrutins_controles: int = 0
    controles: dict[str, dict[str, int]] = field(default_factory=dict)  # id -> nb_verifies/nb_ecarts
    ecarts: list[Ecart] = field(default_factory=list)  # détail plafonné par contrôle
    avertissements: list[str] = field(default_factory=list)
    statut: str = "ok"  # ok | ecarts_connus | ecarts_informatifs | ecarts_nouveaux


class ErreurEcartsConnus(Exception):
    """Fichier des écarts connus illisible ou mal formé : arrêt (jamais « tout est permis »)."""


# --- ALG-05.1 : fichier des écarts connus --------------------------------------------------

_CHAMPS_CONNUS = ("controle", "scrutin_id", "groupe_rang", "detail", "attendu", "obtenu",
                  "motif", "valide_le", "valide_par")  # fmt: skip


def charger_ecarts_connus(chemin: Path | str) -> list[EcartConnu]:
    # ALG-05.1 : entrée mal formée (champ manquant, contrôle inconnu) -> erreur, arrêt
    try:
        brut = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ErreurEcartsConnus(f"fichier illisible : {exc}") from exc
    if not isinstance(brut, list):
        raise ErreurEcartsConnus("la racine doit être une liste")
    resultat = []
    for i, e in enumerate(brut):
        if not isinstance(e, dict) or set(e) != set(_CHAMPS_CONNUS):
            raise ErreurEcartsConnus(f"entrée {i} : champs attendus {_CHAMPS_CONNUS}")
        if e["controle"] not in SEVERITE:
            raise ErreurEcartsConnus(f"entrée {i} : contrôle inconnu {e['controle']!r}")
        for nom in ("attendu", "obtenu"):
            if isinstance(e[nom], bool) or not isinstance(e[nom], int):
                raise ErreurEcartsConnus(f"entrée {i} : {nom} doit être un entier")
        if not all(isinstance(e[nom], str) and e[nom] for nom in ("motif", "valide_le", "valide_par")):
            raise ErreurEcartsConnus(f"entrée {i} : motif, valide_le et valide_par obligatoires")
        resultat.append(EcartConnu(**e))
    return resultat


# --- adaptateur du niveau lot ----------------------------------------------------------------


def depuis_lot(scrutin: ScrutinNormalise, lot: LotScrutin) -> ScrutinAControler:
    """Niveau `lot` : compteurs de la source (ScrutinNormalise), lignes produites (LotScrutin)."""
    groupes = []
    for g in scrutin.groupes:
        groupes.append(
            GroupeAControler(
                rang=g.rang,
                membres=g.membres,
                compteurs={
                    "pour": g.pour,
                    "contre": g.contre,
                    "abstention": g.abstentions,
                    "non_votant": g.non_votants,
                },
                lignes=dict(lot.comptages.par_groupe[g.rang]),
                abstentions_doublon_source=g.abstentions_doublon_source,
            )
        )
    return ScrutinAControler(
        id=scrutin.id,
        numero=scrutin.numero,
        pour=scrutin.pour,
        contre=scrutin.contre,
        abstentions=scrutin.abstentions,
        non_votants=scrutin.non_votants,
        suffrages_exprimes=scrutin.suffrages_exprimes,
        nombre_votants=scrutin.nombre_votants,
        lignes_scrutin=dict(lot.comptages.scrutin),
        groupes=groupes,
        sort_code=scrutin.sort_code,
        type_vote_code=scrutin.type_vote_code,
        nbr_suffrages_requis=scrutin.nbr_suffrages_requis,
        non_votants_volontaires=scrutin.non_votants_volontaires,
    )


# --- contrôles ---------------------------------------------------------------------------------

_SUFFIXE_ID = re.compile(r"(\d+)$")


def _evaluer(s: ScrutinAControler, niveau: str):
    """Génère (contrôle, groupe_rang, détail, attendu, obtenu, est_ecart) pour un scrutin.

    Tous les contrôles applicables sont évalués, sans s'arrêter au premier écart (ALG-05.2) ;
    les calculs sont des entiers comparés exactement (ALG-05.3).
    """
    P, C, A, N = s.pour, s.contre, s.abstentions, s.non_votants
    totaux = {"pour": P, "contre": C, "abstention": A, "non_votant": N}

    # R01 : numero = entier du suffixe de id
    m = _SUFFIXE_ID.search(s.id)
    suffixe = int(m.group(1)) if m else -1
    yield "R01", None, None, s.numero, suffixe, s.numero != suffixe
    # R02 et R03
    yield "R02", None, None, s.suffrages_exprimes, P + C, s.suffrages_exprimes != P + C
    yield "R03", None, None, s.nombre_votants, P + C + A, s.nombre_votants != P + C + A
    # R04 à R07 : somme des compteurs des groupes = total officiel
    for controle, position in (("R04", "pour"), ("R05", "contre"), ("R06", "abstention"),
                               ("R07", "non_votant")):  # fmt: skip
        somme = sum(g.compteurs[position] for g in s.groupes)
        yield controle, None, None, totaux[position], somme, totaux[position] != somme
    # R08 : lignes de vote du scrutin = total officiel, position par position
    for position in _POSITIONS:
        obtenu = s.lignes_scrutin[position]
        yield "R08", None, position, totaux[position], obtenu, totaux[position] != obtenu
    # R09 et R10 : groupe par groupe (le rang est la clé, pas l'identifiant : groupes PO0)
    for g in s.groupes:
        for position in _POSITIONS:
            attendu, obtenu = g.compteurs[position], g.lignes[position]
            yield "R09", g.rang, position, attendu, obtenu, attendu != obtenu
        somme = sum(g.compteurs.values())
        yield "R10", g.rang, None, g.membres, somme, somme > g.membres
    if niveau == "lot":
        if s.sort_code is not None and s.nbr_suffrages_requis is not None:
            # R11 : adopté ⇔ P ≥ R
            attendu, obtenu = int(s.sort_code == "adopte"), int(P >= s.nbr_suffrages_requis)
            yield "R11", None, None, attendu, obtenu, attendu != obtenu
            # R12 : hors motion de censure, R = ⌊X / 2⌋ + 1 (informatif)
            if s.type_vote_code != "MOC":
                attendu = s.suffrages_exprimes // 2 + 1
                yield "R12", None, None, attendu, s.nbr_suffrages_requis, attendu != s.nbr_suffrages_requis
        if s.non_votants_volontaires is not None:
            # R13 : total des non-votants volontaires du scrutin = 0
            yield "R13", None, None, 0, s.non_votants_volontaires, s.non_votants_volontaires != 0
        for g in s.groupes:
            if g.abstentions_doublon_source is not None:
                # R14 : le doublon de la source égale les abstentions du groupe
                a = g.compteurs["abstention"]
                yield "R14", g.rang, None, a, g.abstentions_doublon_source, (
                    a != g.abstentions_doublon_source)
    else:
        # R15 : toute référence de groupe ou de député existe dans sa table
        yield "R15", None, None, 0, s.references_orphelines, s.references_orphelines != 0
        # R17 : au moins un groupe, une ligne de totaux
        yield "R17", None, "groupes", 1, min(len(s.groupes), 1), not s.groupes
        yield "R17", None, "totaux", 1, int(s.a_totaux), not s.a_totaux


def controler(
    scrutins: Iterable[ScrutinAControler],
    connus: Iterable[EcartConnu],
    niveau: str,
    nb_scrutins_attendu: int | None = None,
) -> RapportReconciliation:
    """Compare les chiffres de chaque scrutin ; ne corrige ni ne masque jamais un écart."""
    if niveau not in ("lot", "base"):
        raise ValueError(f"niveau inconnu : {niveau!r}")
    index = {e.cle(): e for e in connus}  # ALG-05.5 : correspondance exacte seulement
    rencontres: set[tuple] = set()
    ids_examines: set[str] = set()
    rapport = RapportReconciliation(niveau=niveau)
    detailles: dict[str, int] = defaultdict(int)

    def enregistrer(controle, scrutin_id, rang, detail, attendu, obtenu, est_ecart):
        stats = rapport.controles.setdefault(controle, {"nb_verifies": 0, "nb_ecarts": 0})
        stats["nb_verifies"] += 1
        if not est_ecart:
            return
        stats["nb_ecarts"] += 1  # le compte est exact même si le détail est plafonné
        cle = (controle, scrutin_id, rang, detail, attendu, obtenu)
        connu = cle in index
        if connu:
            rencontres.add(cle)
        if detailles[controle] < MAX_ECARTS_DETAILLES:
            detailles[controle] += 1
            rapport.ecarts.append(Ecart(controle, scrutin_id, rang, detail, attendu, obtenu, connu))

    # ALG-05.2 : tous les contrôles applicables, scrutin par scrutin
    for s in scrutins:
        rapport.scrutins_controles += 1
        ids_examines.add(s.id)
        for controle, rang, detail, attendu, obtenu, est_ecart in _evaluer(s, niveau):
            enregistrer(controle, s.id, rang, detail, attendu, obtenu, est_ecart)

    # R16 / R17 : une base (ou un lot) vide n'est jamais « ok »
    if rapport.scrutins_controles == 0:
        attendu = nb_scrutins_attendu if nb_scrutins_attendu else 1
        enregistrer("R16", None, None, None, attendu, 0, True)
        if niveau == "base":
            enregistrer("R17", None, None, "scrutins", 1, 0, True)
    elif nb_scrutins_attendu is not None and niveau == "base":
        # R16 : nombre de lignes de `scrutins` = nombre attendu après l'import (ALG-07)
        enregistrer("R16", None, None, None, nb_scrutins_attendu, rapport.scrutins_controles,
                    nb_scrutins_attendu != rapport.scrutins_controles)  # fmt: skip

    # ALG-05.6 : entrée du fichier des écarts connus jamais rencontrée
    # CHOIX: seules les entrées dont le scrutin a été examiné sont concernées
    # RAISON: un lot partiel (un seul scrutin) ne doit pas déclarer « disparus » les écarts
    # connus d'autres scrutins qu'il n'a pas regardés
    for cle, e in index.items():
        if (
            cle not in rencontres
            and _concerne_ce_niveau(e.controle, niveau)
            and e.scrutin_id in ids_examines
        ):
            rapport.avertissements.append(
                f"ecart_connu_disparu : {e.controle} {e.scrutin_id} {e.detail or ''}".strip()
            )

    # ALG-05.7 : statut global
    # CHOIX: un écart informatif (sévérité I) non connu ne bloque pas mais n'est pas « connu » :
    # statut dédié `ecarts_informatifs` (ALG-12 ne réagit qu'à `ecarts_nouveaux`)
    nouveaux = [e for e in rapport.ecarts if not e.connu]
    if any(SEVERITE[e.controle] == "B" for e in nouveaux):
        rapport.statut = "ecarts_nouveaux"
    elif nouveaux:
        rapport.statut = "ecarts_informatifs"
    elif rapport.ecarts:
        rapport.statut = "ecarts_connus"
    return rapport


def _concerne_ce_niveau(controle: str, niveau: str) -> bool:
    return controle in (CONTROLES_LOT if niveau == "lot" else CONTROLES_BASE)


# Rappel de l'ordre des positions utilisé par ALG-04 (garde contre une dérive silencieuse)
assert _POSITIONS == POSITIONS_VOTE
