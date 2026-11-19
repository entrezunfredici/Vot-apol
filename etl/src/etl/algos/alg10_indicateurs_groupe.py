"""ALG-10 : Indicateurs de groupe et comparaison de deux groupes.

Spécification : docs/algorithmes/ALG-10-indicateurs-groupe.md (statut « Validé », version 3).
Fonctions pures. Aucun score, aucun classement, aucune moyenne : des effectifs avec leur
dénominateur, et une répartition en tranches dont les libellés sont des bornes numériques seules.
Chaque bloc de code est précédé de « # ALG-10.k : <résumé> ».
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from itertools import pairwise

from ..models import (
    ComparaisonGroupes,
    IndicateursGroupe,
    LigneGroupeScrutin,
    LigneVoteSelection,
    PositionMajoritaire,
    ScrutinCompare,
)
from .alg03_position_majoritaire import ErreurDonnee, calculer_position

BORNES_PAR_DEFAUT: tuple[int, ...] = (20, 40, 60, 80)
CLES_POSITION = ("pour", "contre", "abstention", "egalite", "aucun_vote_exprime")
_EXPRIMEES = ("pour", "contre", "abstention")


class ErreurParametre(ValueError):
    """`bornes` invalides : aucun calcul (fiche, cas limites)."""


def valider_bornes(bornes: Sequence[int]) -> tuple[int, ...]:
    """Liste non vide d'entiers strictement croissants, compris entre 1 et 99."""
    ok = (
        len(bornes) > 0
        and all(isinstance(b, int) and not isinstance(b, bool) and 1 <= b <= 99 for b in bornes)
        and all(x < y for x, y in pairwise(bornes))
    )
    if not ok:
        raise ErreurParametre(f"bornes invalides : {list(bornes)!r}")
    return tuple(bornes)


def libelles_tranches(bornes: Sequence[int]) -> tuple[str, ...]:
    """Libellés = bornes numériques seules, sans qualificatif (neutralité)."""
    b = valider_bornes(bornes)
    libelles = [f"moins de {b[0]} %"]
    libelles += [f"de {b[i]} % à moins de {b[i + 1]} %" for i in range(len(b) - 1)]
    libelles.append(f"de {b[-1]} % à moins de 100 %")
    libelles.append("100 % (unanime)")
    return tuple(libelles)


def indice_tranche(m: int, e: int, bornes: Sequence[int]) -> int:
    """ALG-10.8 : indice 0 .. k+1 de la tranche (P1 .. P`k+2`), en entiers.

    `m = E` -> dernière tranche (unanime) ; sinon le nombre de bornes `b` telles que
    `100·m ≥ b·E` donne l'indice (chaque borne appartient à la tranche qui commence à elle).
    """
    if e <= 0 or m <= 0 or m > e:
        raise ErreurDonnee(f"part majoritaire impossible : m={m}, E={e}")
    if m == e:
        return len(bornes) + 1
    return sum(1 for b in bornes if 100 * m >= b * e)


def _verifier_ligne(ligne: LigneGroupeScrutin) -> None:
    # ALG-10.3 : indicateur absurde = on ne calcule pas
    compteurs = (ligne.pour, ligne.contre, ligne.abstentions, ligne.non_votants)
    if ligne.membres <= 0 or any(c < 0 for c in compteurs):
        raise ErreurDonnee(f"ligne invalide : {ligne.scrutin_id} / {ligne.groupe_id}")
    if sum(compteurs) > ligne.membres:
        raise ErreurDonnee(
            f"E + N > membres : {ligne.scrutin_id} / {ligne.groupe_id} "
            f"({sum(compteurs)} > {ligne.membres})"
        )


def _position(ligne: LigneGroupeScrutin) -> PositionMajoritaire:
    # ALG-10.4 : une seule définition de la position majoritaire dans tout le projet (ALG-03)
    return calculer_position(ligne.pour, ligne.contre, ligne.abstentions, ligne.membres)


def _cle_position(p: PositionMajoritaire) -> str:
    return p.raison_absence if p.position == "aucune" else p.position  # type: ignore[return-value]


