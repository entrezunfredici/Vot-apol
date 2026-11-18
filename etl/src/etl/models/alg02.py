"""Modèles propres à ALG-02 (normalisation) : anomalies et résultat."""

from dataclasses import dataclass

from .commun import ScrutinNormalise


@dataclass(frozen=True)
class Anomalie:
    """Erreur ou avertissement de normalisation (ALG-02), avec le chemin du champ concerné."""

    chemin: str
    code: str
    detail: str = ""


@dataclass(frozen=True)
class ResultatNormalisation:
    """Sortie d'ALG-02 : un scrutin OU des erreurs (jamais les deux), plus les avertissements."""

    scrutin: ScrutinNormalise | None
    erreurs: list[Anomalie]
    avertissements: list[Anomalie]
