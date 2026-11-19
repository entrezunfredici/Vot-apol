"""Orchestration : télécharger → lire → normaliser → extraire → réconcilier → importer → exporter.

Seul module (avec cli.py) autorisé à relier algos/ et io/.
"""

import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from .algos import (
    alg02_normalisation,
    alg03_position_majoritaire,
    alg04_extraction_scrutin,
    alg06_mises_au_point,
    alg08_classification,
    alg09_resolution_noms,
    alg10_indicateurs_groupe,
    alg11_export_statique,
    alg11_schemas,
)
from .algos.alg01_archive import (
    LIMITES_PAR_DEFAUT,
    PROFIL_REFERENTIELS,
    PROFIL_SCRUTINS,
    ErreurSource,
    LimitesLecture,
    ProfilLecture,
    SourceArchive,
    lire_archive,
)
from .algos.alg02_normalisation import normaliser_scrutin
from .algos.alg04_extraction_scrutin import ErreurExtraction, extraire_scrutin
from .algos.alg05_reconciliation import (
    ErreurEcartsConnus,
    charger_ecarts_connus,
    controler,
    depuis_lot,
)
from .algos.alg06_mises_au_point import rattacher
from .algos.alg07_import_idempotent import ErreurBase, calculer_version_etl, importer
from .algos.alg08_classification import VERSION_REGLES, ErreurCorrections, charger_corrections
from .algos.alg09_resolution_noms import resoudre_noms
from .algos.alg11_export_statique import (
    calculer_diff,
    empreinte_entrees,
    exporter,
    serialiser,
)
from .algos.alg12_garde_fou_deploiement import (
    decider,
    deploiement_autorise,
    doit_traiter,
    serialiser_decision,
    verifier_deploiement,
)
from .algos.alg13_telechargement import (
    PARAMETRES_REFERENTIELS,
    PARAMETRES_SCRUTINS,
    ErreurReseau,
    telecharger,
)
from .config import DATA_DIR, SOURCE_URL, URL_REFERENTIELS, URL_SCRUTINS
from .io.db import (
    DepotSqlite,
    appliquer_migrations,
    ecrire_noms,
    lire_contexte_base,
    lire_pour_controle,
    lire_references_noms,
    lire_referentiels_export,
    lire_scrutins_export,
    version_schema_attendue,
)
from .io.dossier import SourceDossier
from .io.fs import (
    ErreurPublication,
    StockageFichiers,
    ecrire_journal_import,
    publier_fichiers,
    recuperer_publication_interrompue,
    retirer_temporaire,
)
from .io.http import TransportHttp, lire_json_publie
from .io.zipfile import SourceZip
from .models import (
    ContexteExport,
    DecisionPublication,
    EntreeAcceptee,
    EntreesDecision,
    LotScrutin,
    Parametres,
    RapportExport,
    RapportImport,
    RapportLecture,
    RapportReconciliation,
    RapportTelechargement,
    ScrutinAControler,
    ScrutinRefuse,
    Transport,
)

ECARTS_CONNUS = Path(__file__).parents[2] / "ecarts_connus.json"
CORRECTIONS_CLASSIFICATION = Path(__file__).parents[2] / "corrections_classification.json"
JOURNAUX = DATA_DIR / "journaux"


def lire_source(
    chemin: str,
    legislature: int = 17,
    limites: LimitesLecture = LIMITES_PAR_DEFAUT,
    profil: ProfilLecture = PROFIL_SCRUTINS,
) -> tuple[list[EntreeAcceptee], RapportLecture]:
    """Ouvre un ZIP ou un dossier et applique ALG-01 (étape ALG-01.1 : choix de la source)."""
    # ALG-01.1 : source absente ou ni fichier ni dossier -> échec explicite
    source: SourceArchive
    try:
        if os.path.isdir(chemin):
            source = SourceDossier.ouvrir(chemin)
        elif os.path.isfile(chemin):
            source = SourceZip.ouvrir(chemin)
        else:
            return [], RapportLecture(motif_echec="source_introuvable")
    except ErreurSource as exc:
        return [], RapportLecture(motif_echec=exc.motif)
    try:
        return lire_archive(source, legislature, limites, profil)
    finally:
        source.fermer()


