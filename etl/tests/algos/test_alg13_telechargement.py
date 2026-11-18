"""Tests ALG-13 : serveur HTTP local (aucun accès au réseau public), un test par cas de la fiche."""

import hashlib
import io
import json
import threading
import time
import zipfile
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from etl.algos.alg13_telechargement import (
    PARAMETRES_REFERENTIELS,
    PARAMETRES_SCRUTINS,
    ErreurReseau,
    Parametres,
    telecharger,
    url_autorisee,
)
from etl.io.fs import StockageFichiers
from etl.io.http import TransportHttp

HOTE = "127.0.0.1"
MAINTENANT = "2026-11-18T10:00:00Z"
RECENT = "Tue, 17 Nov 2026 08:00:00 GMT"
ANCIEN = "Mon, 01 Jan 2024 08:00:00 GMT"


def _zip(contenu: bytes = b"scrutin") -> bytes:
    flux = io.BytesIO()
    with zipfile.ZipFile(flux, "w", zipfile.ZIP_STORED) as z:
        z.writestr("json/VTANR5L17V1.json", contenu * 40)
    return flux.getvalue()


@dataclass
class Rep:
    """Une réponse programmée du serveur de test."""

    code: int = 200
    corps: bytes = b""
    entetes: dict[str, str] = field(default_factory=dict)
    envoyer: int | None = None  # n'envoie que ce nombre d'octets, puis coupe la connexion
    attente: float = 0.0  # attend avant de répondre (réponse lente)
    longueur: int | None = None  # Content-Length annoncé (par défaut la taille du corps)


class _Serveur:
    def __init__(self):
        self.routes: dict[str, list[Rep]] = {}
        self.requetes: list[tuple[str, dict[str, str]]] = []
        serveur = self

        class Gestionnaire(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # silencieux
                pass

            def do_GET(self):
                serveur.requetes.append((self.path, {k.lower(): v for k, v in self.headers.items()}))
                reponses = serveur.routes.get(self.path)
                if not reponses:
                    rep = Rep(404, b"introuvable")
                else:
                    rep = reponses.pop(0) if len(reponses) > 1 else reponses[0]
                if rep.attente:
                    time.sleep(rep.attente)
                try:
                    self.send_response(rep.code)
                    for k, v in rep.entetes.items():
                        self.send_header(k, v)
                    longueur = rep.longueur if rep.longueur is not None else len(rep.corps)
                    self.send_header("Content-Length", str(longueur))
                    self.end_headers()
                    corps = rep.corps if rep.envoyer is None else rep.corps[: rep.envoyer]
                    self.wfile.write(corps)
                    self.wfile.flush()
                except OSError:
                    pass
                if rep.envoyer is not None:
                    self.close_connection = True

        class _Httpd(ThreadingHTTPServer):
            def handle_error(self, request, client_address):  # client parti : sans importance
                pass

        self._httpd = _Httpd((HOTE, 0), Gestionnaire)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def url(self, chemin: str) -> str:
        return f"http://{HOTE}:{self.port}{chemin}"

    def arreter(self):
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture
def serveur():
    s = _Serveur()
    yield s
    s.arreter()


P = Parametres(
    min_octets=100,
    max_octets=1_000_000,
    delai_connexion=2.0,
    delai_inactivite=0.4,
    delai_total=30.0,
    attentes=(0.0, 0.0),
    taille_bloc=4096,
)


def _telecharger(serveur, tmp_path, chemin="/archive.zip", meta="/meta.json", params=P, **kw):
    pauses: list[float] = []
    stockage = StockageFichiers(tmp_path / "archives")
    rapport = telecharger(
        TransportHttp(), stockage, serveur.url(chemin), [HOTE],
        serveur.url(meta) if meta else None, kw.pop("maintenant", MAINTENANT),
        attendre=pauses.append, horloge=time.monotonic, params=params,
        autoriser_http_local=kw.pop("http_local", True), **kw,
    )  # fmt: skip
    rapport.pauses = pauses  # type: ignore[attr-defined]
    return rapport, tmp_path / "archives"


def _fichiers(repertoire):
    return sorted(p.name for p in repertoire.iterdir())


def _meta(sha: str | None) -> Rep:
    return Rep(200, json.dumps({"archive_sha256": sha}).encode()) if sha else Rep(404)


def _archive(contenu=b"scrutin", **entetes):
    return Rep(200, _zip(contenu), {"Last-Modified": RECENT, "Content-Type": "application/zip", **entetes})


# --- cas nominaux ---------------------------------------------------------------------------------


def test_ALG_13_telechargement_correct_nouvelle(serveur, tmp_path):
    zip_ = _zip()
    serveur.routes = {"/archive.zip": [_archive()], "/meta.json": [_meta(None)]}
    r, rep = _telecharger(serveur, tmp_path)
    sha = hashlib.sha256(zip_).hexdigest()
    assert (r.statut, r.code_http, r.tentatives, r.cause_echec) == ("nouvelle", 200, 1, None)
    assert (r.sha256, r.octets) == (sha, len(zip_)) and r.avertissements == []
    assert _fichiers(rep) == [f"{sha}.zip", "provenance.json"]
    assert (rep / f"{sha}.zip").read_bytes() == zip_  # l'empreinte est celle des octets conservés
    prov = json.loads((rep / "provenance.json").read_text(encoding="utf-8"))
    assert prov["sha256"] == sha and prov["url_finale"] == serveur.url("/archive.zip")
    assert prov["telechargee_le"] == MAINTENANT and prov["tentatives"] == 1
    assert "last-modified" in prov["entetes"] and prov["code_http"] == 200


def test_ALG_13_meme_archive_que_la_publiee_inchangee_fichier_conserve(serveur, tmp_path):
    sha = hashlib.sha256(_zip()).hexdigest()
    serveur.routes = {"/archive.zip": [_archive()], "/meta.json": [_meta(sha)]}
    r, rep = _telecharger(serveur, tmp_path)
    assert r.statut == "inchangee" and (rep / f"{sha}.zip").exists()


def test_ALG_13_archive_differente_de_la_publiee_nouvelle(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive()], "/meta.json": [_meta("0" * 64)]}
    r, _ = _telecharger(serveur, tmp_path)
    assert r.statut == "nouvelle"


