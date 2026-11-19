"""Modèles de données du projet : `commun` (partagés) et un fichier par algorithme.

Règle : un modèle va dans `commun.py` dès qu'un deuxième algorithme l'importe ;
sinon il reste dans le fichier de son algorithme. `commun.py` n'importe rien d'autre du
projet et les fichiers `algNN.py` n'importent que `commun.py` et leurs voisins du paquet.
Tout est ré-exporté ici : `from etl.models import X` fonctionne pour tous les modèles.
"""

from .alg02 import (
    Anomalie,
    ResultatNormalisation,
)
from .alg05 import (
    Ecart,
    EcartConnu,
    GroupeAControler,
    RapportReconciliation,
    ScrutinAControler,
)
from .alg06 import (
    CorrectionGroupe,
)
from .alg07 import (
    AncienScrutin,
    Depot,
    RapportImport,
    ScrutinRefuse,
)
from .alg08 import (
    CATEGORIES,
    Classification,
    CorrectionTitre,
)
from .alg09 import (
    NomDepute,
    NomGroupe,
    RapportResolution,
    ResolutionNoms,
)
from .alg10 import (
    ComparaisonGroupes,
    IndicateursGroupe,
    LigneGroupeScrutin,
    LigneVoteSelection,
    ScrutinCompare,
)
from .alg11 import (
    ContexteExport,
    ParametresExport,
    RapportExport,
    ReferentielsExport,
)
from .alg12 import (
    DecisionPublication,
    EntreesDecision,
    ParametresDecision,
)
from .alg13 import (
    MIO,
    Parametres,
    RapportTelechargement,
    Reponse,
    Stockage,
    Temporaire,
    Transport,
)
from .commun import (
    POSITIONS_VOTE,
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
    PositionMajoritaire,
    RapportLecture,
    ScrutinNormalise,
    Votant,
)

__all__ = [
    "CATEGORIES",
    "MIO",
    "POSITIONS_VOTE",
    "AncienScrutin",
    "Anomalie",
    "Classification",
    "ComparaisonGroupes",
    "Comptages",
    "ContexteExport",
    "CorrectionGroupe",
    "CorrectionTitre",
    "DecisionPublication",
    "Depot",
    "Ecart",
    "EcartConnu",
    "EntreeAcceptee",
    "EntreeRefusee",
    "EntreesDecision",
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
    "NomDepute",
    "NomGroupe",
    "Parametres",
    "ParametresDecision",
    "ParametresExport",
    "PositionMajoritaire",
    "RapportExport",
    "RapportImport",
    "RapportLecture",
    "RapportReconciliation",
    "RapportResolution",
    "RapportTelechargement",
    "ReferentielsExport",
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
