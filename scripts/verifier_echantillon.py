"""ALG-14 : vérification indépendante d'un échantillon de scrutins contre les fichiers bruts.

Spécification : docs/algorithmes/ALG-14-verification-independante.md.
Ce script est volontairement INDÉPENDANT du pipeline : bibliothèque standard seulement, aucun
import du paquet `etl`. Il relit l'archive source (ZIP ou dossier extrait) et les fichiers publics
(`scrutins/<id>.json`) et compare chaque chiffre. Un écart est un défaut d'un des deux côtés : il
n'est jamais corrigé ni toléré.

Usage : python scripts/verifier_echantillon.py --archive Scrutins.json.zip --export dist-data/data/v1
Code de sortie : 0 conforme ; 1 au moins un écart ; 2 entrée illisible.
"""

import argparse
import hashlib
import json
import random
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

TAILLE_ECHANTILLON = 200
IDS_OBLIGATOIRES = (
    "VTANR5L17V1",  # écart connu de la source (21 non-votants nominatifs pour 10 au total)
    "VTANR5L17V489",  # groupes PO0 (aucun groupe identifié)
    "VTANR5L17V1017",  # non-votant avec cause
    "VTANR5L17V1302",  # un seul groupe non identifié
)
NB_RECENTS = 20
MAX_OCTETS_FICHIER = 5 * 1024 * 1024  # même ordre de grandeur que la limite de lecture du pipeline
LIEN_OFFICIEL = "https://www.assemblee-nationale.fr/dyn/17/scrutins/{numero}"

_ID = re.compile(r"VTANR5L17V([1-9][0-9]*)")
_POSITIONS_BRUTES = (
    ("pours", "pour"),
    ("contres", "contre"),
    ("abstentions", "abstention"),
    ("nonVotants", "non_votant"),
)
_RESULTATS = {"adopté": "adopte", "rejeté": "rejete"}


class ErreurEntree(Exception):
    """Archive ou export illisible : on ne rend jamais « ok » sur un contrôle vide."""


# --- lecture des sources -----------------------------------------------------------------------------


def lire_brut(archive: Path) -> dict[str, bytes]:
    """Octets bruts de chaque scrutin de l'archive (ZIP ou dossier contenant `json/`)."""
    bruts: dict[str, bytes] = {}
    if archive.is_dir():
        entrees = ((p.stem, p) for p in sorted((archive / "json").glob("VTANR5L17V*.json")))
        for ident, chemin in entrees:
            if _ID.fullmatch(ident):
                bruts[ident] = chemin.read_bytes()
    elif archive.is_file():
        try:
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    nom = info.filename
                    ident = nom.rsplit("/", 1)[-1].removesuffix(".json")
                    if info.is_dir() or not nom.endswith(".json") or not _ID.fullmatch(ident):
                        continue
                    with z.open(info) as f:
                        octets = f.read(MAX_OCTETS_FICHIER + 1)
                    if len(octets) > MAX_OCTETS_FICHIER:
                        raise ErreurEntree(f"{nom} : fichier trop gros")
                    bruts[ident] = octets
        except zipfile.BadZipFile as exc:
            raise ErreurEntree(f"archive illisible : {exc}") from exc
    else:
        raise ErreurEntree(f"archive introuvable : {archive}")
    if not bruts:
        raise ErreurEntree("aucun scrutin dans l'archive")
    return bruts


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


# --- échantillon -----------------------------------------------------------------------------------------


def numero(ident: str) -> int:
    return int(_ID.fullmatch(ident).group(1))  # type: ignore[union-attr]


def tirer_echantillon(
    identifiants: list[str],
    graine: str,
    taille: int = TAILLE_ECHANTILLON,
    obligatoires: tuple[str, ...] = IDS_OBLIGATOIRES,
    nb_recents: int = NB_RECENTS,
) -> list[str]:
    """Obligatoires présents + les `nb_recents` plus récents + tirage reproductible du reste.

    Mêmes identifiants et même graine : même échantillon. Si `taille` dépasse le nombre de
    scrutins, tous sont vérifiés.
    """
    tous = sorted(set(identifiants), key=numero)
    retenus = [i for i in obligatoires if i in set(tous)]
    retenus += [i for i in tous[-nb_recents:] if i not in retenus]
    reste = [i for i in tous if i not in retenus]
    a_tirer = max(0, taille - len(retenus))
    if a_tirer >= len(reste):
        tires = reste
    else:
        tires = random.Random(int(graine, 16)).sample(reste, a_tirer)
    return sorted(set(retenus) | set(tires), key=numero)


# --- extraction indépendante (aucun code du pipeline) ------------------------------------------------


def _entier(valeur: Any, nom: str) -> int:
    if isinstance(valeur, bool):
        raise ValueError(f"{nom} : booléen")
    if isinstance(valeur, int):
        return valeur
    if isinstance(valeur, str) and re.fullmatch(r"0|[1-9][0-9]*", valeur):
        return int(valeur)
    raise ValueError(f"{nom} : entier invalide {valeur!r}")


