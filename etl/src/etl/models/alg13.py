"""Modèles propres à ALG-13 (téléchargement) : paramètres, réponse, stockage, rapport."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

MIO = 1024 * 1024


@dataclass(frozen=True)
class Parametres:
    """Paramètres de la fiche (valeurs validées le 2026-11-18, à recaler à l'usage)."""

    max_octets: int = 200 * MIO
    min_octets: int = 10 * MIO
    max_redirections: int = 5
    delai_connexion: float = 30.0
    delai_inactivite: float = 60.0
    delai_total: float = 15 * 60.0
    max_tentatives: int = 3
    attentes: tuple[float, ...] = (10.0, 60.0)
    retry_after_max: float = 120.0
    fraicheur_jours: int = 90
    taille_bloc: int = MIO
    user_agent: str = "voteapol-etl (donnees ouvertes; telechargement quotidien)"


class Reponse(Protocol):
    code: int
    entetes: dict[str, str]  # clés en minuscules

    def lire_blocs(self, taille: int) -> Iterator[bytes]: ...
    def fermer(self) -> None: ...


class Transport(Protocol):
    """Une requête GET, sans suivre les redirections ni envoyer cookie ou jeton."""

    def get(self, url: str, params: Parametres) -> Reponse: ...


class Temporaire(Protocol):
    def ecrire(self, bloc: bytes) -> None: ...


class Stockage(Protocol):
    def ouvrir_temporaire(self) -> Temporaire: ...
    def abandonner(self, temp: Temporaire) -> None: ...
    def conserver(self, temp: Temporaire, sha256: str) -> tuple[str, bool]: ...
    def retirer(self, chemin: str) -> None: ...
    def ecrire_provenance(self, provenance: dict[str, Any]) -> None: ...


@dataclass
class RapportTelechargement:
    statut: str = "echec"  # nouvelle | inchangee | echec
    url_demandee: str = ""
    url_finale: str = ""
    code_http: int | None = None
    tentatives: int = 0
    octets: int = 0
    sha256: str = ""
    chemin: str = ""
    entetes: dict[str, str] = field(default_factory=dict)
    avertissements: list[str] = field(default_factory=list)
    cause_echec: str | None = None
