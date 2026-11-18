"""ALG-11.10 : schémas des fichiers publics et validateur écrit à la main (sans dépendance).

Le contrat est décrit dans docs/data-dictionary.md ; ces schémas en sont la forme exécutable.
Un fichier non conforme n'est jamais publié.
"""

from dataclasses import dataclass
from typing import Any


class _Type:
    def verifier(self, v: Any, chemin: str, erreurs: list[str]) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class Chaine(_Type):
    non_vide: bool = False

    def verifier(self, v, chemin, erreurs):
        if not isinstance(v, str) or (self.non_vide and not v):
            erreurs.append(f"{chemin} : chaîne attendue, reçu {v!r}")


@dataclass(frozen=True)
class Entier(_Type):
    minimum: int | None = None

    def verifier(self, v, chemin, erreurs):
        if isinstance(v, bool) or not isinstance(v, int):
            erreurs.append(f"{chemin} : entier attendu, reçu {v!r}")
        elif self.minimum is not None and v < self.minimum:
            erreurs.append(f"{chemin} : entier ≥ {self.minimum} attendu, reçu {v}")


@dataclass(frozen=True)
class Booleen(_Type):
    def verifier(self, v, chemin, erreurs):
        if not isinstance(v, bool):
            erreurs.append(f"{chemin} : booléen attendu, reçu {v!r}")


@dataclass(frozen=True)
class Enum(_Type):
    valeurs: tuple

    def verifier(self, v, chemin, erreurs):
        if isinstance(v, bool) or v not in self.valeurs:
            erreurs.append(f"{chemin} : valeur parmi {list(self.valeurs)} attendue, reçu {v!r}")


@dataclass(frozen=True)
class OuNul(_Type):
    interieur: _Type

    def verifier(self, v, chemin, erreurs):
        if v is not None:
            self.interieur.verifier(v, chemin, erreurs)


@dataclass(frozen=True)
class Liste(_Type):
    element: _Type

    def verifier(self, v, chemin, erreurs):
        if not isinstance(v, list):
            erreurs.append(f"{chemin} : liste attendue")
            return
        for i, x in enumerate(v):
            self.element.verifier(x, f"{chemin}[{i}]", erreurs)


@dataclass(frozen=True)
class Tuple(_Type):
    """Liste de longueur fixe dont chaque position a son type (votes compacts)."""

    elements: tuple[_Type, ...]

    def verifier(self, v, chemin, erreurs):
        if not isinstance(v, list) or len(v) != len(self.elements):
            erreurs.append(f"{chemin} : liste de {len(self.elements)} éléments attendue")
            return
        for i, (t, x) in enumerate(zip(self.elements, v, strict=True)):
            t.verifier(x, f"{chemin}[{i}]", erreurs)


@dataclass(frozen=True)
class Objet(_Type):
    """Objet à clés exactes : une clé absente ou en trop est une erreur."""

    champs: dict[str, _Type]

    def verifier(self, v, chemin, erreurs):
        if not isinstance(v, dict):
            erreurs.append(f"{chemin} : objet attendu")
            return
        for cle in sorted(set(self.champs) - set(v)):
            erreurs.append(f"{chemin}.{cle} : champ manquant")
        for cle in sorted(set(v) - set(self.champs)):
            erreurs.append(f"{chemin}.{cle} : champ inattendu")
        for cle, t in self.champs.items():
            if cle in v:
                t.verifier(v[cle], f"{chemin}.{cle}", erreurs)


@dataclass(frozen=True)
class Libre(_Type):
    """Contenu non contraint (rapport de différences, manifeste), mais JSON valide."""

    def verifier(self, v, chemin, erreurs):
        pass


POSITIONS = ("pour", "contre", "abstention", "non_votant")
POSITIONS_MAJORITAIRES = ("pour", "contre", "abstention", "aucune")
RAISONS = ("aucun_vote_exprime", "egalite")
_S, _I, _B = Chaine(), Entier(0), Booleen()