def test_ALG_13_deux_telechargements_identiques_un_seul_fichier(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive()], "/meta.json": [_meta(None)]}
    _telecharger(serveur, tmp_path)
    r, rep = _telecharger(serveur, tmp_path)
    assert r.statut == "nouvelle"
    assert len([f for f in _fichiers(rep) if f.endswith(".zip")]) == 1
    assert not [f for f in _fichiers(rep) if f.endswith(".tmp")]


def test_ALG_13_deux_archives_differentes_deux_fichiers(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive(b"a")], "/meta.json": [_meta(None)]}
    _telecharger(serveur, tmp_path)
    serveur.routes["/archive.zip"] = [_archive(b"b")]
    _telecharger(serveur, tmp_path)
    assert len([f for f in _fichiers(tmp_path / "archives") if f.endswith(".zip")]) == 2


def test_ALG_13_requete_sans_cookie_ni_jeton_ni_compression(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive()], "/meta.json": [_meta(None)]}
    _telecharger(serveur, tmp_path)
    entetes = serveur.requetes[-1][1]
    assert entetes["accept-encoding"] == "identity" and "voteapol" in entetes["user-agent"]
    assert not {"cookie", "authorization", "proxy-authorization"} & entetes.keys()


# --- version publiée (meta.json) -------------------------------------------------------------------


def test_ALG_13_publie_404_premiere_publication(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive()]}  # /meta.json absent -> 404
    r, _ = _telecharger(serveur, tmp_path)
    assert r.statut == "nouvelle"


@pytest.mark.parametrize("meta", [Rep(500), Rep(200, b"pas du json"), Rep(200, b'{"autre": 1}'),
                                  Rep(200, b'{"archive_sha256": "xyz"}')])  # fmt: skip
def test_ALG_13_publie_inconnu_echec(serveur, tmp_path, meta):
    serveur.routes = {"/archive.zip": [_archive()], "/meta.json": [meta]}
    r, rep = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec) == ("echec", "publie_inconnu")
    assert _fichiers(rep) == []
    assert not any(c == "/archive.zip" for c, _ in serveur.requetes)  # pas de téléchargement


def test_ALG_13_sans_url_meta_pas_de_comparaison(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive()]}
    r, _ = _telecharger(serveur, tmp_path, meta=None)
    assert r.statut == "nouvelle" and not any(c == "/meta.json" for c, _ in serveur.requetes)