def version_etl() -> str:
    """ALG-07, décision 2 : empreinte du contenu des modules ALG-02, ALG-04 et ALG-06."""
    modules = (alg02_normalisation, alg04_extraction_scrutin, alg06_mises_au_point)
    return calculer_version_etl(Path(m.__file__).read_text(encoding="utf-8") for m in modules)


def version_algorithmes() -> str:
    """ALG-12.1 : empreinte du code des algorithmes qui produisent les données publiées.

    Couvre ALG-02, 03, 04, 06, 08, 09, 10 et 11 (et les schémas d'export) : une correction d'un de
    ces algorithmes doit faire traiter à nouveau une archive pourtant inchangée.
    """
    modules = (
        alg02_normalisation, alg03_position_majoritaire, alg04_extraction_scrutin,
        alg06_mises_au_point, alg08_classification, alg09_resolution_noms,
        alg10_indicateurs_groupe, alg11_export_statique, alg11_schemas,
    )  # fmt: skip
    return calculer_version_etl(Path(m.__file__).read_text(encoding="utf-8") for m in modules)


def preparer_flux(
    entrees: list[EntreeAcceptee],
    importe_le: str,
    version: str,
    a_controler: list[ScrutinAControler],
    source_url: str | None = None,
) -> Iterator[LotScrutin | ScrutinRefuse]:
    """ALG-02 -> ALG-04 -> ALG-06 (A) pour chaque entrée, dans l'ordre des numéros.

    Une erreur à l'une des étapes donne un `ScrutinRefuse` (rien ne sera écrit pour ce scrutin).
    Les chiffres du niveau « lot » d'ALG-05 sont collectés dans `a_controler`.
    """
    for entree in sorted(entrees, key=lambda e: e.numero):
        identifiant = entree.nom.rsplit("/", 1)[-1].removesuffix(".json")
        resultat = normaliser_scrutin(entree.document_json)
        if resultat.scrutin is None:
            codes = sorted({e.code for e in resultat.erreurs})
            yield ScrutinRefuse(identifiant, "normalisation : " + ", ".join(codes))
            continue
        try:
            lot = extraire_scrutin(
                resultat.scrutin,
                entree.nom,
                entree.sha256_fichier,
                (source_url if source_url is not None else SOURCE_URL) or None,
                importe_le,
                version,
            )
        except ErreurExtraction as exc:
            yield ScrutinRefuse(identifiant, f"extraction : {exc.motif}")
            continue
        a_controler.append(depuis_lot(resultat.scrutin, lot))
        yield rattacher(lot)


def _resume(rapport: RapportImport) -> dict:
    return {
        "statut": rapport.statut,
        "motif_echec": rapport.motif_echec,
        "import_id": rapport.import_id,
        "statut_lecture": rapport.statut_lecture,
        "nouveaux": rapport.nouveaux,
        "inchanges": rapport.inchanges,
        "modifies": len(rapport.modifies),
        "retraites": len(rapport.retraites),
        "refuses": len(rapport.refuses),
        "absents_de_l_archive": len(rapport.absents_de_l_archive),
        "duree_secondes": round(rapport.duree_secondes, 2),
    }


def _afficher_reconciliation(rapport: RapportReconciliation) -> None:
    nb_ecarts = sum(c["nb_ecarts"] for c in rapport.controles.values())
    print(
        f"reconciliation ({rapport.niveau}) : {rapport.statut}, "
        f"{rapport.scrutins_controles} scrutins, {nb_ecarts} écarts"
    )
    for e in rapport.ecarts[:20]:
        connu = " (connu)" if e.connu else ""
        print(
            f"  {e.controle} {e.scrutin_id} rang={e.groupe_rang} {e.detail or ''} "
            f"attendu={e.attendu} obtenu={e.obtenu}{connu}"
        )
    for a in rapport.avertissements:
        print(f"  avertissement : {a}")


def run_inspect(zip_path: str) -> int:
    """Lit l'archive (ALG-01) et affiche le rapport de lecture, sans rien écrire."""
    _, lecture = lire_source(zip_path)
    rapport = {**lecture.__dict__, "refusees": len(lecture.refusees)}
    print(json.dumps(rapport, indent=2, ensure_ascii=False, default=str))
    return 0 if lecture.statut == "complet" else 1


def _horloge() -> datetime:
    return datetime.now(UTC)  # seul endroit où l'heure est lue ; les algos la reçoivent en argument


