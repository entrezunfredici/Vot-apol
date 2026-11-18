"""Modèles propres à ALG-05 (réconciliation) : chiffres à contrôler, écarts et rapport."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GroupeAControler:
    rang: int
    membres: int
    compteurs: dict[str, int]  # position -> compteur du groupe (source)
    lignes: dict[str, int]  # position -> nombre de lignes de vote nominatif
    abstentions_doublon_source: int | None = None  # niveau lot seulement (R14)


@dataclass(frozen=True)
class ScrutinAControler:
    """Chiffres d'un scrutin, quelle que soit leur provenance (lot ou base)."""

    id: str
    numero: int
    pour: int
    contre: int
    abstentions: int
    non_votants: int
    suffrages_exprimes: int
    nombre_votants: int
    lignes_scrutin: dict[str, int]  # position -> lignes de vote du scrutin
    groupes: list[GroupeAControler]
    # niveau lot seulement (champs non stockés, ALG-04) :
    sort_code: str | None = None
    type_vote_code: str | None = None
    nbr_suffrages_requis: int | None = None
    non_votants_volontaires: int | None = None
    # niveau base seulement :
    a_totaux: bool = True
    references_orphelines: int = 0  # lignes dont groupe_id ou depute_id est inconnu (R15)


@dataclass(frozen=True)
class Ecart:
    controle: str
    scrutin_id: str | None
    groupe_rang: int | None
    detail: str | None  # position (R08, R09) ou objet vérifié (R17)
    attendu: int
    obtenu: int
    connu: bool = False


@dataclass(frozen=True)
class EcartConnu:
    controle: str
    scrutin_id: str | None
    groupe_rang: int | None
    detail: str | None
    attendu: int
    obtenu: int
    motif: str
    valide_le: str
    valide_par: str

    def cle(self) -> tuple:
        return (self.controle, self.scrutin_id, self.groupe_rang, self.detail, self.attendu,
                self.obtenu)  # fmt: skip


@dataclass
class RapportReconciliation:
    niveau: str
    scrutins_controles: int = 0
    controles: dict[str, dict[str, int]] = field(
        default_factory=dict
    )  # id -> nb_verifies/nb_ecarts
    ecarts: list[Ecart] = field(default_factory=list)  # détail plafonné par contrôle
    avertissements: list[str] = field(default_factory=list)
    statut: str = "ok"  # ok | ecarts_connus | ecarts_informatifs | ecarts_nouveaux
