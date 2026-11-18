"""Modèles propres à ALG-12 (garde-fou de déploiement) : entrées, paramètres, décision."""

from dataclasses import dataclass, field
from typing import Any

from .alg05 import RapportReconciliation
from .alg07 import RapportImport
from .alg11 import RapportExport
from .alg13 import RapportTelechargement
from .commun import RapportLecture


@dataclass(frozen=True)
class ParametresDecision:
    """Seuils de la fiche (propositions à recaler après quelques semaines d'observation)."""

    seuil_modifies: int = 20
    seuil_nouveaux: int = 500


@dataclass(frozen=True)
class EntreesDecision:
    """Les seuls rapports dont dépend la décision (fonction pure : ni réseau ni horloge)."""

    lecture: RapportLecture
    importation: RapportImport
    reconciliation: RapportReconciliation  # niveau base
    export: RapportExport
    tests_ok: bool
    manifeste_courant: dict[str, Any]  # celui qui vient d'être exporté
    telechargement: RapportTelechargement | None = None  # None : exécution locale sans réseau
    verification: str | None = None  # statut d'ALG-14 (`ok` ou `echec`) ; None : non exécutée
    manifeste_precedent: dict[str, Any] | None = None  # version publiée ; None : aucune publication
    diff: dict[str, Any] | None = None  # calculé par ALG-11 (étape 8) à partir des deux manifestes
    noms_modifies: list[dict[str, Any]] = field(default_factory=list)  # RapportResolution (ALG-09)
    nombre_groupes_precedent: int | None = None  # meta.json publié
    indetermines_precedent: int | None = None  # qualite.json publié
    indetermines_courant: int | None = None
    forcer: bool = False
    mode_sur: bool = True  # actif au départ : jamais de publication automatique sans instruction


@dataclass(frozen=True)
class DecisionPublication:
    decision: str  # rien_a_faire | publier | attente_validation | bloquer
    raisons: tuple[dict[str, str], ...]  # {id, detail} : règles B, V puis avertissements A
    diff: dict[str, Any] | None
    donnees_sha256: str
    empreinte_entrees: str
    rapport_sha256: str  # SHA-256 du contenu de la décision : relie une validation à un état précis