def executer_import(
    zip_path: str,
    db_path: str,
    importe_le: str,
    dry_run: bool = False,
    journal_dir: str | Path | None = None,
    source_url: str | None = None,
) -> tuple[RapportImport, RapportLecture, list[ScrutinAControler], Path]:
    """ALG-01 -> 02 -> 04 -> 06 -> 07 ; renvoie (rapport, lecture, lots à contrôler, journal).

    Lève `ErreurBase` si la base est inutilisable. Aucun affichage : c'est l'appelant qui décide.
    """
    entrees, lecture = lire_source(zip_path)
    a_controler: list[ScrutinAControler] = []
    flux = preparer_flux(entrees, importe_le, version_etl(), a_controler, source_url)
    depot = DepotSqlite(db_path, lecture_seule=dry_run)

    # ALG-07.12 : un Ctrl-C termine le scrutin en cours et valide le lot
    demande = {"stop": False}
    ancien = signal.signal(signal.SIGINT, lambda *_: demande.update(stop=True))
    try:
        rapport = importer(
            depot,
            flux,
            lecture,
            importe_le,
            _horloge,
            version_schema_attendue(),
            simulation=dry_run,
            interruption=lambda: demande["stop"],
        )
    finally:
        depot.fermer()
        signal.signal(signal.SIGINT, ancien)
    chemin = ecrire_journal_import(rapport, journal_dir or JOURNAUX)
    return rapport, lecture, a_controler, chemin


def nombre_scrutins_attendu(rapport: RapportImport) -> int:
    """Nombre de scrutins que la base doit contenir après cet import (ALG-05, niveau base)."""
    return (
        rapport.nouveaux
        + rapport.inchanges
        + len(rapport.modifies)
        + len(rapport.retraites)
        + len(rapport.absents_de_l_archive)
    )


def run_import(
    zip_path: str,
    db_path: str,
    dry_run: bool = False,
    journal_dir: str | Path | None = None,
    ecarts_connus: str | Path = ECARTS_CONNUS,
) -> int:
    """ALG-01 -> 02 -> 04 -> 06 -> 07, puis ALG-05 (niveau lot, puis niveau base après l'import)."""
    importe_le = _horloge().isoformat()
    try:
        connus = charger_ecarts_connus(ecarts_connus)
    except ErreurEcartsConnus as exc:
        print(f"écarts connus illisibles : {exc}")
        return 2

    try:
        rapport, _, a_controler, chemin = executer_import(
            zip_path, db_path, importe_le, dry_run, journal_dir
        )
    except ErreurBase as exc:
        print(f"base inutilisable : {exc.motif}")
        return 1

    print(json.dumps(_resume(rapport), indent=2, ensure_ascii=False))
    print(f"journal : {chemin}")

    # ALG-05 niveau lot : contrôles sur les lots construits (informatif, ne bloque pas l'import)
    _afficher_reconciliation(controler(a_controler, connus, "lot"))

    code = 0 if rapport.statut in ("termine", "simulation") else 1
    if rapport.statut in ("termine", "termine_avec_erreurs") and not dry_run:
        # ALG-05 niveau base : après l'import, relu par requêtes
        code = max(code, _valider_base(db_path, connus, nombre_scrutins_attendu(rapport)))
    return code


def _valider_base(db_path: str | Path, connus, nb_attendu: int | None) -> int:
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        rapport = controler(lire_pour_controle(conn), connus, "base", nb_attendu)
    finally:
        conn.close()
    _afficher_reconciliation(rapport)
    return 1 if rapport.statut == "ecarts_nouveaux" else 0


def run_validate(db_path: str, ecarts_connus: str | Path = ECARTS_CONNUS) -> int:
    """ALG-05 niveau base : code de sortie 1 si des écarts nouveaux bloquants existent."""
    if not Path(db_path).is_file():
        print(f"base introuvable : {db_path}")
        return 2
    try:
        connus = charger_ecarts_connus(ecarts_connus)
    except ErreurEcartsConnus as exc:
        print(f"écarts connus illisibles : {exc}")
        return 2
    return _valider_base(db_path, connus, None)


