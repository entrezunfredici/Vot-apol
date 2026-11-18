"""Accès HTTP (utilisé par le pipeline pour ALG-13) : bibliothèque standard seulement.

Une requête GET, sans cookie ni jeton, certificat TLS vérifié, sans compression
(`Accept-Encoding: identity` : les octets reçus sont les octets hachés), sans suivre les
redirections (c'est ALG-13 qui les contrôle une à une).
"""

import http.client
import socket
import ssl
from collections.abc import Iterator
from urllib.parse import urlsplit

from ..algos.alg13_telechargement import ErreurReseau
from ..models import Parametres


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
            except socket.timeout as exc:
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
        except socket.timeout as exc:
            conn.close()
            raise ErreurReseau("delai", str(exc)) from exc
        except ssl.SSLError as exc:
            conn.close()
            raise ErreurReseau("tls", str(exc)) from exc
        except (http.client.HTTPException, OSError) as exc:
            conn.close()
            raise ErreurReseau("connexion", str(exc)) from exc
        return ReponseHttp(conn, reponse)