_CATEGORIE_INDEX = Objet({"valeur": _S, "methode": _S, "a_verifier": _B})
_CATEGORIE = Objet({"valeur": _S, "methode": _S, "confiance": _S, "a_verifier": _B})
_POSITION = Objet(
    {
        "position": Enum(POSITIONS_MAJORITAIRES),
        "raison_absence": OuNul(Enum(RAISONS)),
        "exprimes": _I,
        "m": _I,
        "majorite_absolue": _B,
    }
)
_TOTAUX_INDEX = Objet(
    {
        "pour": _I, "contre": _I, "abstentions": _I, "non_votants": _I,
        "suffrages_exprimes": _I, "nombre_votants": _I,
    }
)  # fmt: skip
_CORRECTION = Objet(
    {
        "pour_corrige": _I, "contre_corrige": _I, "abstentions_corrigees": _I,
        "position_officielle": Enum(POSITIONS_MAJORITAIRES),
        "position_corrigee": Enum(POSITIONS_MAJORITAIRES),
        "raison_absence_corrigee": OuNul(Enum(RAISONS)),
        "change_position_majoritaire": _B, "nb_mises_au_point": _I,
    }
)  # fmt: skip
_GROUPE_SCRUTIN = Objet(
    {
        "rang": Entier(1), "groupe_id": OuNul(_S), "ventilation_disponible": _B,
        "membres": _I, "pour": _I, "contre": _I, "abstentions": _I, "non_votants": _I,
        "sans_vote_enregistre": OuNul(_I), "position_majoritaire": OuNul(_POSITION),
        "correction_mise_au_point": OuNul(_CORRECTION),
    }
)  # fmt: skip
_MISE_AU_POINT = Objet(
    {
        "depute_id": _S, "groupe_rang": OuNul(_I), "groupe_id": OuNul(_S),
        "position_initiale": OuNul(Enum(POSITIONS)), "position_declaree": _S,
        "par_delegation": Enum((0, 1)), "statut": Enum(("rattachee", "introuvable")),
        "effet": OuNul(Enum(("sans_effet", "modifie_position"))),
    }
)  # fmt: skip

SCHEMA_SCRUTIN = Objet(
    {
        "id": _S, "numero": Entier(1), "date": _S, "titre": _S,
        "type_vote": Objet({"code": _S, "libelle": _S}),
        "resultat": _S, "categorie": _CATEGORIE,
        "source": Objet({"fichier": _S, "sha256": _S, "archive_sha256": _S, "lien_officiel": _S}),
        "totaux": Objet(
            {
                "pour": _I, "contre": _I, "abstentions": _I, "non_votants": _I,
                "suffrages_exprimes": _I, "nombre_votants": _I,
                "sans_vote_enregistre": OuNul(_I),
            }
        ),
        "groupes": Liste(_GROUPE_SCRUTIN),
        "votes": Liste(Tuple((_S, _I, Enum(POSITIONS), Enum((0, 1)), OuNul(_S)))),
        "mises_au_point": Liste(_MISE_AU_POINT),
        "dysfonctionnements": Liste(_MISE_AU_POINT),
    }
)  # fmt: skip