def _ecarts_publies(reconciliation, connus) -> list[dict]:
    """Écarts connus (déjà validés) publiés dans qualite.json, avec leur motif."""
    par_cle = {k.cle(): k for k in connus}
    publies = []
    for e in reconciliation.ecarts:
        if not e.connu:
            continue
        k = par_cle[(e.controle, e.scrutin_id, e.groupe_rang, e.detail, e.attendu, e.obtenu)]
        publies.append(
            {
                "controle": e.controle,
                "scrutin_id": e.scrutin_id,
                "detail": e.detail,
                "attendu": e.attendu,
                "obtenu": e.obtenu,
                "motif": k.motif,
                "valide_le": k.valide_le,
            }
        )
    return publies


def entrees_composites(archive_sha256: str, referentiels_sha256: str | None) -> dict:
    """ALG-12.1 : les entrées dont dépendent les données publiées (clé `entrees` du manifeste).

    Même composition pour la décision « rien à faire » (avant tout traitement) et pour l'export :
    si elles divergeaient, une archive inchangée serait retraitée à chaque exécution.
    """
    entrees = {
        "versions_algorithmes": version_algorithmes(),
        "archive_sha256": archive_sha256,
        "version_etl": version_etl(),
        "version_regles_classification": VERSION_REGLES,
    }
    if referentiels_sha256 is not None:
        entrees["referentiels_sha256"] = referentiels_sha256
    return entrees


def executer_export(
    db_path: str,
    out_dir: str,
    connus,
    liste_corrections,
    precedent: dict | None,
    referentiels_sha256: str | None = None,
    type_empreinte: str = "non_renseigne",
) -> tuple[RapportExport, RapportReconciliation, int]:
    """ALG-05 (base) -> ALG-11 : renvoie (rapport d'export, réconciliation, 1 si publication KO).

    Le répertoire de sortie n'est remplacé que si l'export est `ok` ; sinon l'ancien reste intact.
    """
    # ALG-11.1 : état de la réconciliation sur cette base, relue par requêtes
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        reconciliation = controler(lire_pour_controle(conn), connus, "base", None)
        base = lire_contexte_base(conn)
        referentiels = lire_referentiels_export(conn)
        contexte = ContexteExport(
            archive_sha256=base["archive_sha256"],
            type_empreinte=type_empreinte,
            donnees_du=base["donnees_du"],
            version_etl=version_etl(),
            version_regles_classification=VERSION_REGLES,
            statut_reconciliation=reconciliation.statut,
            nombre_scrutins_base=base["nombre_scrutins"],
            ecarts_connus=_ecarts_publies(reconciliation, connus),
            corrections=tuple(liste_corrections),
            entrees={"versions_algorithmes": version_algorithmes()}
            | ({"referentiels_sha256": referentiels_sha256} if referentiels_sha256 else {}),
            manifeste_precedent=precedent,
        )
        sortie = Path(out_dir)
        recuperer_publication_interrompue(sortie)
        fichiers, rapport = exporter(lire_scrutins_export(conn), referentiels, contexte)
    finally:
        conn.close()

    if rapport.statut != "ok":
        retirer_temporaire(sortie)  # l'ancien répertoire reste intact
        return rapport, reconciliation, 0
    try:
        publier_fichiers(fichiers, sortie)
    except ErreurPublication as exc:
        print(f"publication impossible : {exc}")
        return rapport, reconciliation, 1
    return rapport, reconciliation, 0


def run_export(
    db_path: str,
    out_dir: str,
    ecarts_connus: str | Path = ECARTS_CONNUS,
    corrections: str | Path = CORRECTIONS_CLASSIFICATION,
    manifeste_precedent: str | Path | None = None,
) -> int:
    """ALG-05 (base) -> ALG-11 : exporte les fichiers publics vers `out_dir`, ou ne change rien.

    Code de sortie : 0 export publié ; 1 export refusé (la version précédente reste intacte) ;
    2 entrée illisible (base, écarts connus, corrections, manifeste).
    """
    if not Path(db_path).is_file():
        print(f"base introuvable : {db_path}")
        return 2
    try:
        connus = charger_ecarts_connus(ecarts_connus)
        liste_corrections = charger_corrections(corrections)
        precedent = (
            json.loads(Path(manifeste_precedent).read_text(encoding="utf-8"))
            if manifeste_precedent
            else None
        )
    except (ErreurEcartsConnus, ErreurCorrections, OSError, ValueError) as exc:
        print(f"entrée illisible : {exc}")
        return 2
    rapport, _, echec_publication = executer_export(
        db_path, out_dir, connus, liste_corrections, precedent
    )
    if echec_publication:
        return 1
    print(json.dumps(rapport.__dict__, indent=2, ensure_ascii=False, default=list))
    return 0 if rapport.statut == "ok" else 1


