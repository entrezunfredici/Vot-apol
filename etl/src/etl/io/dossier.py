"""Lecture d'un dossier déjà extrait (utilisé pour ALG-01) : lecture seule, liens non suivis."""

import os
from pathlib import Path

from ..algos.alg01_archive import EntreeBrute, ErreurLecture, ErreurSource


class SourceDossier:
    """Source dossier : parcourt `source/json` et lit les fichiers réels uniquement."""

    type_source = "dossier"
    type_empreinte = "manifeste"

    def __init__(self, racine: str | Path) -> None:
        self._racine = Path(racine)

    @classmethod
    def ouvrir(cls, chemin: str | Path) -> "SourceDossier":
        if not Path(chemin).is_dir():
            raise ErreurSource("source_introuvable", f"{chemin} n'est pas un dossier")
        return cls(chemin)

    def fermer(self) -> None:
        """Rien à fermer pour un dossier ; présent pour l'interface commune."""

    def empreinte_fichier(self) -> None:
        return None

    def lister(self, plafond: int | None = None) -> list[EntreeBrute]:
        # ALG-01.8 : parcours en profondeur de source/json, sans suivre de lien symbolique
        entrees: list[EntreeBrute] = []
        base = self._racine / "json"
        if not base.is_dir():
            return entrees
        pile = [base]
        while pile:
            dossier = pile.pop()
            with os.scandir(dossier) as it:
                for e in it:
                    # ALG-01.5 : parcours borné ; un dépassement est détecté par l'appelant
                    if plafond is not None and len(entrees) > plafond:
                        return entrees
                    nom = e.path
                    relatif = Path(nom).relative_to(self._racine).as_posix()
                    if e.is_symlink():
                        # Refusé (motif lien_symbolique) si le nom a la forme d'un scrutin,
                        # ignoré avec compteur sinon : décision prise par ALG-01.
                        entrees.append(
                            EntreeBrute(relatif, False, False, True, True, 0, 0)
                        )
                    elif e.is_dir(follow_symlinks=False):
                        pile.append(Path(nom))
                    elif e.is_file(follow_symlinks=False):
                        taille = e.stat(follow_symlinks=False).st_size
                        entrees.append(
                            EntreeBrute(relatif, False, False, True, False, taille, taille)
                        )
        return entrees

    def lire(self, nom: str, plafond: int) -> bytes:
        """Lit au plus `plafond` octets (ALG-01.13) ; ErreurLecture si le fichier est illisible."""
        try:
            with open(self._racine / nom, "rb") as flux:
                return flux.read(plafond)
        except OSError as exc:
            raise ErreurLecture(str(exc)) from exc
