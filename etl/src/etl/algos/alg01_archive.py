"""ALG-01 : Lecture sécurisée de l'archive (ZIP/dossier, taille, chemins, empreinte).

Spécification : docs/algorithmes/ALG-01-lecture-archive.md (statut « Validé », version 2).
Aucun accès disque ni réseau ici : l'ouverture et la lecture des octets sont déléguées à une
source (`SourceArchive`, implémentée dans etl/io/zipfile.py et etl/io/dossier.py).
Chaque bloc de code est précédé de « # ALG-01.k : <résumé> ».
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from ..models import EntreeAcceptee, EntreeRefusee, RapportLecture

# CHOIX: limites regroupées dans un objet immuable plutôt que des constantes de module
# RAISON: les tests peuvent les réduire (archives de quelques octets) sans bricoler le module


@dataclass(frozen=True)
class LimitesLecture:
    """Paramètres de la fiche ALG-01 (valeurs validées)."""

    max_entrees: int = 50_000
    max_octets_entree: int = 5 * 1024 * 1024
    max_octets_total: int = 1024 * 1024 * 1024
    max_ratio: int = 100
    max_trous_detailles: int = 1000


LIMITES_PAR_DEFAUT = LimitesLecture()


class ErreurSource(Exception):
    """Source inexploitable (échec de l'archive entière) ; `motif` va dans le rapport."""

    def __init__(self, motif: str, detail: str = "") -> None:
        super().__init__(f"{motif}: {detail}" if detail else motif)
        self.motif = motif


class ErreurLecture(Exception):
    """Lecture d'une entrée impossible (CRC invalide, flux corrompu)."""


@dataclass(frozen=True)
class EntreeBrute:
    """Métadonnées d'une entrée telle que la source la décrit, avant tout contrôle."""

    nom: str
    est_dossier: bool
    chiffree: bool
    methode_supportee: bool
    lien_symbolique: bool
    taille_declaree: int
    taille_compressee: int


class SourceArchive(Protocol):
    """Contrat d'une source (ZIP ou dossier) ; implémentée dans etl/io/."""

    type_source: str
    type_empreinte: str

    def empreinte_fichier(self) -> str | None: ...
    def lister(self, plafond: int | None = None) -> list[EntreeBrute]: ...
    def lire(self, nom: str, plafond: int) -> bytes: ...
    def fermer(self) -> None: ...


_NOM_SCRUTIN = re.compile(r"json/VTANR5L(?P<leg>[1-9][0-9]*)V(?P<num>[1-9][0-9]{0,8})\.json")
_FORME_SCRUTIN = re.compile(r"VTANR5L[0-9]+V[0-9]+\.json")
_LECTEUR = re.compile(r"[A-Za-z]:")


def _nom_dangereux(nom: str) -> bool:
    """ALG-01.10 : chemin pouvant sortir de la racine (zip-slip, chemins Windows)."""
    return (
        "\\" in nom
        or any(ord(c) < 32 or ord(c) == 127 for c in nom)
        or nom.startswith("/")
        or ".." in nom.split("/")
        or _LECTEUR.match(nom) is not None
    )


def _refuser_cles_dupliquees(paires: list[tuple[str, Any]]) -> dict[str, Any]:
    """ALG-01.17 : une clé dupliquée écraserait silencieusement une valeur."""
    resultat: dict[str, Any] = {}
    for cle, valeur in paires:
        if cle in resultat:
            raise ValueError(f"clé dupliquée : {cle}")
        resultat[cle] = valeur
    return resultat


def _refuser_constante(valeur: str) -> Any:
    raise ValueError(f"constante non JSON : {valeur}")


def _verifier_et_parser(octets: bytes, nom: str, legislature: int) -> tuple[Any, str | None]:
    """Étapes 16 à 19 : renvoie (document, None) ou (None, motif de refus)."""
    # ALG-01.16 : UTF-8 strict, BOM refusé
    if octets.startswith(b"\xef\xbb\xbf"):
        return None, "encodage"
    try:
        texte = octets.decode("utf-8")
    except UnicodeDecodeError:
        return None, "encodage"
    # ALG-01.17 : JSON sans clé dupliquée, NaN, Infinity ni dépassement de profondeur
    try:
        doc = json.loads(
            texte,
            object_pairs_hook=_refuser_cles_dupliquees,
            parse_constant=_refuser_constante,
        )
    except (ValueError, RecursionError):
        return None, "json_invalide"
    # ALG-01.18 : racine exactement {"scrutin": {...}}
    if not (isinstance(doc, dict) and set(doc) == {"scrutin"} and isinstance(doc["scrutin"], dict)):
        return None, "structure"
    # ALG-01.19 : identité nom de fichier / contenu
    scrutin = doc["scrutin"]
    sans_extension = nom.rsplit("/", 1)[-1].removesuffix(".json")
    if scrutin.get("uid") != sans_extension or scrutin.get("legislature") != str(legislature):
        return None, "identite"
    return doc, None


def lire_archive(
    source: SourceArchive,
    legislature: int = 17,
    limites: LimitesLecture = LIMITES_PAR_DEFAUT,
) -> tuple[list[EntreeAcceptee], RapportLecture]:
    """Lit une archive de scrutins et renvoie (entrées acceptées triées, rapport).

    Les échecs systémiques (source illisible, trop d'entrées, nom en double, dépassement du
    total) renvoient une liste vide et un rapport `echec` avec son `motif_echec`.
    """
    rapport = RapportLecture(type_source=source.type_source, type_empreinte=source.type_empreinte)
    acceptees: list[EntreeAcceptee] = []
    # Hachages des entrées dont le contenu a pu être lu (pour le manifeste, ALG-01.22)
    hachages: dict[str, str] = {}
    # Refus d'entrées au motif admis (ALG-01.23) : seuls les refus des étapes 12 à 19 comptent
    refus_bloquants = 0

    # ALG-01.2 à 3 : empreinte du fichier ZIP (calculée à l'ouverture de la source)
    empreinte = source.empreinte_fichier()
    if empreinte is not None:
        rapport.empreinte_archive = empreinte

    # ALG-01.5 : borne du nombre d'entrées (ZIP et dossier ; le parcours d'un dossier s'arrête
    # dès que la borne est dépassée)
    entrees = source.lister(limites.max_entrees)
    if len(entrees) > limites.max_entrees:
        rapport.motif_echec = "trop_d_entrees"
        return [], rapport

    # ALG-01.6 : nom en double (ZIP) -> échec
    if source.type_source == "zip":
        noms = [e.nom for e in entrees]
        if len(set(noms)) != len(noms):
            rapport.motif_echec = "nom_en_double"
            return [], rapport

    # ALG-01.7 : somme des tailles déclarées (ZIP)
    if sum(e.taille_declaree for e in entrees) > limites.max_octets_total:
        rapport.motif_echec = "taille_declaree_excessive"
        return [], rapport

    # ALG-01.9 : examen dans l'ordre alphabétique des noms
    for entree in sorted(entrees, key=lambda e: e.nom):
        nom = entree.nom
        motif_nom = _NOM_SCRUTIN.fullmatch(nom)

        # ALG-01.8 : lien symbolique d'un dossier : refusé s'il a la forme d'un scrutin,
        # sinon ignoré avec compteur (hors entrees_vues)
        if source.type_source == "dossier" and entree.lien_symbolique:
            if motif_nom:
                rapport.entrees_vues += 1
                rapport.refusees.append(EntreeRefusee(nom, "lien_symbolique"))
                refus_bloquants += 1
            else:
                rapport.liens_symboliques_ignores += 1
            continue

        rapport.entrees_vues += 1

        # ALG-01.9 : entrée de dossier -> ignorée
        if entree.est_dossier:
            rapport.ignorees += 1
            continue

        # ALG-01.10 : nom dangereux, vérifié avant le motif
        if _nom_dangereux(nom):
            rapport.refusees.append(EntreeRefusee(nom, "nom_dangereux"))
            if _FORME_SCRUTIN.fullmatch(nom.replace("\\", "/").rsplit("/", 1)[-1]):
                refus_bloquants += 1  # CHOIX: « ressemble à un scrutin » = nom de fichier VTANR5L…
            else:
                rapport.avertissements.append(f"entrée refusée (nom dangereux) : {nom!r}")
            continue

        # ALG-01.11 : liste blanche du motif de nom, puis législature attendue
        if motif_nom is None:
            rapport.refusees.append(EntreeRefusee(nom, "hors_motif"))
            rapport.avertissements.append(f"entrée hors motif : {nom}")
            continue
        if motif_nom.group("leg") != str(legislature):
            rapport.refusees.append(EntreeRefusee(nom, "legislature_inattendue"))
            rapport.avertissements.append(f"législature inattendue : {nom}")
            continue
        numero = int(motif_nom.group("num"))

        # ALG-01.12 : entrée chiffrée, méthode inconnue ou lien symbolique (ZIP)
        if entree.chiffree or not entree.methode_supportee or entree.lien_symbolique:
            rapport.refusees.append(EntreeRefusee(nom, "nom_non_supporte"))
            refus_bloquants += 1
            continue

        # ALG-01.13 : lecture plafonnée à MAX_OCTETS_ENTREE + 1 et à la taille déclarée + 1
        plafond = min(limites.max_octets_entree, entree.taille_declaree) + 1
        try:
            octets = source.lire(nom, plafond)
        except ErreurLecture:
            # ALG-01.14 : CRC invalide ou flux corrompu -> entrée refusée, on continue
            rapport.refusees.append(EntreeRefusee(nom, "corrompue"))
            refus_bloquants += 1
            continue
        hachage = hashlib.sha256(octets).hexdigest()
        hachages[nom] = hachage
        ratio_excessif = (
            len(octets) > 0
            and (
                entree.taille_compressee == 0
                or len(octets) / entree.taille_compressee > limites.max_ratio
            )
        )
        if (
            len(octets) > limites.max_octets_entree
            or len(octets) != entree.taille_declaree
            or ratio_excessif
        ):
            rapport.refusees.append(EntreeRefusee(nom, "taille"))
            refus_bloquants += 1
            continue

        # ALG-01.15 : cumul des octets réellement lus
        rapport.octets_lus += len(octets)
        if rapport.octets_lus > limites.max_octets_total:
            rapport.motif_echec = "octets_totaux_excessifs"
            rapport.statut = "echec"
            return [], rapport

        # ALG-01.16 à 19 : décodage, JSON, structure, identité
        document, motif_refus = _verifier_et_parser(octets, nom, legislature)
        if motif_refus is not None:
            rapport.refusees.append(EntreeRefusee(nom, motif_refus))
            refus_bloquants += 1
            continue

        # ALG-01.20 : entrée acceptée avec son empreinte
        acceptees.append(EntreeAcceptee(nom, numero, hachage, len(octets), document))

    # ALG-01.21 : tri par numéro croissant, bornes et trous de numérotation (compte exact,
    # détail plafonné)
    acceptees.sort(key=lambda a: a.numero)
    rapport.acceptees = len(acceptees)
    if acceptees:
        rapport.numero_min = acceptees[0].numero
        rapport.numero_max = acceptees[-1].numero
        presents = {a.numero for a in acceptees}
        # CHOIX: les trous sont comptés par écarts entre numéros consécutifs, sans énumérer
        # l'intervalle ; seuls les `max_trous_detailles` premiers sont détaillés
        # RAISON: deux scrutins numérotés 1 et 10⁹ ne doivent pas construire 10⁹ entiers
        numeros = sorted(presents)
        for avant, apres in zip(numeros, numeros[1:], strict=False):
            ecart = apres - avant - 1
            if ecart <= 0:
                continue
            rapport.nb_trous += ecart
            restant = limites.max_trous_detailles - len(rapport.trous)
            if restant > 0:
                rapport.trous.extend(range(avant + 1, avant + 1 + min(ecart, restant)))

    # ALG-01.22 : empreinte d'un dossier = SHA-256 du manifeste trié
    if source.type_source == "dossier":
        manifeste = "".join(f"{nom}\t{h}\n" for nom, h in sorted(hachages.items()))
        rapport.empreinte_archive = hashlib.sha256(manifeste.encode("utf-8")).hexdigest()

    # ALG-01.23 : statut
    if not acceptees:
        rapport.statut = "echec"
        rapport.motif_echec = rapport.motif_echec or "aucune_entree_acceptee"
    elif refus_bloquants:
        rapport.statut = "partiel"
    else:
        rapport.statut = "complet"

    # ALG-01.24 : numérotation discontinue = avertissement, sans changer le statut
    if rapport.nb_trous or (rapport.numero_min is not None and rapport.numero_min != 1):
        rapport.avertissements.append("numérotation discontinue")

    # ALG-01.25 : retour du flux trié et du rapport (journalisé en entier par l'appelant)
    return acceptees, rapport