SCHEMA_INDEX_FRAGMENT = Objet(
    {
        "mois": _S,
        "scrutins": Liste(
            Objet(
                {
                    "id": _S, "numero": Entier(1), "date": _S, "titre": _S,
                    "categorie": _CATEGORIE_INDEX, "resultat": _S, "totaux": _TOTAUX_INDEX,
                }
            )
        ),
    }
)  # fmt: skip
SCHEMA_INDEX = Objet(
    {"fragments": Liste(Objet({"mois": _S, "nombre_scrutins": Entier(1), "fichier": _S}))}
)
SCHEMA_GROUPES = Objet(
    {
        "groupes": Liste(
            Objet({"id": _S, "libelle": OuNul(_S), "sigle": OuNul(_S), "nombre_scrutins": Entier(1)})
        )
    }
)
# `groupes/<id>.json` : une ligne par scrutin du groupe, en tableau ; les colonnes sont nommées une
# seule fois (même contenu qu'un objet par ligne, environ 3 fois plus petit : décision du 2026-11-18)
COLONNES_GROUPE = (
    "scrutin_id", "numero", "date", "categorie", "membres", "pour", "contre", "abstentions",
    "non_votants", "sans_vote_enregistre", "position", "raison_absence", "exprimes", "m",
    "majorite_absolue",
)  # fmt: skip
SCHEMA_GROUPE = Objet(
    {
        "groupe_id": _S, "libelle": OuNul(_S), "sigle": OuNul(_S),
        "colonnes": Liste(_S),
        "scrutins": Liste(
            Tuple(
                (
                    _S, Entier(1), _S, _S, _I, _I, _I, _I, _I, _I,
                    Enum(POSITIONS_MAJORITAIRES), OuNul(Enum(RAISONS)), _I, _I, _B,
                )
            )
        ),
    }
)  # fmt: skip
SCHEMA_DEPUTES = Objet(
    {
        "deputes": Liste(
            Objet({"id": _S, "nom": OuNul(_S), "prenom": OuNul(_S), "civilite": OuNul(_S)})
        )
    }
)
_INDICATEURS = Objet(
    {
        "groupe_id": _S, "nb_scrutins": _I, "nb_scrutins_exclus_groupe_non_identifie": _I,
        "membres_scrutins": _I, "personnes_exprimees": _I, "personnes_avec_vote": _I,
        "pour": _I, "contre": _I, "abstentions": _I, "non_votants": _I,
        "sans_vote_enregistre": _I, "exprimes": _I,
        "scrutins_par_position_majoritaire": Objet(
            {
                "pour": _I, "contre": _I, "abstention": _I, "egalite": _I,
                "aucun_vote_exprime": _I,
            }
        ),
        "repartition_part_majoritaire": Liste(_I),
    }
)  # fmt: skip
SCHEMA_STATS = Objet(
    {
        "bornes": Liste(Entier(1)), "libelles_tranches": Liste(_S),
        "selections": Liste(
            Objet(
                {"id": _S, "filtres": _S, "nombre_scrutins": _I, "groupes": Liste(_INDICATEURS)}
            )
        ),
    }
)  # fmt: skip
SCHEMA_QUALITE = Objet(
    {
        "schema": _S, "statut_reconciliation": _S, "nombre_scrutins": _I,
        "archive_sha256": _S, "donnees_du": _S,
        "ecarts_connus": Liste(
            Objet(
                {
                    "controle": _S, "scrutin_id": OuNul(_S), "detail": OuNul(_S),
                    "attendu": Entier(), "obtenu": Entier(), "motif": _S, "valide_le": _S,
                }
            )
        ),
        "classification": Objet(
            {"par_categorie": Libre(), "a_verifier": _I, "indetermine": _I}
        ),
        "noms_non_resolus": Objet({"groupes": _I, "deputes": _I}),
        "modifications": OuNul(Libre()),
    }
)  # fmt: skip
SCHEMA_MANIFESTE = Objet(
    {
        "schema": _S, "entrees": Libre(), "empreinte_entrees": _S, "donnees_sha256": _S,
        "scrutins": Libre(),
    }
)
SCHEMA_META = Objet(
    {
        "schema": _S, "nombre_scrutins": Entier(1), "nombre_groupes": _I,
        "premiere_date": _S, "derniere_date": _S, "donnees_du": _S, "version_donnees": _S,
        "archive_sha256": _S, "type_empreinte": _S, "version_etl": _S,
        "version_regles_classification": _S,
    }
)  # fmt: skip


def schema_pour(chemin: str) -> Objet | None:
    """Schéma du fichier public `chemin` (relatif à /data/v1/), ou None s'il est inconnu."""
    if chemin.startswith("scrutins-index/"):
        return SCHEMA_INDEX_FRAGMENT
    if chemin.startswith("scrutins/"):
        return SCHEMA_SCRUTIN
    if chemin.startswith("groupes/"):
        return SCHEMA_GROUPE
    return {
        "meta.json": SCHEMA_META,
        "scrutins-index.json": SCHEMA_INDEX,
        "groupes.json": SCHEMA_GROUPES,
        "deputes.json": SCHEMA_DEPUTES,
        "stats.json": SCHEMA_STATS,
        "qualite.json": SCHEMA_QUALITE,
        "manifeste.json": SCHEMA_MANIFESTE,
    }.get(chemin)


def valider(chemin: str, document: Any) -> list[str]:
    """Erreurs de conformité du document (liste vide = conforme)."""
    schema = schema_pour(chemin)
    if schema is None:
        return [f"{chemin} : aucun schéma pour ce fichier"]
    erreurs: list[str] = []
    schema.verifier(document, chemin, erreurs)
    if schema is SCHEMA_GROUPE and isinstance(document, dict):
        if document.get("colonnes") != list(COLONNES_GROUPE):
            erreurs.append(f"{chemin}.colonnes : colonnes attendues {list(COLONNES_GROUPE)}")
    return erreurs
