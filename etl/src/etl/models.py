"""Dataclasses partagées (Scrutin, VoteGroupe, MiseAuPoint…), à définir avec les fiches validées."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EntreeAcceptee:
    """Un fichier de scrutin accepté par ALG-01 (sortie 1 de la fiche)."""

    nom: str
    numero: int
    sha256_fichier: str
    octets_bruts: int
    document_json: dict[str, Any]


@dataclass(frozen=True)
class EntreeRefusee:
    """Une entrée refusée par ALG-01 et la cause du refus."""

    nom: str
    motif: str


@dataclass
class RapportLecture:
    """Rapport de lecture exact d'une archive (sortie 2 de ALG-01)."""

    type_source: str = ""  # "zip" | "dossier"
    empreinte_archive: str = ""
    type_empreinte: str = ""  # "fichier" | "manifeste"
    entrees_vues: int = 0
    acceptees: int = 0
    ignorees: int = 0
    refusees: list[EntreeRefusee] = field(default_factory=list)
    octets_lus: int = 0
    numero_min: int | None = None
    numero_max: int | None = None
    trous: list[int] = field(default_factory=list)  # au plus `max_trous_detailles` numéros
    nb_trous: int = 0  # nombre exact de numéros absents (la liste ci-dessus peut être tronquée)
    avertissements: list[str] = field(default_factory=list)
    statut: str = "echec"  # "complet" | "partiel" | "echec"
    motif_echec: str | None = None
    liens_symboliques_ignores: int = 0


@dataclass(frozen=True)
class Anomalie:
    """Erreur ou avertissement de normalisation (ALG-02), avec le chemin du champ concerné."""

    chemin: str
    code: str
    detail: str = ""


@dataclass(frozen=True)
class Votant:
    """Vote individuel d'un député dans un groupe (ALG-02)."""

    acteur_ref: str
    mandat_ref: str
    position: str  # pour | contre | abstention | non_votant
    par_delegation: bool
    cause: str | None  # MG | PSE | PAN, uniquement pour un non-votant


@dataclass(frozen=True)
class LigneCorrection:
    """Mise au point ou dysfonctionnement déclaré (ALG-02), rattaché plus tard par ALG-06."""

    acteur_ref: str
    mandat_ref: str
    position_declaree: str
    par_delegation: bool
    origine: str  # mise_au_point | dysfonctionnement


@dataclass(frozen=True)
class GroupeNormalise:
    """Groupe tel qu'enregistré dans le scrutin ; `organe_ref` vaut None si non résolue (PO0)."""

    rang: int
    organe_ref: str | None
    membres: int
    pour: int
    contre: int
    abstentions: int
    non_votants: int
    position_majoritaire_source: str
    abstentions_doublon_source: int  # copie de nonVotantsVolontaires, réservée au contrôle ALG-05
    votants: list[Votant]


@dataclass(frozen=True)
class ScrutinNormalise:
    """Scrutin typé et sans ambiguïté (sortie d'ALG-02)."""

    id: str
    numero: int
    legislature: int
    date_scrutin: str
    session_ref: str
    seance_ref: str
    organe_ref: str
    quantieme_jour_seance: int
    lieu_vote: str
    type_vote_code: str
    type_vote_libelle: str
    type_majorite: str
    titre: str
    objet_libelle: str
    dossier_ref: str | None
    dossier_libelle: str | None
    demandeur_texte: str | None
    mode_publication: str
    sort_code: str
    sort_libelle: str
    nombre_votants: int
    suffrages_exprimes: int
    nbr_suffrages_requis: int
    pour: int
    contre: int
    abstentions: int
    non_votants: int
    non_votants_volontaires: int
    groupes: list[GroupeNormalise]
    mises_au_point: list[LigneCorrection]
    dysfonctionnements: list[LigneCorrection]


@dataclass(frozen=True)
class ResultatNormalisation:
    """Sortie d'ALG-02 : un scrutin OU des erreurs (jamais les deux), plus les avertissements."""

    scrutin: ScrutinNormalise | None
    erreurs: list[Anomalie]
    avertissements: list[Anomalie]


@dataclass(frozen=True)
class PositionMajoritaire:
    """Position majoritaire calculée d'un groupe sur un scrutin (sortie d'ALG-03)."""

    position: str  # pour | contre | abstention | aucune
    raison_absence: str | None  # aucun_vote_exprime | egalite | None
    exprimes: int  # E = pour + contre + abstentions
    effectif_majoritaire: int  # m
    majorite_absolue: bool  # 2·m > E (faux si aucune position)
    participation_num: int  # E
    participation_den: int  # effectif du groupe (nombreMembresGroupe)
    position_source: str | None = None  # positionMajoritaire de la source, pour audit seulement
