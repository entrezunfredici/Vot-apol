"""Modèles propres à ALG-06 (mises au point)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CorrectionGroupe:
    """Effectifs corrigés d'un groupe par les mises au point (ALG-06, partie B), pour l'affichage."""

    rang: int
    groupe_id: str
    pour_corrige: int
    contre_corrige: int
    abstentions_corrigees: int
    position_officielle: str
    position_corrigee: str
    raison_absence_corrigee: str | None
    change_position_majoritaire: bool
    nb_mises_au_point: int
