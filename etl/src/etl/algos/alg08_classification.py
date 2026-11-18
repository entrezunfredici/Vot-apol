"""ALG-08 : Classification des scrutins (catégorie, confiance, « à vérifier »).

Spécification : docs/algorithmes/ALG-08-classification.md (statut « Validé », version 3).
Fonction pure : pas de disque, pas de réseau, pas de SQL (voir etl/io/). La catégorie n'est
pas stockée : elle est recalculée à l'export (ALG-11).
Chaque bloc de code est précédé de « # ALG-08.k : <résumé> ».
"""

import json
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

from ..models import CATEGORIES, Classification, CorrectionTitre

# CHOIX: version portée à chaque résultat ; à incrémenter à chaque changement de règle
# RAISON: la catégorie doit être reproductible (mêmes entrées + même version = mêmes résultats)
VERSION_REGLES = "alg08-v3"

# R1 n'est pas ancrée (« sur la motion de rejet préalable… ») ; les autres le sont au début du titre
_REGLES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("R1", "motion_rejet", re.compile(r"motion de rejet préalable")),
    ("R2", "declaration_gouvernement",
     re.compile(r"^la déclaration (du gouvernement|de politique générale)")),
    ("R3", "procedure",
     re.compile(r"^(la demande de |la proposition du gouvernement de prolonger)")),
    ("R4", "sous_amendement", re.compile(r"^(l'|le )sous-amendement\b")),
    ("R5", "amendement", re.compile(r"^(l'|le )amendement\b")),
    ("R6", "article", re.compile(r"^l'article\b")),
    ("R7", "partie_loi_finances", re.compile(r"^la (première|deuxième|troisième) partie\b")),
    ("R8", "texte_ensemble",
     re.compile(r"^(l'ensemble (du|de la|des) |la proposition de (loi|résolution)|le projet de loi)")),
)  # fmt: skip

_ESPACES = re.compile(r"\s+")


class ErreurCorrections(Exception):
    """Fichier de corrections illisible ou mal formé : arrêt (jamais « aucune correction »)."""


def normaliser_titre(titre: str) -> str:
    """ALG-08.3 : NFC, minuscules, apostrophes ’ et ‘ -> ', espaces réduits, bords retirés."""
    t = unicodedata.normalize("NFC", titre).lower().replace("’", "'").replace("‘", "'")
    return _ESPACES.sub(" ", t).strip()


def charger_corrections(chemin: Path | str) -> list[CorrectionTitre]:
    """Lit la table de corrections manuelles ; toute entrée mal formée est une erreur."""
    try:
        brut = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ErreurCorrections(f"fichier illisible : {exc}") from exc
    if not isinstance(brut, list):
        raise ErreurCorrections("la racine doit être une liste")
    champs = {"id", "titre", "categorie", "motif", "valide_le", "valide_par"}
    corrections, ids = [], set()
    for i, e in enumerate(brut):
        if not isinstance(e, dict) or set(e) != champs:
            raise ErreurCorrections(f"entrée {i} : champs attendus {sorted(champs)}")
        if not all(isinstance(e[c], str) and e[c] for c in champs):
            raise ErreurCorrections(f"entrée {i} : tous les champs sont des textes non vides")
        if e["categorie"] not in CATEGORIES or e["categorie"] == "indetermine":
            raise ErreurCorrections(f"entrée {i} : catégorie inconnue {e['categorie']!r}")
        if e["id"] in ids:
            raise ErreurCorrections(f"entrée {i} : identifiant en double {e['id']!r}")
        ids.add(e["id"])
        corrections.append(CorrectionTitre(**e))
    return corrections


def classifier(
    scrutin_id: str,
    type_vote_code: str,
    titre: str,
    corrections: Iterable[CorrectionTitre] = (),
) -> Classification:
    """Catégorie d'un scrutin : une et une seule, avec sa méthode et sa confiance."""
    avertissements: list[str] = []

    # ALG-08.1 : une correction validée, pour ce titre exact, prime ; titre changé = obsolète
    for c in corrections:
        if c.id == scrutin_id:
            if c.titre == titre:
                return Classification(
                    c.categorie, "correction_manuelle", None, "haute", False, VERSION_REGLES
                )
            avertissements.append("correction_obsolete")
            break

    t = normaliser_titre(titre)

    # ALG-08.2 : métadonnée officielle (motion de censure) ; incohérence avec le titre signalée
    if type_vote_code == "MOC":
        incoherent = "motion de censure" not in t
        if incoherent:
            avertissements.append("incoherence_metadonnee")
        return Classification(
            "motion_censure",
            "metadonnee_officielle",
            "M0",
            "haute",
            incoherent,
            VERSION_REGLES,
            tuple(avertissements),
        )

    # ALG-08.4 : toutes les règles qui correspondent (ALG-08.3 : titre déjà normalisé)
    trouvees = [(rid, cat) for rid, cat, motif in _REGLES if motif.search(t)]
    categories = {cat for _, cat in trouvees}

    # ALG-08.5 : deux catégories différentes = ambiguïté, jamais un choix arbitraire
    if len(categories) >= 2:
        avertissements.append("regles_en_conflit")
        return Classification(
            "indetermine", "aucune", None, "aucune", True, VERSION_REGLES, tuple(avertissements)
        )

    # ALG-08.6 : une seule catégorie, déduite d'un titre : jamais présentée comme une certitude
    if len(categories) == 1:
        regle_id, categorie = trouvees[0]
        return Classification(
            categorie, "regle_titre", regle_id, "moyenne", True, VERSION_REGLES,
            tuple(avertissements),
        )  # fmt: skip

    # ALG-08.7 : aucune règle : « non déterminé » vaut mieux qu'une catégorie inventée
    return Classification(
        "indetermine", "aucune", None, "aucune", True, VERSION_REGLES, tuple(avertissements)
    )
