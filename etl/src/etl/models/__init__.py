"""Modèles de données du projet : `commun` (partagés) et un fichier par algorithme.

Règle : un modèle va dans `commun.py` dès qu'un deuxième algorithme l'importe ;
sinon il reste dans le fichier de son algorithme. `commun.py` n'importe rien d'autre du
projet et les fichiers `algNN.py` n'importent que `commun.py` et leurs voisins du paquet.
Tout est ré-exporté ici : `from etl.models import X` fonctionne pour tous les modèles.
"""

from .commun import (
    Comptages,
    EntreeAcceptee,
    EntreeRefusee,
    GroupeNormalise,
    LigneCorrection,
    LigneGroupe,
    LigneMiseAuPoint,
    LigneScrutin,
    LigneTotaux,
    LigneVote,
    LotScrutin,
    POSITIONS_VOTE,
    PositionMajoritaire,
    RapportLecture,
    ScrutinNormalise,
    Votant,
)  # noqa: F401
from .alg02 import (
    Anomalie,
    ResultatNormalisation,
)  # noqa: F401
from .alg05 import (
    Ecart,
    EcartConnu,
    GroupeAControler,
    RapportReconciliation,
    ScrutinAControler,
)  # noqa: F401
from .alg06 import (
    CorrectionGroupe,
)  # noqa: F401
from .alg07 import (
    AncienScrutin,
    Depot,
    RapportImport,
    ScrutinRefuse,
)  # noqa: F401
from .alg08 import (
    CATEGORIES,
    Classification,
    CorrectionTitre,
)  # noqa: F401
from .alg09 import (
    NomDepute,
    NomGroupe,
    RapportResolution,
    ResolutionNoms,
)  # noqa: F401
from .alg10 import (
    ComparaisonGroupes,
    IndicateursGroupe,
    LigneGroupeScrutin,
    LigneVoteSelection,
    ScrutinCompare,
)  # noqa: F401
from .alg11 import (
    ContexteExport,
    ParametresExport,
    RapportExport,
    ReferentielsExport,
)  # noqa: F401
from .alg12 import (
    DecisionPublication,
    EntreesDecision,
    ParametresDecision,
)  # noqa: F401
from .alg13 import (
    MIO,
    Parametres,
    RapportTelechargement,
    Reponse,
    Stockage,
    Temporaire,
    Transport,
)  # noqa: F401

__all__ = [
    "DecisionPublication",
    "EntreesDecision",
    "ParametresDecision",
    "ContexteExport",
    "ParametresExport",
    "RapportExport",
    "ReferentielsExport",
    "AncienScrutin",
    "Anomalie",
    "CATEGORIES",
    "Classification",
    "ComparaisonGroupes",
    "Comptages",
    "CorrectionGroupe",
    "CorrectionTitre",
    "Depot",
    "Ecart",
    "EcartConnu",
    "EntreeAcceptee",
    "EntreeRefusee",
    "GroupeAControler",
    "GroupeNormalise",
    "IndicateursGroupe",
    "LigneCorrection",
    "LigneGroupe",
    "LigneGroupeScrutin",
    "LigneMiseAuPoint",
    "LigneScrutin",
    "LigneTotaux",
    "LigneVote",
    "LigneVoteSelection",
    "LotScrutin",
    "MIO",
    "NomDepute",
    "NomGroupe",
    "POSITIONS_VOTE",
    "Parametres",
    "PositionMajoritaire",
    "RapportImport",
    "RapportLecture",
    "RapportReconciliation",
    "RapportResolution",
    "RapportTelechargement",
    "Reponse",
    "ResolutionNoms",
    "ResultatNormalisation",
    "ScrutinAControler",
    "ScrutinCompare",
    "ScrutinNormalise",
    "ScrutinRefuse",
    "Stockage",
    "Temporaire",
    "Transport",
    "Votant",
]