# --- sync : télécharger -> importer -> noms -> exporter -> vérifier -> décider -------------------------

SCRIPT_VERIFICATION = Path(__file__).parents[3] / "scripts" / "verifier_echantillon.py"
FICHIERS_PUBLIES = ("manifeste.json", "meta.json", "qualite.json", "groupes.json", "deputes.json")


@dataclass(frozen=True)
class ConfigSync:
    """Réglages d'une exécution de `etl sync` (aucun secret : le déploiement est un autre travail)."""

    dossier_travail: Path  # archives, base, journaux, decision.json, verification.json
    sortie: Path  # répertoire exporté (l'artefact à déployer)
    url_scrutins: str = URL_SCRUTINS
    url_referentiels: str = URL_REFERENTIELS
    url_publiee: str = ""  # racine des données en ligne ; vide = aucune version publiée connue
    tests_ok: bool = False  # tests, lexique, couleurs : exécutés avant, par le workflow (G05)
    forcer: bool = False
    mode_sur: bool = True  # jamais de publication automatique sans instruction explicite
    ecarts_connus: Path = ECARTS_CONNUS
    corrections: Path = CORRECTIONS_CLASSIFICATION
    autoriser_http_local: bool = False  # tests uniquement
    verificateur: Path = SCRIPT_VERIFICATION


def _hote(url: str) -> str:
    return urlsplit(url).hostname or ""


def _url_publiee(cfg: ConfigSync, fichier: str) -> str | None:
    return cfg.url_publiee.rstrip("/") + "/" + fichier if cfg.url_publiee else None


def _lire_publie(
    transport: Transport, cfg: ConfigSync, params: Parametres
) -> dict[str, dict | None] | None:
    """Fichiers de la version publiée (None pour chacun si 404) ; None entier si l'état est inconnu."""
    if not cfg.url_publiee:
        return dict.fromkeys(FICHIERS_PUBLIES)
    try:
        return {
            f: lire_json_publie(transport, cast(str, _url_publiee(cfg, f)), params)
            for f in FICHIERS_PUBLIES
        }
    except ErreurReseau as exc:
        print(f"version publiée illisible : {exc}")
        return None


def _conclure_sync(entrees: EntreesDecision, cfg: ConfigSync) -> int:
    """ALG-12 : décide, écrit `decision.json`, code de sortie 1 seulement si la décision bloque."""
    decision = decider(entrees)
    chemin = cfg.dossier_travail / "decision.json"
    chemin.write_bytes(serialiser_decision(decision))
    print(f"décision : {decision.decision} ({chemin})")
    for r in decision.raisons:
        print(f"  {r['id']} {r['detail']}".rstrip())
    return 1 if decision.decision == "bloquer" else 0


def _entrees_en_echec(cfg: ConfigSync, precedent: dict | None, **rapports: Any) -> EntreesDecision:
    """Décision quand une étape n'a pas pu s'exécuter : les rapports manquants valent « échec »."""
    return EntreesDecision(
        lecture=rapports.get("lecture", RapportLecture(motif_echec="non_executee")),
        importation=rapports.get("importation", RapportImport()),
        reconciliation=rapports.get("reconciliation", RapportReconciliation(niveau="base")),
        export=rapports.get("export", RapportExport()),
        tests_ok=cfg.tests_ok,
        manifeste_courant=rapports.get("manifeste_courant", {}),
        telechargement=rapports.get("telechargement"),
        verification=rapports.get("verification"),
        manifeste_precedent=precedent,
        forcer=cfg.forcer,
        mode_sur=cfg.mode_sur,
    )


def _verification_independante(cfg: ConfigSync, archive: str) -> str:
    """ALG-14 : script indépendant, lancé dans son propre processus (aucun import du paquet etl)."""
    if not cfg.verificateur.is_file():
        return "echec"
    commande = [
        sys.executable, "-I", str(cfg.verificateur),
        "--archive", archive,
        "--export", str(cfg.sortie),
        "--sortie", str(cfg.dossier_travail / "verification.json"),
    ]  # fmt: skip
    code = subprocess.run(commande, check=False).returncode
    return "ok" if code == 0 else "echec"


