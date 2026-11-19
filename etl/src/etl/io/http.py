"""Accès HTTP (utilisé par le pipeline pour ALG-13) : bibliothèque standard seulement.

Une requête GET, sans cookie ni jeton, certificat TLS vérifié, sans compression
(`Accept-Encoding: identity` : les octets reçus sont les octets hachés), sans suivre les
redirections (c'est ALG-13 qui les contrôle une à une).
"""

import http.client
import json
import ssl
from collections.abc import Iterator
from urllib.parse import urlsplit

from ..algos.alg13_telechargement import ErreurReseau
from ..models import Parametres, Transport


class ReponseHttp:
    """Réponse ouverte : `lire_blocs` lit le corps par blocs, `fermer` libère la connexion."""

    def __init__(self, conn: http.client.HTTPConnection, reponse: http.client.HTTPResponse):
        self._conn = conn
        self._reponse = reponse
        self.code = reponse.status
        self.entetes = {k.lower(): v for k, v in reponse.getheaders()}

    def lire_blocs(self, taille: int) -> Iterator[bytes]:
        while True:
            try:
                bloc = self._reponse.read(taille)
            except TimeoutError as exc:
                raise ErreurReseau("delai", "inactivité") from exc
            except (http.client.HTTPException, OSError) as exc:
                raise ErreurReseau("coupure", str(exc)) from exc
            if not bloc:
                return
            yield bloc

    def fermer(self) -> None:
        try:
            self._reponse.close()
        finally:
            self._conn.close()


class TransportHttp:
    """Implémente `Transport` (ALG-13) avec http.client."""

    def get(self, url: str, params: Parametres) -> ReponseHttp:
        u = urlsplit(url)
        chemin = (u.path or "/") + (f"?{u.query}" if u.query else "")
        # délai de connexion d'abord ; le délai d'inactivité s'applique ensuite à chaque lecture
        if u.scheme == "https":
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                u.hostname, u.port, timeout=params.delai_connexion,
                context=ssl.create_default_context(),  # vérification activée, jamais désactivée
            )  # fmt: skip
        else:
            conn = http.client.HTTPConnection(u.hostname, u.port, timeout=params.delai_connexion)
        try:
            conn.connect()
            conn.sock.settimeout(params.delai_inactivite)
            conn.request(
                "GET",
                chemin,
                headers={"User-Agent": params.user_agent, "Accept-Encoding": "identity"},
            )
            reponse = conn.getresponse()
        except TimeoutError as exc:
            conn.close()
            raise ErreurReseau("delai", str(exc)) from exc
        except ssl.SSLError as exc:
            conn.close()
            raise ErreurReseau("tls", str(exc)) from exc
        except (http.client.HTTPException, OSError) as exc:
            conn.close()
            raise ErreurReseau("connexion", str(exc)) from exc
        return ReponseHttp(conn, reponse)


MAX_OCTETS_JSON_PUBLIE = 25 * 1024 * 1024  # limite de l'hébergement : aucun fichier publié ne la dépasse


def lire_json_publie(transport: Transport, url: str, params: Parametres) -> dict | None:
    """Lit un fichier JSON de la version publiée ; `None` si l'adresse répond 404.

    Une première publication n'a aucun fichier : le 404 n'est pas une erreur. Toute autre anomalie
    (code, coupure, contenu qui n'est pas un objet JSON) lève `ErreurReseau` : on ne devine jamais
    qu'il n'y a « rien de publié ». Aucune redirection n'est suivie.
    """
    reponse = transport.get(url, params)
    try:
        if reponse.code == 404:
            return None
        if reponse.code != 200:
            raise ErreurReseau("http_erreur", f"{url} : code {reponse.code}")
        octets = b""
        for bloc in reponse.lire_blocs(params.taille_bloc):
            octets += bloc
            if len(octets) > MAX_OCTETS_JSON_PUBLIE:
                raise ErreurReseau("trop_gros", url)
    finally:
        reponse.fermer()
    try:
        contenu = json.loads(octets.decode("utf-8"))
    except ValueError as exc:
        raise ErreurReseau("contenu", f"{url} : JSON illisible") from exc
    if not isinstance(contenu, dict):
        raise ErreurReseau("contenu", f"{url} : un objet JSON est attendu")
    return contenu