def _liste(noeud: Any) -> list[Any]:
    """Un objet unique, une liste ou `null` -> liste (variantes XML converties en JSON)."""
    if noeud is None:
        return []
    return noeud if isinstance(noeud, list) else [noeud]


def extraire_brut(octets: bytes) -> dict[str, Any]:
    """Ce que la source dit, sous la forme du contrat publié (valeurs attendues)."""
    s = json.loads(octets.decode("utf-8"))["scrutin"]
    groupes_bruts = _liste((s["ventilationVotes"]["organe"]["groupes"] or {}).get("groupe"))
    groupes, votes = [], []
    for rang, g in enumerate(groupes_bruts, start=1):  # le rang est l'ordre dans le fichier source
        voix = g["vote"]["decompteVoix"]
        ref = g["organeRef"]
        groupes.append(
            {
                "rang": rang,
                "groupe_id": None if ref == "PO0" else ref,  # PO0 : référence non résolue
                "membres": _entier(g["nombreMembresGroupe"], "nombreMembresGroupe"),
                "pour": _entier(voix["pour"], "pour"),
                "contre": _entier(voix["contre"], "contre"),
                "abstentions": _entier(voix["abstentions"], "abstentions"),
                "non_votants": _entier(voix["nonVotants"], "nonVotants"),
            }
        )
        nominatif = g["vote"]["decompteNominatif"] or {}
        for cle, position in _POSITIONS_BRUTES:
            for v in _liste((nominatif.get(cle) or {}).get("votant")):
                cause = v.get("causePositionVote") if position == "non_votant" else None
                delegation = {"true": 1, "false": 0}[v["parDelegation"]]
                votes.append((v["acteurRef"], rang, position, delegation, cause))
    synthese = s["syntheseVote"]
    decompte = synthese["decompte"]
    return {
        "id": s["uid"],
        "numero": _entier(s["numero"], "numero"),
        "date": s["dateScrutin"],
        "titre": s["titre"],
        "type_vote": {"code": s["typeVote"]["codeTypeVote"], "libelle": s["typeVote"]["libelleTypeVote"]},
        "resultat": _RESULTATS[s["sort"]["code"]],
        "totaux": {
            "pour": _entier(decompte["pour"], "pour"),
            "contre": _entier(decompte["contre"], "contre"),
            "abstentions": _entier(decompte["abstentions"], "abstentions"),
            "non_votants": _entier(decompte["nonVotants"], "nonVotants"),
            "suffrages_exprimes": _entier(synthese["suffragesExprimes"], "suffragesExprimes"),
            "nombre_votants": _entier(synthese["nombreVotants"], "nombreVotants"),
        },
        "groupes": groupes,
        "votes": sorted(votes, key=lambda x: (x[1], x[2], x[0])),
    }


# --- comparaison -------------------------------------------------------------------------------------------


def comparer(brut: dict[str, Any], publie: dict[str, Any], sha256_brut: str, sha256_archive: str | None) -> tuple[list[dict], int]:
    """Renvoie (écarts, nombre de champs comparés) pour un scrutin."""
    ecarts: list[dict] = []
    compares = 0

    def egal(champ: str, attendu: Any, obtenu: Any) -> None:
        nonlocal compares
        compares += 1
        if attendu != obtenu:
            ecarts.append({"scrutin_id": brut["id"], "champ": champ,
                           "attendu_source": attendu, "obtenu_export": obtenu})  # fmt: skip

    for champ in ("id", "numero", "date", "titre", "resultat"):
        egal(champ, brut[champ], publie.get(champ))
    egal("type_vote.code", brut["type_vote"]["code"], (publie.get("type_vote") or {}).get("code"))
    egal("type_vote.libelle", brut["type_vote"]["libelle"], (publie.get("type_vote") or {}).get("libelle"))
    egal("source.sha256", sha256_brut, (publie.get("source") or {}).get("sha256"))
    egal("source.lien_officiel", LIEN_OFFICIEL.format(numero=brut["numero"]), (publie.get("source") or {}).get("lien_officiel"))
    if sha256_archive is not None:
        egal("source.archive_sha256", sha256_archive, (publie.get("source") or {}).get("archive_sha256"))
    for cle, valeur in brut["totaux"].items():
        egal(f"totaux.{cle}", valeur, (publie.get("totaux") or {}).get(cle))

    # groupes comparés par rang (jamais par identifiant : plusieurs groupes peuvent être PO0)
    publies = {g.get("rang"): g for g in publie.get("groupes", [])}
    egal("groupes.rangs", [g["rang"] for g in brut["groupes"]], sorted(publies, key=lambda r: (r is None, r)))
    for g in brut["groupes"]:
        p = publies.get(g["rang"], {})
        for cle in ("groupe_id", "membres", "pour", "contre", "abstentions", "non_votants"):
            egal(f"groupes[{g['rang']}].{cle}", g[cle], p.get(cle))
        egal(f"groupes[{g['rang']}].ventilation_disponible", g["groupe_id"] is not None, p.get("ventilation_disponible"))

    # votes : nombre par position, puis chaque (député, rang, position, délégation, cause)
    publies_votes = sorted((tuple(v) for v in publie.get("votes", [])), key=lambda x: (x[1], x[2], x[0]))
    for position in ("pour", "contre", "abstention", "non_votant"):
        egal(f"votes.nombre.{position}",
             sum(1 for v in brut["votes"] if v[2] == position),
             sum(1 for v in publies_votes if len(v) > 2 and v[2] == position))  # fmt: skip
    egal("votes", [list(v) for v in brut["votes"]], [list(v) for v in publies_votes])
    return ecarts, compares


