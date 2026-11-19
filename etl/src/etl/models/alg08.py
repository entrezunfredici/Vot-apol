"""Modèles propres à ALG-08 (classification)."""

from dataclasses import dataclass

CATEGORIES = (
    "texte_ensemble",
    "article",
    "amendement",
    "sous_amendement",
    "motion_censure",
    "motion_rejet",
    "autre_motion",
    "procedure",
    "declaration_gouvernement",
    "partie_loi_finances",
    "autre",
    "indetermine",
)


@dataclass(frozen=True)
class CorrectionTitre:
    """Correction manuelle validée par une personne (ALG-08) ; ne vaut que pour ce titre exact."""

    id: str
    titre: str
    categorie: str
    motif: str
    valide_le: str
    valide_par: str


@dataclass(frozen=True)
class Classification:
    """Catégorie d'un scrutin et manière dont elle a été obtenue (sortie d'ALG-08)."""

    categorie: str
    methode: str  # metadonnee_officielle | regle_titre | correction_manuelle | aucune
    regle_id: str | None
    confiance: str  # haute | moyenne | aucune
    a_verifier: bool
    version_regles: str
    avertissements: tuple[str, ...] = ()
