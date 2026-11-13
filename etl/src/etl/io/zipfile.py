"""Lecture du ZIP (utilisé pour ALG-01) : une seule ouverture, aucune écriture sur le disque."""

import hashlib
import stat
import zipfile
from typing import BinaryIO

from ..algos.alg01_archive import EntreeBrute, ErreurLecture, ErreurSource

_BLOC = 1024 * 1024  # 1 Mio (ALG-01.3)
_METHODES_SUPPORTEES = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


class SourceZip:
    """Source ZIP : empreinte du fichier, liste des entrées, lecture bornée."""

    type_source = "zip"
    type_empreinte = "fichier"

    def __init__(self, descripteur: BinaryIO) -> None:
        self._descripteur = descripteur
        self._zip: zipfile.ZipFile | None = None
        self._infos: dict[str, zipfile.ZipInfo] = {}
        self._empreinte = ""

    @classmethod
    def ouvrir(cls, chemin: str) -> "SourceZip":
        """Ouvre le fichier une seule fois, calcule l'empreinte puis ouvre l'archive.

        Raises:
            ErreurSource: fichier illisible ou archive ZIP invalide.
        """
        # ALG-01.2 : un seul descripteur, conservé pour les étapes 3 et 4
        try:
            descripteur = open(chemin, "rb")  # noqa: SIM115 (fermé par fermer())
        except OSError as exc:
            raise ErreurSource("source_introuvable", str(exc)) from exc
        source = cls(descripteur)
        try:
            # ALG-01.3 : SHA-256 par blocs de 1 Mio, puis retour au début
            hachage = hashlib.sha256()
            while bloc := descripteur.read(_BLOC):
                hachage.update(bloc)
            source._empreinte = hachage.hexdigest()
            descripteur.seek(0)
            # ALG-01.4 : ouverture de l'archive depuis ce descripteur
            source._zip = zipfile.ZipFile(descripteur)
        except (zipfile.BadZipFile, OSError) as exc:
            descripteur.close()
            raise ErreurSource("zip_invalide", str(exc)) from exc
        return source

    def fermer(self) -> None:
        if self._zip is not None:
            self._zip.close()
        self._descripteur.close()

    def empreinte_fichier(self) -> str:
        return self._empreinte

    def lister(self, plafond: int | None = None) -> list[EntreeBrute]:
        assert self._zip is not None
        entrees: list[EntreeBrute] = []
        for info in self._zip.infolist():
            # ALG-01.12 : lien symbolique d'après les attributs Unix du ZIP
            mode = info.external_attr >> 16
            self._infos.setdefault(info.filename, info)
            entrees.append(
                EntreeBrute(
                    nom=info.filename,
                    est_dossier=info.filename.endswith("/"),
                    chiffree=bool(info.flag_bits & 0x1),
                    methode_supportee=info.compress_type in _METHODES_SUPPORTEES,
                    lien_symbolique=stat.S_ISLNK(mode),
                    taille_declaree=info.file_size,
                    taille_compressee=info.compress_size,
                )
            )
        return entrees

    def lire(self, nom: str, plafond: int) -> bytes:
        """Lit au plus `plafond` octets de l'entrée (ALG-01.13) ; ErreurLecture si corrompue."""
        assert self._zip is not None
        try:
            with self._zip.open(self._infos[nom]) as flux:
                return flux.read(plafond)
        except (zipfile.BadZipFile, OSError, EOFError, zipfile.LargeZipFile, NotImplementedError,
                RuntimeError) as exc:
            # ALG-01.14 : CRC invalide ou flux corrompu
            raise ErreurLecture(str(exc)) from exc