# --- vérification d'ensemble ---------------------------------------------------------------------------------


def verifier(
    archive: Path,
    export: Path,
    graine: str | None = None,
    taille: int = TAILLE_ECHANTILLON,
) -> dict[str, Any]:
    """Contrôle global (mêmes scrutins des deux côtés) puis échantillon détaillé."""
    if not export.is_dir():
        raise ErreurEntree(f"export introuvable : {export}")
    bruts = lire_brut(archive)
    sha_archive = sha256_fichier(archive) if archive.is_file() else None
    graine = graine or (sha_archive or hashlib.sha256("".join(sorted(bruts)).encode()).hexdigest())
    ecarts: list[dict] = []

    # global : les identifiants de l'archive et ceux de l'export sont les mêmes
    publies = {p.stem for p in (export / "scrutins").glob("*.json")} if (export / "scrutins").is_dir() else set()
    for ident in sorted(set(bruts) - publies, key=numero):
        ecarts.append({"scrutin_id": ident, "champ": "fichier", "attendu_source": "présent", "obtenu_export": "absent"})
    for ident in sorted(publies - set(bruts)):
        ecarts.append({"scrutin_id": ident, "champ": "fichier", "attendu_source": "absent", "obtenu_export": "présent"})
    try:
        meta = json.loads((export / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ErreurEntree(f"meta.json illisible : {exc}") from exc
    if meta.get("nombre_scrutins") != len(bruts):
        ecarts.append({"scrutin_id": None, "champ": "meta.nombre_scrutins",
                       "attendu_source": len(bruts), "obtenu_export": meta.get("nombre_scrutins")})  # fmt: skip

    tires = tirer_echantillon(sorted(bruts, key=numero), graine, taille)
    champs = 0
    verifies = 0
    for ident in tires:
        chemin = export / "scrutins" / f"{ident}.json"
        if not chemin.is_file():
            continue  # déjà signalé par le contrôle global
        try:
            publie = json.loads(chemin.read_text(encoding="utf-8"))
            brut = extraire_brut(bruts[ident])
        except (ValueError, KeyError, TypeError) as exc:
            ecarts.append({"scrutin_id": ident, "champ": "lecture", "attendu_source": "lisible", "obtenu_export": str(exc)})
            continue
        e, n = comparer(brut, publie, hashlib.sha256(bruts[ident]).hexdigest(), sha_archive)
        ecarts += e
        champs += n
        verifies += 1
    return {
        "graine": graine,
        "nombre_scrutins_archive": len(bruts),
        "tires": tires,
        "nb_verifies": verifies,
        "nb_champs_compares": champs,
        "ecarts": ecarts,
        "statut": "ok" if not ecarts and verifies > 0 else "echec",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ALG-14 : vérification indépendante d'un échantillon")
    p.add_argument("--archive", required=True, help="ZIP des scrutins ou dossier extrait (avec json/)")
    p.add_argument("--export", required=True, help="répertoire /data/v1/ exporté")
    p.add_argument("--graine", default=None, help="graine hexadécimale (défaut : SHA-256 de l'archive)")
    p.add_argument("--taille", type=int, default=TAILLE_ECHANTILLON)
    p.add_argument("--sortie", default=None, help="écrit verification.json à cet emplacement")
    a = p.parse_args(argv)
    try:
        rapport = verifier(Path(a.archive), Path(a.export), a.graine, a.taille)
    except ErreurEntree as exc:
        print(f"entrée illisible : {exc}", file=sys.stderr)
        return 2
    texte = json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if a.sortie:
        Path(a.sortie).write_text(texte, encoding="utf-8")
    print(f"vérification : {rapport['statut']} ({rapport['nb_verifies']} scrutins, "
          f"{rapport['nb_champs_compares']} champs, {len(rapport['ecarts'])} écart(s))")  # fmt: skip
    for e in rapport["ecarts"][:20]:
        print(f"  écart : {e}")
    return 0 if rapport["statut"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