# --- codes HTTP et tentatives ----------------------------------------------------------------------


def test_ALG_13_404_sur_l_archive_sans_nouvelle_tentative(serveur, tmp_path):
    serveur.routes = {"/meta.json": [_meta(None)]}
    r, rep = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec, r.code_http, r.tentatives) == ("echec", "http_erreur", 404, 1)
    assert _fichiers(rep) == []


def test_ALG_13_503_puis_200_nouvelle_deux_tentatives(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(503), _archive()], "/meta.json": [_meta(None)]}
    r, _ = _telecharger(serveur, tmp_path)
    assert (r.statut, r.tentatives) == ("nouvelle", 2) and len(r.pauses) == 1


def test_ALG_13_trois_503_echec_apres_trois_tentatives(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(503)], "/meta.json": [_meta(None)]}
    r, rep = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec, r.tentatives) == ("echec", "indisponible", 3)
    assert _fichiers(rep) == []


def test_ALG_13_retry_after_respecte_et_borne(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(429, entetes={"Retry-After": "7"}), _archive()],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    r, _ = _telecharger(serveur, tmp_path)
    assert r.pauses == [7.0]
    serveur.routes = {"/archive.zip": [Rep(503, entetes={"Retry-After": "99999"}), _archive(b"z")],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    r, _ = _telecharger(serveur, tmp_path)
    assert r.pauses == [120.0]


def test_ALG_13_attentes_par_defaut_10_puis_60(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(503), Rep(503), _archive()], "/meta.json": [_meta(None)]}
    avec_attentes = Parametres(min_octets=100, taille_bloc=4096, attentes=(10.0, 60.0))
    r, _ = _telecharger(serveur, tmp_path, params=avec_attentes)
    assert r.pauses == [10.0, 60.0] and r.tentatives == 3


def test_ALG_13_reponse_lente_delai_d_inactivite(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(200, _zip(), attente=1.0)], "/meta.json": [_meta(None)]}
    lent = Parametres(min_octets=100, delai_inactivite=0.2, max_tentatives=2, attentes=(0.0,))
    r, rep = _telecharger(serveur, tmp_path, params=lent)
    assert (r.statut, r.cause_echec, r.tentatives) == ("echec", "indisponible", 2)
    assert _fichiers(rep) == []


# --- complétude, taille, format ------------------------------------------------------------------


def test_ALG_13_coupure_a_mi_flux_incomplet_aucun_fichier(serveur, tmp_path):
    zip_ = _zip(b"x" * 20)
    serveur.routes = {
        "/archive.zip": [Rep(200, zip_, longueur=len(zip_) + 5000, envoyer=len(zip_))],
        "/meta.json": [_meta(None)],
    }
    r, rep = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec) == ("echec", "incomplet") and _fichiers(rep) == []


def test_ALG_13_page_html_en_200_trop_petit(serveur, tmp_path):
    page = Rep(200, b"<html>" + b"x" * 5000 + b"</html>")
    serveur.routes = {"/archive.zip": [page], "/meta.json": [_meta(None)]}
    sur_10_ko = Parametres(min_octets=10_000, taille_bloc=4096)
    r, rep = _telecharger(serveur, tmp_path, params=sur_10_ko)
    assert (r.statut, r.cause_echec) == ("echec", "trop_petit") and _fichiers(rep) == []


def test_ALG_13_html_assez_gros_n_est_pas_un_zip(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(200, b"<html>" + b"x" * 20_000)],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    r, rep = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec) == ("echec", "pas_un_zip") and _fichiers(rep) == []


def test_ALG_13_flux_trop_gros_interrompu(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(200, b"PK\x03\x04" + b"x" * 200_000)],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    petit = Parametres(min_octets=100, max_octets=50_000, taille_bloc=4096)
    r, rep = _telecharger(serveur, tmp_path, params=petit)
    assert (r.statut, r.cause_echec) == ("echec", "trop_gros") and _fichiers(rep) == []
    assert r.octets <= 50_000 + 4096  # interrompu dès le dépassement, pas lu en entier


# --- redirections ----------------------------------------------------------------------------------