def _noms_publies(publie: dict[str, dict | None]) -> tuple[dict, dict]:
    """Noms de la version publiée (ALG-09.8 : un nom qui change est signalé, jamais silencieux)."""
    groupes = {
        g["id"]: (g.get("libelle"), g.get("sigle"))
        for g in (publie.get("groupes.json") or {}).get("groupes", [])
    }
    deputes = {
        d["id"]: (d.get("nom"), d.get("prenom"), d.get("civilite"))
        for d in (publie.get("deputes.json") or {}).get("deputes", [])
    }
    return groupes, deputes


def _resoudre_noms(db_path: Path, archive_ref: str, publie: dict[str, dict | None]):
    """ALG-01 (profil référentiels) -> ALG-09 ; écrit les noms résolus. Renvoie (lecture, rapport)."""
    entrees, lecture = lire_source(archive_ref, profil=PROFIL_REFERENTIELS)
    if lecture.statut in ("echec", "partiel"):
        return lecture, None
    conn = sqlite3.connect(str(db_path))
    try:
        groupes_ref, deputes_ref = lire_references_noms(conn)
        anciens_g, anciens_d = _noms_publies(publie)
        resolution = resoudre_noms(entrees, groupes_ref, deputes_ref, anciens_g, anciens_d)
        ecrire_noms(conn, resolution)
        conn.commit()
    finally:
        conn.close()
    return lecture, resolution.rapport


