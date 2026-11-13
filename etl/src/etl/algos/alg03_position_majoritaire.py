"""ALG-03 : Position majoritaire d'un groupe.

Spécification : docs/algorithmes/ALG-03-position-majoritaire.md.
Fonctions pures : pas de disque, pas de réseau, pas de SQL (voir etl/io/).
Chaque bloc de code est précédé de « # ALG-03.k : <résumé> ».
"""

from ..models import GroupeNormalise, PositionMajoritaire


class ErreurDonnee(ValueError):
    """Compteur absent, négatif ou non entier : on ne calcule pas (ALG-03.2)."""


def _compteur(valeur: object, nom: str) -> int:
    # ALG-03.2 : absent, négatif ou non entier (booléen exclu) -> erreur de donnée
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 0:
        raise ErreurDonnee(f"{nom} invalide : {valeur!r}")
    return valeur


def calculer_position(
    pour: int,
    contre: int,
    abstentions: int,
    membres: int,
    position_source: str | None = None,
) -> PositionMajoritaire:
    """Position majoritaire d'après les seuls compteurs `pour`, `contre`, `abstentions`.

    Les non-votants ne sont pas une position : ils ne sont pas pris en argument.
    `position_source` est recopiée pour audit, jamais utilisée dans le calcul (ALG-03.10).
    """
    # ALG-03.1 et 2 : lecture des seuls P, C, A ; validation
    p = _compteur(pour, "pour")
    c = _compteur(contre, "contre")
    a = _compteur(abstentions, "abstentions")

    # ALG-03.3 : positions exprimées
    e = p + c + a

    # ALG-03.4 : aucun vote exprimé -> aucune position (la source met « pour » dans ce cas)
    if e == 0:
        return PositionMajoritaire(
            "aucune", "aucun_vote_exprime", 0, 0, False, 0, membres, position_source
        )

    # ALG-03.5 et 6 : effectif maximal et nombre de positions à ce niveau
    m = max(p, c, a)
    en_tete = [nom for nom, v in (("pour", p), ("contre", c), ("abstention", a)) if v == m]

    # ALG-03.7 : égalité en tête -> aucune position (désigner l'une serait arbitraire)
    if len(en_tete) > 1:
        return PositionMajoritaire("aucune", "egalite", e, m, False, e, membres, position_source)

    # ALG-03.8 et 9 : majorité relative stricte ; absolue si 2m > E (entiers, aucun flottant)
    return PositionMajoritaire(en_tete[0], None, e, m, 2 * m > e, e, membres, position_source)


def position_majoritaire_groupe(groupe: GroupeNormalise) -> PositionMajoritaire:
    """Applique ALG-03 à un groupe normalisé par ALG-02."""
    return calculer_position(
        groupe.pour,
        groupe.contre,
        groupe.abstentions,
        groupe.membres,
        groupe.position_majoritaire_source,
    )
