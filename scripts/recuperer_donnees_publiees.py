"""Récupère les données actuellement en ligne (`/data/v1/`) pour redéployer le front sans nouvelle synchro.

Chaque déploiement Cloudflare remplace tous les fichiers du site : pour publier une nouvelle version
du front, il faut donc rejouer les données déjà publiées. Ce script les télécharge, puis recalcule
`donnees_sha256` (même règle qu'ALG-11 : SHA-256 de la liste `chemin<TAB>sha256` de tous les fichiers
sauf `manifeste.json` et `meta.json`) et le compare à celui du manifeste. Une donnée tronquée, altérée
ou mélangée entre deux publications est refusée : on ne redéploie jamais un site à moitié à jour.

Bibliothèque standard seulement. Code de sortie : 0 (données récupérées et vérifiées), 1 (refus).

    python scripts/recuperer_donnees_publiees.py <url_publiee_avec_/data/v1/> <dossier_de_sortie>
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCHEMA = "v1"
TENTATIVES = 3
TIMEOUT_S = 30
PARALLELISME = 16
# Fichiers à ne pas compter dans l'empreinte des données (ALG-11 : calculée avant leur création).
HORS_EMPREINTE = {"manifeste.json", "meta.json"}
FIXES = ["meta.json", "manifeste.json", "groupes.json", "deputes.json", "stats.json", "qualite.json", "scrutins-index.json"]


class Refus(Exception):
    """Les données publiées ne peuvent pas être reprises telles quelles."""


def telecharger(base: str, chemin: str) -> bytes:
    """Télécharge un fichier publié ; réessaie sur une erreur réseau, jamais sur un 404."""
    url = base + chemin
    derniere: Exception | None = None
    for essai in range(TENTATIVES):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_S) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Refus(f"{chemin} : introuvable (404)") from e
            derniere = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            derniere = e
        time.sleep(2**essai)
    raise Refus(f"{chemin} : téléchargement impossible ({derniere})")


def recuperer(url_publiee: str, sortie: Path) -> int:
    """Télécharge et vérifie les données ; retourne le nombre de fichiers écrits."""
    base = url_publiee if url_publiee.endswith("/") else url_publiee + "/"
    if not base.startswith("https://") and not base.startswith("http://127.0.0.1"):
        raise Refus("L'adresse publiée doit être en https")

    fichiers: dict[str, bytes] = {}
    for chemin in FIXES:
        fichiers[chemin] = telecharger(base, chemin)

    try:
        meta = json.loads(fichiers["meta.json"])
        manifeste = json.loads(fichiers["manifeste.json"])
        groupes = json.loads(fichiers["groupes.json"])["groupes"]
        fragments = json.loads(fichiers["scrutins-index.json"])["fragments"]
    except (ValueError, KeyError, TypeError) as e:
        raise Refus(f"Fichier de référence illisible : {e}") from e
    if meta.get("schema") != SCHEMA or manifeste.get("schema") != SCHEMA:
        raise Refus(f"Schéma publié inattendu (attendu {SCHEMA})")

    # Liste complète des fichiers, déduite des fichiers de référence (aucun listing de dossier en ligne).
    restants = (
        [f["fichier"] for f in fragments]
        + [f"scrutins/{sid}.json" for sid in manifeste["scrutins"]]
        + [f"groupes/{g['id']}.json" for g in groupes]
    )
    with ThreadPoolExecutor(max_workers=PARALLELISME) as pool:
        for chemin, contenu in zip(restants, pool.map(lambda c: telecharger(base, c), restants), strict=True):
            fichiers[chemin] = contenu

    lignes = "".join(
        f"{c}\t{hashlib.sha256(o).hexdigest()}\n"
        for c, o in sorted(fichiers.items())
        if c not in HORS_EMPREINTE
    )
    calcule = hashlib.sha256(lignes.encode("utf-8")).hexdigest()
    if calcule != manifeste.get("donnees_sha256"):
        raise Refus("Empreinte des données récupérées différente de celle du manifeste")
    if meta.get("version_donnees") != calcule[:16]:
        raise Refus("meta.json ne correspond pas aux données récupérées (publication en cours ?)")

    for chemin, contenu in fichiers.items():
        cible = sortie / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(contenu)
    return len(fichiers)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    try:
        n = recuperer(argv[0], Path(argv[1]))
    except Refus as e:
        print(f"Refus : {e}", file=sys.stderr)
        return 1
    print(f"{n} fichiers récupérés et vérifiés dans {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