def _lire_json_local(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def run_sync(
    cfg: ConfigSync,
    transport: Transport | None = None,
    params_scrutins: Parametres = PARAMETRES_SCRUTINS,
    params_referentiels: Parametres = PARAMETRES_REFERENTIELS,
    attendre: Callable[[float], None] = time.sleep,
) -> int:
    """Enchaîne ALG-13, 01, 07, 05, 09, 11, 14 et 12 ; écrit `decision.json` et l'artefact exporté.

    La base est reconstruite à chaque exécution (décision du 2026-11-18). Code de sortie : 0 si la
    décision est `rien_a_faire`, `publier` ou `attente_validation` ; 1 si elle bloque ; 2 si une
    entrée de configuration est illisible. Rien n'est déployé ici : le déploiement est un travail
    distinct qui consulte `decision.json` (voir `run_autoriser`).
    """
    transport = transport or TransportHttp()
    travail = cfg.dossier_travail
    travail.mkdir(parents=True, exist_ok=True)
    try:
        connus = charger_ecarts_connus(cfg.ecarts_connus)
        liste_corrections = charger_corrections(cfg.corrections)
    except (ErreurEcartsConnus, ErreurCorrections) as exc:
        print(f"entrée illisible : {exc}")
        return 2

    # ALG-12.1 : l'état publié (manifeste, meta, qualité, noms) sert à décider et à comparer
    publie = _lire_publie(transport, cfg, params_scrutins)
    if publie is None:
        echec = RapportTelechargement(url_demandee=cfg.url_publiee, cause_echec="publie_inconnu")
        return _conclure_sync(_entrees_en_echec(cfg, None, telechargement=echec), cfg)
    precedent = publie["manifeste.json"]

    # ALG-13 : archive des scrutins, puis référentiels de noms (profil propre)
    hotes = {_hote(cfg.url_scrutins), _hote(cfg.url_referentiels)}
    if cfg.url_publiee:
        hotes.add(_hote(cfg.url_publiee))
    hotes_autorises = sorted(hotes - {""})
    horloge = time.monotonic
    tele = telecharger(
        transport, StockageFichiers(travail / "archives"), cfg.url_scrutins, hotes_autorises,
        _url_publiee(cfg, "meta.json"), _horloge().isoformat(), attendre, horloge,
        params_scrutins, cfg.autoriser_http_local,
    )  # fmt: skip
    print(f"scrutins : {tele.statut} {tele.cause_echec or ''} {tele.sha256}".rstrip())
    if tele.statut == "echec":
        return _conclure_sync(_entrees_en_echec(cfg, precedent, telechargement=tele), cfg)
    ref = telecharger(
        transport, StockageFichiers(travail / "referentiels"), cfg.url_referentiels,
        hotes_autorises, None, _horloge().isoformat(), attendre, horloge,
        params_referentiels, cfg.autoriser_http_local,
    )  # fmt: skip
    print(f"référentiels : {ref.statut} {ref.cause_echec or ''} {ref.sha256}".rstrip())
    if ref.statut == "echec":
        return _conclure_sync(_entrees_en_echec(cfg, precedent, telechargement=ref), cfg)

    # ALG-12.1 : « rien à faire » si TOUTES les entrées sont identiques à celles de la version publiée
    entrees = entrees_composites(tele.sha256, ref.sha256)
    if not doit_traiter(entrees, precedent, cfg.forcer):
        courant = {
            "empreinte_entrees": empreinte_entrees(entrees),
            "donnees_sha256": (precedent or {}).get("donnees_sha256", ""),
        }
        return _conclure_sync(
            _entrees_en_echec(cfg, precedent, telechargement=tele, manifeste_courant=courant), cfg
        )

    # ALG-01, 02, 04, 06, 07 : import dans une base neuve
    base = travail / "voteapol.db"
    base.unlink(missing_ok=True)
    conn = sqlite3.connect(base)
    appliquer_migrations(conn)
    conn.close()
    try:
        rapport_import, lecture, _, _ = executer_import(
            tele.chemin, str(base), _horloge().isoformat(), journal_dir=travail / "journaux",
            source_url=tele.url_finale,
        )  # fmt: skip
    except ErreurBase as exc:
        print(f"base inutilisable : {exc.motif}")
        return _conclure_sync(_entrees_en_echec(cfg, precedent, telechargement=tele), cfg)
    print(json.dumps(_resume(rapport_import), indent=2, ensure_ascii=False))
    if rapport_import.statut != "termine":
        return _conclure_sync(
            _entrees_en_echec(
                cfg, precedent, telechargement=tele, lecture=lecture, importation=rapport_import
            ),
            cfg,
        )

    # ALG-09 : noms des groupes et des députés (sans quoi les libellés restent « non résolus »)
    lecture_ref, rapport_noms = _resoudre_noms(base, ref.chemin, publie)
    if rapport_noms is None:
        return _conclure_sync(
            _entrees_en_echec(
                cfg, precedent, telechargement=ref, lecture=lecture_ref, importation=rapport_import
            ),
            cfg,
        )
    print(
        f"noms : {rapport_noms.groupes_resolus}/{rapport_noms.groupes_references} groupes, "
        f"{rapport_noms.deputes_resolus}/{rapport_noms.deputes_references} députés, "
        f"{len(rapport_noms.noms_modifies)} modifié(s)"
    )

    # ALG-05 (base) puis ALG-11 : l'export est l'artefact de cette exécution
    rapport_export, reconciliation, publication_ko = executer_export(
        str(base), str(cfg.sortie), connus, liste_corrections, precedent,
        referentiels_sha256=ref.sha256,
        type_empreinte=rapport_import.type_empreinte or "non_renseigne",
    )  # fmt: skip
    _afficher_reconciliation(reconciliation)
    rapports = {
        "telechargement": tele, "lecture": lecture, "importation": rapport_import,
        "reconciliation": reconciliation,
    }  # fmt: skip
    if publication_ko or rapport_export.statut != "ok":
        return _conclure_sync(
            _entrees_en_echec(cfg, precedent, export=rapport_export, **rapports), cfg
        )

    # ALG-14 : vérification indépendante sur l'archive brute et les fichiers exportés
    verification = _verification_independante(cfg, tele.chemin)
    print(f"vérification indépendante : {verification}")

    # ALG-12 : décision (diff, noms modifiés, groupes et indéterminés comparés à la version publiée)
    manifeste = _lire_json_local(cfg.sortie / "manifeste.json")
    qualite = _lire_json_local(cfg.sortie / "qualite.json")
    meta_publie = publie["meta.json"] or {}
    qualite_publiee = publie["qualite.json"] or {}
    indetermines_publies = (qualite_publiee.get("classification") or {}).get("indetermine")
    return _conclure_sync(
        EntreesDecision(
            lecture=lecture,
            importation=rapport_import,
            reconciliation=reconciliation,
            export=rapport_export,
            tests_ok=cfg.tests_ok,
            manifeste_courant=manifeste,
            telechargement=tele,
            verification=verification,
            manifeste_precedent=precedent,
            diff=calculer_diff(manifeste["scrutins"], precedent),
            noms_modifies=rapport_noms.noms_modifies,
            nombre_groupes_precedent=meta_publie.get("nombre_groupes"),
            indetermines_precedent=indetermines_publies,
            indetermines_courant=qualite["classification"]["indetermine"],
            forcer=cfg.forcer,
            mode_sur=cfg.mode_sur,
        ),
        cfg,
    )


# --- autorisation et contrôle du déploiement (ALG-12.8 et 12.9) -------------------------------------


def _donnees_sha256(dossier: Path) -> str:
    """Recalcule `donnees_sha256` (ALG-11.8) : tous les fichiers sauf manifeste.json et meta.json."""
    # tri sur la chaîne du chemin (comme ALG-11) : trier des `Path` donnerait un autre ordre
    fichiers = {p.relative_to(dossier).as_posix(): p for p in dossier.rglob("*") if p.is_file()}
    lignes = [
        f"{relatif}\t{hashlib.sha256(fichiers[relatif].read_bytes()).hexdigest()}\n"
        for relatif in sorted(fichiers)
        if relatif not in ("manifeste.json", "meta.json")
    ]
    return hashlib.sha256("".join(lignes).encode("utf-8")).hexdigest()


def run_autoriser(decision_path: str | Path, data_dir: str | Path, approuvee: bool = False) -> int:
    """ALG-12.8 : le déploiement ne publie que l'artefact que la décision a examiné.

    Contrôle que `decision.json` n'a pas été altéré (son `rapport_sha256` est recalculé), que les
    fichiers à déployer sont ceux que la décision désigne (`donnees_sha256` recalculé sur disque,
    `empreinte_entrees` du manifeste), puis applique `deploiement_autorise`. Code 0 : autorisé.
    """
    try:
        brut = json.loads(Path(decision_path).read_text(encoding="utf-8"))
        decision = DecisionPublication(
            brut["decision"], tuple(brut["raisons"]), brut["diff"], brut["donnees_sha256"],
            brut["empreinte_entrees"], brut["rapport_sha256"],
        )  # fmt: skip
        manifeste = _lire_json_local(Path(data_dir) / "manifeste.json")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"refusé : décision ou artefact illisible ({exc})")
        return 1
    contenu = {
        "decision": decision.decision,
        "raisons": list(decision.raisons),
        "diff": decision.diff,
        "donnees_sha256": decision.donnees_sha256,
        "empreinte_entrees": decision.empreinte_entrees,
    }
    recalcule = hashlib.sha256(serialiser(contenu)).hexdigest()
    artefact_conforme = (
        manifeste.get("donnees_sha256") == decision.donnees_sha256
        and manifeste.get("empreinte_entrees") == decision.empreinte_entrees
        and _donnees_sha256(Path(data_dir)) == decision.donnees_sha256
    )
    if not artefact_conforme:
        print("refusé : les fichiers à déployer ne sont pas ceux que la décision a examinés")
        return 1
    if not deploiement_autorise(decision, approuvee, recalcule):
        print(f"refusé : décision « {decision.decision} », approbation : {approuvee}")
        return 1
    print(f"autorisé : décision « {decision.decision} »")
    return 0


def run_verifier_deploiement(
    url_publiee: str,
    data_dir: str | Path,
    transport: Transport | None = None,
    params: Parametres = PARAMETRES_SCRUTINS,
) -> int:
    """ALG-12.9 : relit `meta.json` en ligne et le compare à celui qui vient d'être déployé."""
    local = _lire_json_local(Path(data_dir) / "meta.json")
    try:
        en_ligne = lire_json_publie(
            transport or TransportHttp(), url_publiee.rstrip("/") + "/meta.json", params
        )
    except ErreurReseau as exc:
        print(f"déploiement non confirmé : {exc}")
        return 1
    erreurs = verifier_deploiement(en_ligne, local["archive_sha256"], local["nombre_scrutins"])
    for e in erreurs:
        print(f"déploiement non confirmé : {e}")
    if not erreurs:
        print("déploiement confirmé")
    return 1 if erreurs else 0
