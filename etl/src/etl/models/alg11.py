"""Modèles propres à ALG-11 (export statique) : contexte, paramètres, référentiels, rapport."""

from dataclasses import dataclass, field
from typing import Any

from .alg08 import CorrectionTitre
from .alg13 import MIO


@dataclass(frozen=True)
class ParametresExport:
    """Limites de l'hébergement (fiche ALG-11, « Paramètres »)."""

    max_fichiers_echec: int = 19_000
    max_fichiers_avertissement: int = 15_000
    max_octets_fichier_echec: int = 20 * MIO
    max_octets_fichier_avertissement: int = 1 * MIO
    pas_echantillon: int = 50  # un scrutin sur 50 est relu et comparé aux lignes de la base (ALG-11.13)
    bornes: tuple[int, ...] = (20, 40, 60, 80)  # tranches d'ALG-10 pour stats.json


@dataclass(frozen=True)
class ReferentielsExport:
    """Noms résolus (ALG-09) : tout identifiant non résolu a un nom à None."""

    groupes: dict[str, tuple[str | None, str | None]]  # id -> (libellé, sigle)
    deputes: dict[str, tuple[str | None, str | None, str | None]]  # id -> (nom, prénom, civilité)


@dataclass(frozen=True)
class ContexteExport:
    """Tout ce qui n'est pas un scrutin ; aucune heure n'est lue sur l'horloge système."""

    archive_sha256: str
    type_empreinte: str  # fichier | manifeste
    donnees_du: str  # date de synchronisation, issue de la base (table imports)
    version_etl: str
    version_regles_classification: str
    statut_reconciliation: str  # résultat d'ALG-05 niveau base
    nombre_scrutins_base: int  # comptes de la base, comparés à meta.json (ALG-11.12)
    ecarts_connus: list[dict[str, Any]] = field(default_factory=list)  # écarts connus publiés
    corrections: tuple[CorrectionTitre, ...] = ()  # corrections manuelles d'ALG-08
    entrees: dict[str, Any] = field(default_factory=dict)  # versions, référentiels (ALG-12)
    manifeste_precedent: dict[str, Any] | None = None  # manifeste de la version publiée


@dataclass
class RapportExport:
    statut: str = "echec"  # ok | echec
    cause_echec: str | None = None
    detail_echec: str = ""
    nombre_scrutins: int = 0
    nombre_groupes: int = 0
    fichiers_par_type: dict[str, int] = field(default_factory=dict)
    nombre_fichiers: int = 0
    octets_total: int = 0
    plus_gros_fichier: tuple[str, int] = ("", 0)
    donnees_sha256: str = ""
    version_donnees: str = ""
    avertissements: list[str] = field(default_factory=list)
