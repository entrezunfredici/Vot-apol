"""Modèles propres à ALG-09 (résolution des noms)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NomGroupe:
    id: str
    libelle: str
    sigle: str | None


@dataclass(frozen=True)
class NomDepute:
    id: str
    nom: str
    prenom: str | None
    civilite: str | None


@dataclass
class RapportResolution:
    """Rapport de résolution des noms (sortie d'ALG-09)."""

    groupes_references: int = 0
    groupes_resolus: int = 0
    groupes_non_resolus: list[dict[str, Any]] = field(default_factory=list)  # {id, raison, occurrences}
    deputes_references: int = 0
    deputes_resolus: int = 0
    deputes_non_resolus: list[dict[str, Any]] = field(default_factory=list)
    noms_modifies: list[dict[str, Any]] = field(default_factory=list)  # {id, ancien, nouveau}
    avertissements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResolutionNoms:
    """Noms à écrire (identifiants résolus seulement) et rapport."""

    groupes: list[NomGroupe]
    deputes: list[NomDepute]
    rapport: RapportResolution
