"""ALG-13 : Téléchargement de l'archive (URL, statut HTTP, taille, fraîcheur, empreinte).

Spécification : docs/algorithmes/ALG-13-telechargement.md (statut « Validé », version 3).
Aucun accès réseau ni disque ici : la requête est déléguée à un `Transport`, l'écriture à un
`Stockage` (implémentés dans etl/io/http.py et etl/io/fs.py), l'attente et l'horloge sont injectées.
Un téléchargement douteux ne laisse aucune archive : tout échec supprime le fichier temporaire.
Chaque bloc de code est précédé de « # ALG-13.k : <résumé> ».
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

from ..models import MIO, Parametres, RapportTelechargement, Reponse, Stockage, Transport

_ENTETES_RETENUS = ("etag", "last-modified", "content-length", "content-type", "date")
_REDIRECTIONS = (301, 302, 303, 307, 308)
_SIGNATURE_ZIP = b"PK\x03\x04"
_SHA256 = re.compile(r"[0-9a-f]{64}")

PARAMETRES_SCRUTINS = Parametres()
# profil « référentiels de noms » (ALG-13) : archive AMO30 de 13,7 Mio observés
PARAMETRES_REFERENTIELS = Parametres(max_octets=100 * MIO, min_octets=5 * MIO)


class ErreurReseau(Exception):
    """Panne de transport : connexion refusée ou coupée, délai dépassé, TLS invalide."""

    def __init__(self, nature: str, detail: str = "") -> None:
        super().__init__(f"{nature}: {detail}" if detail else nature)
        self.nature = nature  # connexion | delai | tls | coupure












def url_autorisee(url: str, hotes_autorises: list[str], autoriser_http_local: bool = False) -> bool:
    """ALG-13.1 : https, sans identifiant ni mot de passe, hôte autorisé.

    `autoriser_http_local` (désactivé par défaut) n'admet `http` que pour 127.0.0.1 et localhost :
    réservé aux tests sur un serveur local.
    """
    try:
        u = urlsplit(url)
        hote = u.hostname
        u.port  # noqa: B018 - lève ValueError si le port est invalide
    except ValueError:
        return False
    if u.username is not None or u.password is not None or not hote:
        return False
    if u.scheme == "https" or u.scheme == "http" and autoriser_http_local and hote in ("127.0.0.1", "localhost"):
        pass
    else:
        return False
    return hote.lower() in {h.lower() for h in hotes_autorises}


def _entetes_retenus(reponse: Reponse) -> dict[str, str]:
    return {k: reponse.entetes[k] for k in _ENTETES_RETENUS if k in reponse.entetes}


def _attente(reponse: Reponse | None, tentative: int, p: Parametres) -> float:
    # ALG-13.5 : Retry-After respecté (borné), sinon attentes fixes
    if reponse is not None:
        brut = reponse.entetes.get("retry-after", "")
        if brut.isdigit():
            return min(float(brut), p.retry_after_max)
    return p.attentes[min(tentative - 1, len(p.attentes) - 1)]


@dataclass
class _Resultat:
    reponse: Reponse | None = None
    url_finale: str = ""
    code: int | None = None
    tentatives: int = 0
    cause: str | None = None


def _obtenir(
    transport: Transport,
    url: str,
    hotes: list[str],
    p: Parametres,
    attendre: Callable[[float], None],
    horloge: Callable[[], float],
    debut: float,
    http_local: bool,
) -> _Resultat:
    """ALG-13.3 à 5 : GET avec redirections contrôlées et nouvelles tentatives.

    Renvoie une réponse 200 ouverte (à fermer par l'appelant) ou une cause d'échec.
    """
    res = _Resultat(url_finale=url)
    for tentative in range(1, p.max_tentatives + 1):
        res.tentatives = tentative
        if horloge() - debut > p.delai_total:
            res.cause = "delai_total"
            return res
        courante = url
        redirections = 0
        reponse: Reponse | None = None
        transitoire = False
        while True:
            try:
                reponse = transport.get(courante, p)
            except ErreurReseau:
                transitoire = True  # connexion coupée ou délai dépassé : nouvelle tentative
                reponse = None
                break
            res.code = reponse.code
            if reponse.code in _REDIRECTIONS and "location" in reponse.entetes:
                # ALG-13.4 : chaque redirection reste en https et sur un hôte autorisé
                redirections += 1
                cible = urljoin(courante, reponse.entetes["location"])
                reponse.fermer()
                if redirections > p.max_redirections or not url_autorisee(cible, hotes, http_local):
                    res.cause = "redirection_refusee"
                    res.url_finale = cible
                    return res
                courante = cible
                continue
            break
        res.url_finale = courante
        if not transitoire and reponse is not None and reponse.code == 200:
            res.reponse = reponse
            return res
        retentable = transitoire or (
            reponse is not None and (reponse.code == 429 or 500 <= reponse.code <= 599)
        )
        if not retentable:
            # 404, 4xx, 3xx non géré : pas d'insistance
            if reponse is not None:
                reponse.fermer()
            res.cause = "http_erreur"
            return res
        if tentative == p.max_tentatives:
            if reponse is not None:
                reponse.fermer()
            res.cause = "indisponible"
            return res
        duree = _attente(reponse, tentative, p)
        if reponse is not None:
            reponse.fermer()
        attendre(duree)
    res.cause = "indisponible"
    return res


def _lire_empreinte_publiee(
    transport: Transport,
    url_meta: str,
    hotes: list[str],
    p: Parametres,
    attendre: Callable[[float], None],
    horloge: Callable[[], float],
    debut: float,
    http_local: bool,
) -> tuple[str | None, bool]:
    """ALG-13.2 : (empreinte publiée ou None, ok). Un 404 vaut « aucune publication »."""
    res = _obtenir(transport, url_meta, hotes, p, attendre, horloge, debut, http_local)
    if res.reponse is None:
        # 404 = première publication ; toute autre erreur n'est jamais une première publication
        return None, res.code == 404 and res.cause == "http_erreur"
    try:
        octets = b"".join(res.reponse.lire_blocs(p.taille_bloc))
    except ErreurReseau:
        return None, False
    finally:
        res.reponse.fermer()
    try:
        empreinte = json.loads(octets.decode("utf-8")).get("archive_sha256")
    except (ValueError, AttributeError):
        return None, False
    if not (isinstance(empreinte, str) and _SHA256.fullmatch(empreinte)):
        return None, False
    return empreinte, True


def _age_en_jours(last_modified: str, telechargee_le: str) -> float | None:
    try:
        modifie = parsedate_to_datetime(last_modified)
        reference = datetime.fromisoformat(telechargee_le)
    except (TypeError, ValueError):
        return None
    if modifie.tzinfo is None:
        modifie = modifie.replace(tzinfo=UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    return (reference - modifie).total_seconds() / 86400


def telecharger(
    transport: Transport,
    stockage: Stockage,
    url: str,
    hotes_autorises: list[str],
    url_meta_publie: str | None,
    telechargee_le: str,
    attendre: Callable[[float], None],
    horloge: Callable[[], float],
    params: Parametres = PARAMETRES_SCRUTINS,
    autoriser_http_local: bool = False,
) -> RapportTelechargement:
    """Télécharge l'archive, la vérifie et dit si elle diffère de la version publiée.

    `url_meta_publie` : adresse du `meta.json` de la version publiée ; `None` = pas de comparaison
    (usage local) : `empreinte_publiee` vaut alors `None`.
    """
    rapport = RapportTelechargement(url_demandee=url, url_finale=url)
    debut = horloge()

    def echec(cause: str) -> RapportTelechargement:
        # ALG-13.14 : aucun fichier partiel, une cause explicite
        rapport.statut = "echec"
        rapport.cause_echec = cause
        return rapport

    # ALG-13.1 : configuration (https, pas d'identifiant, hôte autorisé)
    if not url_autorisee(url, hotes_autorises, autoriser_http_local):
        return echec("config_invalide")
    if url_meta_publie is not None and not url_autorisee(
        url_meta_publie, hotes_autorises, autoriser_http_local
    ):
        return echec("config_invalide")

    # ALG-13.2 : empreinte de la version publiée (404 = aucune publication)
    empreinte_publiee: str | None = None
    if url_meta_publie is not None:
        empreinte_publiee, ok = _lire_empreinte_publiee(
            transport, url_meta_publie, hotes_autorises, params, attendre, horloge, debut,
            autoriser_http_local,
        )  # fmt: skip
        if not ok:
            return echec("publie_inconnu")

    # ALG-13.3 à 5 : requête, redirections, nouvelles tentatives
    res = _obtenir(
        transport, url, hotes_autorises, params, attendre, horloge, debut, autoriser_http_local
    )
    rapport.tentatives = res.tentatives
    rapport.url_finale = res.url_finale
    rapport.code_http = res.code
    if res.reponse is None:
        return echec(res.cause or "indisponible")

    reponse = res.reponse
    rapport.entetes = _entetes_retenus(reponse)
    temp = stockage.ouvrir_temporaire()
    h = hashlib.sha256()
    octets = 0
    debut_flux = b""
    try:
        # ALG-13.6 : flux par blocs, empreinte au fil de l'eau, borne sur ce qui est reçu
        try:
            for bloc in reponse.lire_blocs(params.taille_bloc):
                octets += len(bloc)
                if octets > params.max_octets:
                    stockage.abandonner(temp)
                    return echec("trop_gros")
                if len(debut_flux) < 4:
                    debut_flux = (debut_flux + bloc)[:4]
                h.update(bloc)
                temp.ecrire(bloc)
                if horloge() - debut > params.delai_total:
                    stockage.abandonner(temp)
                    return echec("delai_total")
        except ErreurReseau:
            # coupure à mi-flux : pas de nouvelle tentative, aucun fichier conservé
            stockage.abandonner(temp)
            return echec("incomplet")
        except OSError:
            stockage.abandonner(temp)
            return echec("stockage")
    finally:
        reponse.fermer()
    rapport.octets = octets

    # ALG-13.7 : Content-Length présent et différent du nombre d'octets reçus
    declare = rapport.entetes.get("content-length", "")
    if declare.isdigit() and int(declare) != octets:
        stockage.abandonner(temp)
        return echec("incomplet")
    # ALG-13.8 : une page d'erreur servie en 200 ou une archive tronquée
    if octets < params.min_octets:
        stockage.abandonner(temp)
        return echec("trop_petit")
    # ALG-13.9 : format minimal (signature d'un ZIP)
    if debut_flux != _SIGNATURE_ZIP:
        stockage.abandonner(temp)
        return echec("pas_un_zip")
    # ALG-13.10 : fraîcheur annoncée par la source (avertissement seulement)
    last_modified = rapport.entetes.get("last-modified")
    if last_modified is None:
        rapport.avertissements.append("fraicheur_inconnue")
    else:
        age = _age_en_jours(last_modified, telechargee_le)
        if age is None:
            rapport.avertissements.append("fraicheur_inconnue")
        elif age > params.fraicheur_jours:
            rapport.avertissements.append("archive_ancienne")

    # ALG-13.11 : archive adressée par son contenu (jamais d'écrasement)
    rapport.sha256 = h.hexdigest()
    try:
        rapport.chemin, cree = stockage.conserver(temp, rapport.sha256)
    except OSError:
        stockage.abandonner(temp)
        return echec("stockage")

    # ALG-13.12 : comparaison avec la version PUBLIÉE (jamais avec le dernier import)
    rapport.statut = "inchangee" if empreinte_publiee == rapport.sha256 else "nouvelle"

    # ALG-13.13 : provenance (l'URL finale sert de source_url, ALG-04)
    try:
        stockage.ecrire_provenance(
            {
                "url_demandee": rapport.url_demandee,
                "url_finale": rapport.url_finale,
                "code_http": rapport.code_http,
                "entetes": rapport.entetes,
                "sha256": rapport.sha256,
                "octets": rapport.octets,
                "telechargee_le": telechargee_le,
                "tentatives": rapport.tentatives,
            }
        )
    except OSError:
        # aucune archive ne reste après un échec : on retire celle que cet appel vient de créer
        if cree:
            stockage.retirer(rapport.chemin)
        rapport.chemin = ""
        return echec("stockage")
    return rapport
