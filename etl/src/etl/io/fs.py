"""Écriture des fichiers exportés (ALG-11) et du journal d'import (ALG-07.15)."""

import dataclasses
import json
import os
import shutil
from pathlib import Path

from ..algos.alg07_import_idempotent import RapportImport


def ecrire_journal_import(rapport: RapportImport, dossier: Path | str) -> Path:
    """Écrit le rapport complet dans `import-<id>.json` (`import-sans-id.json` si pas de ligne)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    identifiant = rapport.import_id if rapport.import_id is not None else "sans-id"
    chemin = dossier / f"import-{identifiant}.json"
    chemin.write_text(
        json.dumps(dataclasses.asdict(rapport), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chemin


class _FichierTemporaire:
    def __init__(self, chemin: Path):
        self.chemin = chemin
        self._flux = chemin.open("wb")

    def ecrire(self, bloc: bytes) -> None:
        self._flux.write(bloc)

    def fermer(self) -> None:
        if not self._flux.closed:
            self._flux.close()


class StockageFichiers:
    """Implémente `Stockage` (ALG-13) : archives adressées par SHA-256 dans un répertoire.

    Le fichier temporaire est créé dans le même répertoire que l'archive finale (même volume :
    le renommage est possible), puis renommé en `<sha256>.zip` ou supprimé si ce fichier existe.
    """

    def __init__(self, repertoire: Path | str):
        self.repertoire = Path(repertoire)
        self.repertoire.mkdir(parents=True, exist_ok=True)
        self._compteur = 0

    def ouvrir_temporaire(self) -> _FichierTemporaire:
        self._compteur += 1
        return _FichierTemporaire(self.repertoire / f".telechargement-{os.getpid()}-{self._compteur}.tmp")

    def abandonner(self, temp: _FichierTemporaire) -> None:
        temp.fermer()
        temp.chemin.unlink(missing_ok=True)

    def conserver(self, temp: _FichierTemporaire, sha256: str) -> tuple[str, bool]:
        temp.fermer()
        cible = self.repertoire / f"{sha256}.zip"
        if cible.exists():
            temp.chemin.unlink(missing_ok=True)  # contenu identique : jamais d'écrasement
            return str(cible), False
        os.replace(temp.chemin, cible)
        return str(cible), True

    def retirer(self, chemin: str) -> None:
        Path(chemin).unlink(missing_ok=True)

    def ecrire_provenance(self, provenance: dict) -> None:
        (self.repertoire / "provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )


# --- ALG-11.14 : publication d'un répertoire ---------------------------------------------------------


class ErreurPublication(Exception):
    """La publication a échoué ; l'ancienne version a été conservée ou restaurée."""


def recuperer_publication_interrompue(sortie: Path | str) -> bool:
    """Au démarrage : un `<sortie>.precedent` orphelin signale une publication interrompue.

    L'ancienne version complète est restaurée avant tout (ALG-11.14). Renvoie True s'il a fallu
    restaurer.
    """
    sortie = Path(sortie)
    precedent = sortie.with_name(sortie.name + ".precedent")
    if not precedent.exists():
        return False
    if sortie.exists():
        shutil.rmtree(precedent)  # la nouvelle version est en place : l'ancienne est inutile
        return False
    os.replace(precedent, sortie)
    return True


def publier_fichiers(fichiers: dict[str, bytes], sortie: Path | str) -> None:
    """Écrit `fichiers` dans un répertoire temporaire frère puis le publie (ALG-11.14).

    Procédure : (1) restaurer une publication interrompue ; (2) écrire dans `<sortie>.tmp`, vidé
    au départ ; (3) renommer l'ancien `<sortie>` en `<sortie>.precedent` ; (4) renommer le
    temporaire en `<sortie>` ; (5) supprimer `.precedent` seulement si les deux renommages ont
    réussi. Si le second échoue, l'ancien répertoire est restauré. Un renommage de répertoire n'est
    pas atomique partout : c'est la procédure, pas l'opération, qui garantit qu'il reste toujours
    une version complète.
    """
    sortie = Path(sortie)
    temporaire = sortie.with_name(sortie.name + ".tmp")
    precedent = sortie.with_name(sortie.name + ".precedent")
    recuperer_publication_interrompue(sortie)
    if temporaire.exists():
        shutil.rmtree(temporaire)  # aucun fichier périmé d'une exécution précédente
    try:
        for chemin, octets in fichiers.items():
            cible = temporaire / chemin
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(octets)
    except OSError as exc:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise ErreurPublication(f"écriture impossible : {exc}") from exc
    avait_une_version = sortie.exists()
    try:
        if avait_une_version:
            os.replace(sortie, precedent)
        try:
            os.replace(temporaire, sortie)
        except OSError:
            if avait_une_version:
                os.replace(precedent, sortie)  # restauration
            raise
    except OSError as exc:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise ErreurPublication(f"publication impossible : {exc}") from exc
    if precedent.exists():
        shutil.rmtree(precedent)


def retirer_temporaire(sortie: Path | str) -> None:
    """Échec d'export : supprimer le temporaire, conserver l'ancien répertoire intact."""
    sortie = Path(sortie)
    shutil.rmtree(sortie.with_name(sortie.name + ".tmp"), ignore_errors=True)
