"""Modèles propres à ALG-07 (import idempotent) : rapport, scrutin refusé, accès à la base."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from .commun import LotScrutin


@dataclass(frozen=True)
class ScrutinRefuse:
    """Scrutin écarté avant l'import (erreur ALG-02, 04 ou 06) : rien n'est écrit (ALG-07.4)."""

    id: str
    cause: str


@dataclass(frozen=True)
class AncienScrutin:
    """Ce que la base contient pour un scrutin, pour calculer `champs_modifies` (ALG-07.9)."""

    scrutin: dict[str, Any]
    totaux: dict[str, Any]
    groupes: dict[int, dict[str, Any]]  # rang -> colonnes
    nb_votes: int
    nb_mises_au_point: int


@dataclass
class RapportImport:
    """Journal complet d'une exécution (sortie de la fiche)."""

    import_id: int | None = None
    archive_sha256: str = ""
    type_empreinte: str = ""
    statut_lecture: str = ""
    fichiers_vus: int = 0
    fichiers_ok: int = 0
    fichiers_en_echec: int = 0
    nouveaux: int = 0
    inchanges: int = 0
    modifies: list[dict[str, Any]] = field(default_factory=list)
    retraites: list[dict[str, Any]] = field(default_factory=list)
    refuses: list[dict[str, str]] = field(default_factory=list)
    absents_de_l_archive: list[str] = field(default_factory=list)
    duree_secondes: float = 0.0
    statut: str = "echoue"  # termine | termine_avec_erreurs | echoue | interrompu | simulation
    motif_echec: str | None = None


class Depot(Protocol):
    """Accès à la base nécessaire à ALG-07 (implémenté par io/db.py)."""

    def version_schema(self) -> int: ...
    def debut_import(self, importe_le: str, archive_sha256: str) -> int: ...
    def debut_lot(self) -> None: ...
    def valider_lot(self) -> None: ...
    def annuler_lot(self) -> None: ...
    def lire_empreinte(self, scrutin_id: str) -> tuple[str, str] | None: ...
    def lire_ancien(self, scrutin_id: str) -> AncienScrutin: ...
    def inserer_references(self, groupes: list[str], deputes: list[str]) -> None: ...
    def supprimer_enfants(self, scrutin_id: str) -> None: ...
    def ecrire_scrutin(self, lot: LotScrutin) -> None: ...
    def ids_en_base(self) -> set[str]: ...
    def terminer_import(self, import_id: int, termine_le: str, rapport: RapportImport) -> None: ...