def calculer_indicateurs(
    lignes: Iterable[LigneGroupeScrutin],
    votes: Iterable[LigneVoteSelection] = (),
    filtres: str = "",
    bornes: Sequence[int] = BORNES_PAR_DEFAUT,
    libelles_groupes: Mapping[str, str | None] | None = None,
) -> list[IndicateursGroupe]:
    """Indicateurs de chaque groupe identifié sur la sélection, triés sans critère évaluatif."""
    bornes = valider_bornes(bornes)
    libelles = libelles_tranches(bornes)
    libelles_groupes = libelles_groupes or {}

    # ALG-10.1 : les groupes non identifiés sont exclus et comptés (en scrutins distincts)
    par_groupe: dict[str, list[LigneGroupeScrutin]] = defaultdict(list)
    exclus: set[str] = set()
    for ligne in lignes:
        if ligne.groupe_id is None:
            exclus.add(ligne.scrutin_id)
        else:
            par_groupe[ligne.groupe_id].append(ligne)  # ALG-10.2 : un indicateur = un groupe

    # personnes distinctes : votes de la sélection, par groupe
    exprimes_par_groupe: dict[str, set[str]] = defaultdict(set)
    avec_vote_par_groupe: dict[str, set[str]] = defaultdict(set)
    for v in votes:
        if v.groupe_id is None:
            continue
        avec_vote_par_groupe[v.groupe_id].add(v.depute_id)
        if v.position in _EXPRIMEES:
            exprimes_par_groupe[v.groupe_id].add(v.depute_id)

    resultats: list[IndicateursGroupe] = []
    for gid, lignes_g in par_groupe.items():
        scrutins_vus: set[str] = set()
        positions = dict.fromkeys(CLES_POSITION, 0)
        repartition = [0] * len(libelles)
        somme = {"membres": 0, "p": 0, "c": 0, "a": 0, "n": 0, "s": 0}
        for ligne in lignes_g:
            if ligne.scrutin_id in scrutins_vus:
                raise ErreurDonnee(f"ligne en double : {ligne.scrutin_id} / {gid}")
            scrutins_vus.add(ligne.scrutin_id)
            _verifier_ligne(ligne)
            pos = _position(ligne)
            e = pos.exprimes
            somme["membres"] += ligne.membres
            somme["p"] += ligne.pour
            somme["c"] += ligne.contre
            somme["a"] += ligne.abstentions
            somme["n"] += ligne.non_votants
            somme["s"] += ligne.membres - (e + ligne.non_votants)  # ALG-10 : sans vote enregistré
            # ALG-10.7 : nombre de scrutins par position majoritaire
            positions[_cle_position(pos)] += 1
            # ALG-10.8 : tranche de la part majoritaire (seulement avec une position)
            if pos.position != "aucune":
                repartition[indice_tranche(pos.effectif_majoritaire, e, bornes)] += 1
        resultats.append(
            IndicateursGroupe(
                groupe_id=gid,
                filtres=filtres,
                nb_scrutins=len(lignes_g),
                nb_scrutins_exclus_groupe_non_identifie=len(exclus),
                membres_scrutins=somme["membres"],
                personnes_exprimees=len(exprimes_par_groupe.get(gid, ())),
                personnes_avec_vote=len(avec_vote_par_groupe.get(gid, ())),
                pour=somme["p"],
                contre=somme["c"],
                abstentions=somme["a"],
                non_votants=somme["n"],
                sans_vote_enregistre=somme["s"],
                exprimes=somme["p"] + somme["c"] + somme["a"],
                scrutins_par_position_majoritaire=positions,
                bornes=bornes,
                libelles_tranches=libelles,
                repartition_part_majoritaire=tuple(repartition),
            )
        )

    # ALG-10.9 : ordre alphabétique (libellé, puis identifiant), jamais selon un indicateur ;
    # un libellé non résolu vient après les libellés connus
    def cle(i: IndicateursGroupe) -> tuple:
        lib = libelles_groupes.get(i.groupe_id)
        return (lib is None, (lib or "").casefold(), i.groupe_id)

    return sorted(resultats, key=cle)


def _compare(sid: str, a: LigneGroupeScrutin, b: LigneGroupeScrutin) -> tuple[str, ScrutinCompare]:
    pa, pb = _position(a), _position(b)
    sc = ScrutinCompare(
        scrutin_id=sid,
        position_a=pa.position,
        raison_a=pa.raison_absence,
        exprimes_a=pa.exprimes,
        majoritaire_a=pa.effectif_majoritaire,
        membres_a=a.membres,
        position_b=pb.position,
        raison_b=pb.raison_absence,
        exprimes_b=pb.exprimes,
        majoritaire_b=pb.effectif_majoritaire,
        membres_b=b.membres,
    )
    if pa.position != "aucune" and pb.position != "aucune":
        # ALG-10.11 : les deux ont une position
        return ("meme_position" if pa.position == pb.position else "positions_differentes"), sc
    return "au_moins_une_sans_position", sc


def comparer_groupes(
    groupe_a: str,
    groupe_b: str,
    lignes: Iterable[LigneGroupeScrutin],
    filtres: str = "",
) -> ComparaisonGroupes:
    """Compare deux groupes sur les scrutins où les deux sont identifiés.

    Les mises au point n'entrent jamais ici : seules les valeurs officielles sont utilisées.
    """
    if groupe_a == groupe_b:
        raise ValueError("deux groupes distincts sont nécessaires")
    # ALG-10.10 : lignes de chaque groupe par scrutin
    lignes_a: dict[str, LigneGroupeScrutin] = {}
    lignes_b: dict[str, LigneGroupeScrutin] = {}
    for ligne in lignes:
        for gid, cible in ((groupe_a, lignes_a), (groupe_b, lignes_b)):
            if ligne.groupe_id == gid:
                if ligne.scrutin_id in cible:
                    raise ErreurDonnee(f"ligne en double : {ligne.scrutin_id} / {gid}")
                _verifier_ligne(ligne)
                cible[ligne.scrutin_id] = ligne
    communs = sorted(lignes_a.keys() & lignes_b.keys())
    classes: dict[str, list[ScrutinCompare]] = {
        "meme_position": [],
        "positions_differentes": [],
        "au_moins_une_sans_position": [],
    }
    for sid in communs:
        classe, sc = _compare(sid, lignes_a[sid], lignes_b[sid])
        classes[classe].append(sc)
    # un seul des deux groupes est présent : compté à part
    un_seul = len(lignes_a.keys() ^ lignes_b.keys())
    return ComparaisonGroupes(
        groupe_a=groupe_a,
        groupe_b=groupe_b,
        filtres=filtres,
        scrutins_communs=len(communs),
        meme_position=classes["meme_position"],
        positions_differentes=classes["positions_differentes"],
        au_moins_une_sans_position=classes["au_moins_une_sans_position"],
        scrutins_un_seul_present=un_seul,
    )