def test_ALG_13_redirection_meme_hote_suivie(serveur, tmp_path):
    serveur.routes = {
        "/archive.zip": [Rep(301, entetes={"Location": "/ailleurs.zip"})],
        "/ailleurs.zip": [_archive()],
        "/meta.json": [_meta(None)],
    }
    r, _ = _telecharger(serveur, tmp_path)
    assert r.statut == "nouvelle" and r.url_finale == serveur.url("/ailleurs.zip")


def test_ALG_13_redirection_vers_un_autre_hote_refusee(serveur, tmp_path):
    autre = f"http://localhost:{serveur.port}/archive.zip"  # autre nom d'hôte
    serveur.routes = {"/archive.zip": [Rep(302, entetes={"Location": autre})],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    r, rep = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec) == ("echec", "redirection_refusee") and _fichiers(rep) == []


def test_ALG_13_redirection_vers_http_non_local_refusee(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(302, entetes={"Location": "http://exemple.invalid/x"})],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    r, _ = _telecharger(serveur, tmp_path)
    assert r.cause_echec == "redirection_refusee"


def test_ALG_13_boucle_de_redirections_refusee(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [Rep(302, entetes={"Location": "/archive.zip"})],
                      "/meta.json": [_meta(None)]}  # fmt: skip
    r, _ = _telecharger(serveur, tmp_path)
    assert (r.statut, r.cause_echec) == ("echec", "redirection_refusee")


# --- configuration -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url, http_local",
    [
        ("http://127.0.0.1:1/archive.zip", False),  # http sans le paramètre de test
        ("http://exemple.invalid/archive.zip", True),  # http hors interface locale
        ("https://utilisateur:secret@127.0.0.1/archive.zip", True),  # identifiant
        ("https://autre.invalid/archive.zip", True),  # hôte non autorisé
        ("ftp://127.0.0.1/archive.zip", True),
        ("", True),
    ],
)
def test_ALG_13_configuration_invalide_aucune_requete(serveur, tmp_path, url, http_local):
    pauses: list[float] = []
    stockage = StockageFichiers(tmp_path / "a")
    r = telecharger(TransportHttp(), stockage, url, [HOTE], None, MAINTENANT,
                    attendre=pauses.append, horloge=time.monotonic, params=P,
                    autoriser_http_local=http_local)  # fmt: skip
    assert (r.statut, r.cause_echec) == ("echec", "config_invalide")
    assert serveur.requetes == [] and _fichiers(tmp_path / "a") == []


def test_ALG_13_url_meta_invalide_config_invalide(serveur, tmp_path):
    serveur.routes = {"/archive.zip": [_archive()]}
    stockage = StockageFichiers(tmp_path / "a")
    r = telecharger(TransportHttp(), stockage, serveur.url("/archive.zip"), [HOTE],
                    "https://autre.invalid/meta.json", MAINTENANT, attendre=lambda s: None,
                    horloge=time.monotonic, params=P, autoriser_http_local=True)  # fmt: skip
    assert r.cause_echec == "config_invalide" and serveur.requetes == []


def test_ALG_13_url_autorisee_https_par_defaut():
    assert url_autorisee("https://data.assemblee-nationale.fr/x.zip", ["data.assemblee-nationale.fr"])
    assert not url_autorisee("http://data.assemblee-nationale.fr/x.zip", ["data.assemblee-nationale.fr"])
    assert not url_autorisee("https://DATA.assemblee-nationale.fr.evil.fr/x", ["data.assemblee-nationale.fr"])
    assert url_autorisee("https://DATA.assemblee-nationale.fr/x", ["data.assemblee-nationale.fr"])
    assert not url_autorisee("https://data.assemblee-nationale.fr:notaport/x",
                             ["data.assemblee-nationale.fr"])  # fmt: skip


# --- fraîcheur --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entetes, avertissements",
    [
        ({"Last-Modified": RECENT}, []),
        ({"Last-Modified": ANCIEN}, ["archive_ancienne"]),
        ({}, ["fraicheur_inconnue"]),
        ({"Last-Modified": "pas une date"}, ["fraicheur_inconnue"]),
    ],
)
def test_ALG_13_fraicheur_avertissement_seulement(serveur, tmp_path, entetes, avertissements):
    serveur.routes = {"/archive.zip": [Rep(200, _zip(), entetes)], "/meta.json": [_meta(None)]}
    r, _ = _telecharger(serveur, tmp_path)
    assert r.statut == "nouvelle" and r.avertissements == avertissements


