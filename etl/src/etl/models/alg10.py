"""Modèles propres à ALG-10 (indicateurs de groupe et comparaison)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LigneGroupeScrutin:
    """Une ligne (groupe, scrutin) de la sélection ; `groupe_id` vaut None pour un groupe PO0."""

    scrutin_id: str
    date_scrutin: str
    categorie: str
    resultat_code: str
    type_vote_code: str
    groupe_id: str | None
    membres: int
    pour: int
    contre: int
    abstentions: int
    non_votants: int


@dataclass(frozen=True)
class LigneVoteSelection:
    """Vote nominatif d'un député dans un groupe d'un scrutin de la sélection."""

    scrutin_id: str
    groupe_id: str | None
    depute_id: str
    position: str  # pour | contre | abstention | non_votant


@dataclass(frozen=True)
class IndicateursGroupe:
    """Indicateurs d'un groupe sur une sélection de scrutins : des effectifs, jamais un score."""

    groupe_id: str
    filtres: str
    nb_scrutins: int
    nb_scrutins_exclus_groupe_non_identifie: int
    membres_scrutins: int
    personnes_exprimees: int
    personnes_avec_vote: int
    pour: int
    contre: int
    abstentions: int
    non_votants: int
    sans_vote_enregistre: int
    exprimes: int
    scrutins_par_position_majoritaire: dict[str, int]
    bornes: tuple[int, ...]
    libelles_tranches: tuple[str, ...]
    repartition_part_majoritaire: tuple[int, ...]  # un nombre de scrutins par tranche


@dataclass(frozen=True)
class ScrutinCompare:
    """Un scrutin commun à deux groupes, avec les effectifs de chacun."""

    scrutin_id: str
    position_a: str
    raison_a: str | None
    exprimes_a: int
    majoritaire_a: int
    membres_a: int
    position_b: str
    raison_b: str | None
    exprimes_b: int
    majoritaire_b: int
    membres_b: int


@dataclass(frozen=True)
class ComparaisonGroupes:
    groupe_a: str
    groupe_b: str
    filtres: str
    scrutins_communs: int
    meme_position: list[ScrutinCompare]
    positions_differentes: list[ScrutinCompare]
    au_moins_une_sans_position: list[ScrutinCompare]
    scrutins_un_seul_present: int