# --- erreurs de stockage et de temps (transport et stockage factices) -----------------------------------


class _RepFactice:
    code = 200

    def __init__(self, blocs, entetes=None):
        self._blocs = blocs
        self.entetes = entetes or {"last-modified": RECENT}

    def lire_blocs(self, taille):
        yield from self._blocs

    def fermer(self):
        pass


class _TransportFactice:
    def __init__(self, reponse):
        self._reponse = reponse

    def get(self, url, params):
        return self._reponse


class _StockageFactice:
    def __init__(self, echec_conserver=False, echec_provenance=False):
        self.echec_conserver, self.echec_provenance = echec_conserver, echec_provenance
        self.abandonnes, self.retires, self.ecrits = 0, [], []

    def ouvrir_temporaire(self):
        return self

    def ecrire(self, bloc):
        self.ecrits.append(bloc)

    def abandonner(self, temp):
        self.abandonnes += 1

    def conserver(self, temp, sha256):
        if self.echec_conserver:
            raise OSError("disque plein")
        return f"/archives/{sha256}.zip", True

    def retirer(self, chemin):
        self.retires.append(chemin)

    def ecrire_provenance(self, provenance):
        if self.echec_provenance:
            raise OSError("disque plein")


def _factice(blocs, stockage, horloge=time.monotonic):
    return telecharger(
        _TransportFactice(_RepFactice(blocs)), stockage, "https://h.fr/a.zip", ["h.fr"], None,
        MAINTENANT, attendre=lambda s: None, horloge=horloge, params=Parametres(min_octets=4),
    )  # fmt: skip


def test_ALG_13_echec_du_stockage_aucune_archive():
    s = _StockageFactice(echec_conserver=True)
    r = _factice([b"PK\x03\x04abcd"], s)
    assert (r.statut, r.cause_echec, r.chemin) == ("echec", "stockage", "") and s.abandonnes == 1


def test_ALG_13_echec_de_la_provenance_retire_l_archive_creee():
    s = _StockageFactice(echec_provenance=True)
    r = _factice([b"PK\x03\x04abcd"], s)
    assert (r.statut, r.cause_echec, r.chemin) == ("echec", "stockage", "")
    assert len(s.retires) == 1 and s.retires[0].endswith(".zip")


def test_ALG_13_signature_zip_lue_meme_si_le_premier_bloc_est_court():
    r = _factice([b"PK", b"\x03\x04abcdef"], _StockageFactice())
    assert r.statut == "nouvelle"


def test_ALG_13_delai_total_depasse():
    temps = iter([0.0, 0.0, 0.0, 10_000.0, 10_000.0, 10_000.0, 10_000.0])
    s = _StockageFactice()
    r = _factice([b"PK\x03\x04abcd", b"efgh"], s, horloge=lambda: next(temps))
    assert (r.statut, r.cause_echec) == ("echec", "delai_total") and s.abandonnes == 1


def test_ALG_13_coupure_pendant_la_lecture_incomplet():
    class _Coupee(_RepFactice):
        def lire_blocs(self, taille):
            yield b"PK\x03\x04"
            raise ErreurReseau("coupure")

    s = _StockageFactice()
    r = telecharger(_TransportFactice(_Coupee([])), s, "https://h.fr/a.zip", ["h.fr"], None,
                    MAINTENANT, attendre=lambda x: None, horloge=time.monotonic,
                    params=Parametres(min_octets=4))  # fmt: skip
    assert (r.statut, r.cause_echec) == ("echec", "incomplet") and s.abandonnes == 1


# --- paramètres ----------------------------------------------------------------------------------------


def test_ALG_13_parametres_de_la_fiche():
    p = PARAMETRES_SCRUTINS
    assert (p.max_octets, p.min_octets) == (200 * 1024 * 1024, 10 * 1024 * 1024)
    assert (p.max_redirections, p.delai_connexion, p.delai_inactivite) == (5, 30.0, 60.0)
    assert (p.delai_total, p.max_tentatives, p.attentes) == (900.0, 3, (10.0, 60.0))
    assert (p.retry_after_max, p.fraicheur_jours) == (120.0, 90)
    r = PARAMETRES_REFERENTIELS
    assert (r.max_octets, r.min_octets) == (100 * 1024 * 1024, 5 * 1024 * 1024)
    assert r.max_tentatives == 3  # autres paramètres identiques
