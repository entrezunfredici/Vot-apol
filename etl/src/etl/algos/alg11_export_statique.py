"""ALG-11 : Export statique (fichiers JSON, déterminisme, limites Cloudflare).

Spécification : docs/algorithmes/ALG-11-export-statique.md (statut « Validé », version 2).
Fonction pure : elle reçoit les scrutins (un `LotScrutin` par scrutin, lus dans la base par
etl/io/db.py) et renvoie les octets de chaque fichier public ; l'écriture et la publication du
répertoire sont dans etl/io/fs.py. Aucune heure n'est lue : tout vient des entrées.
Chaque bloc de code est précédé de « # ALG-11.k : <résumé> ».
"""

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ..models import (
    POSITIONS_VOTE,
    ContexteExport,
    LigneGroupeScrutin,
    LigneVoteSelection,
    LotScrutin,
    ParametresExport,
    RapportExport,
    ReferentielsExport,
)
from .alg03_position_majoritaire import ErreurDonnee, calculer_position
from .alg06_mises_au_point import corriger_effectifs
from .alg08_classification import classifier
from .alg10_indicateurs_groupe import calculer_indicateurs, libelles_tranches
from .alg11_schemas import COLONNES_GROUPE, valider

SCHEMA = "v1"
URL_OFFICIELLE = "https://www.assemblee-nationale.fr/dyn/17/scrutins/{numero}"
_ORDRE_POSITION = {p: i for i, p in enumerate(POSITIONS_VOTE)}
_RECONCILIATION_ADMISE = ("ok", "ecarts_connus")
MAX_MODIFICATIONS_DETAILLEES = 200  # qualite.json : listes de scrutins plafonnées (compte exact)


def serialiser(valeur: Any) -> bytes:
    """ALG-11.9 : JSON, clés triées, sans espace, UTF-8 sans BOM, `\\n` final, NaN refusé."""
    texte = json.dumps(
        valeur, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return (texte + "\n").encode("utf-8")


def _sha256(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def empreinte_entrees(entrees: dict[str, Any]) -> str:
    """Empreinte composite des entrées (ALG-12.1) : tout ce qui peut changer les données publiées."""
    return _sha256(serialiser(entrees))


def lien_officiel(numero: int) -> str:
    return URL_OFFICIELLE.format(numero=numero)


def empreinte_chiffres(document: dict[str, Any]) -> str:
    """Empreinte des chiffres officiels publiés d'un scrutin (fiche ALG-12, « Manifeste »).

    Résultat, totaux, compteurs de chaque groupe et liste complète des votes : un changement de
    cette empreinte signifie qu'un chiffre officiel publié a changé.
    """
    compteurs = [
        {k: g[k] for k in ("rang", "groupe_id", "membres", "pour", "contre", "abstentions", "non_votants")}
        for g in document["groupes"]
    ]
    return _sha256(
        serialiser(
            {
                "resultat": document["resultat"],
                "totaux": {k: v for k, v in document["totaux"].items() if k != "sans_vote_enregistre"},
                "groupes": compteurs,
                "votes": document["votes"],
            }
        )
    )


def calculer_diff(
    scrutins_courants: dict[str, dict[str, str]], precedent: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Différences avec le manifeste publié (ALG-12.3) ; None s'il n'y a pas de publication."""
    if precedent is None:
        return None
    avant = precedent.get("scrutins", {})
    nouveaux = sorted(set(scrutins_courants) - set(avant))
    supprimes = sorted(set(avant) - set(scrutins_courants))
    chiffres, autres = [], []
    for sid in sorted(set(scrutins_courants) & set(avant)):
        a, c = avant[sid], scrutins_courants[sid]
        if a.get("empreinte_chiffres") != c["empreinte_chiffres"]:
            chiffres.append(sid)
        elif a.get("source_hash") != c["source_hash"]:
            autres.append(sid)
    return {
        "nouveaux": len(nouveaux),
        "supprimes": supprimes[:MAX_MODIFICATIONS_DETAILLEES],
        "nombre_supprimes": len(supprimes),
        "modifies_chiffres": chiffres[:MAX_MODIFICATIONS_DETAILLEES],
        "nombre_modifies_chiffres": len(chiffres),
        "modifies_autres": autres[:MAX_MODIFICATIONS_DETAILLEES],
        "nombre_modifies_autres": len(autres),
    }


@dataclass
class _Cumuls:
    """Ce qui s'accumule scrutin après scrutin pour construire les fichiers transversaux."""

    index_par_mois: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    manifeste: dict[str, dict[str, str]] = field(default_factory=dict)
    lignes_groupes: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    lignes_stats: list[LigneGroupeScrutin] = field(default_factory=list)
    votes_stats: list[LigneVoteSelection] = field(default_factory=list)
    deputes_vus: set[str] = field(default_factory=set)
    groupes_vus: Counter = field(default_factory=Counter)
    categories: Counter = field(default_factory=Counter)
    a_verifier: int = 0
    echantillon: dict[str, LotScrutin] = field(default_factory=dict)


def _position_dict(p) -> dict[str, Any]:
    return {
        "position": p.position,
        "raison_absence": p.raison_absence,
        "exprimes": p.exprimes,
        "m": p.effectif_majoritaire,
        "majorite_absolue": p.majorite_absolue,
    }


def _mise_au_point_dict(m) -> dict[str, Any]:
    return {
        "depute_id": m.depute_id,
        "groupe_rang": m.groupe_rang,
        "groupe_id": m.groupe_id,
        "position_initiale": m.position_initiale,
        "position_declaree": m.position_declaree,
        "par_delegation": m.par_delegation,
        "statut": m.statut_rattachement or ("rattachee" if m.groupe_rang is not None else "introuvable"),
        "effet": m.effet,
    }


def construire_document(lot: LotScrutin, contexte: ContexteExport) -> tuple[dict, Any]:
    """ALG-11.3 : document d'un scrutin ; renvoie (document, classification).

    Chaque valeur dérivée vient de sa fiche : catégorie (ALG-08), position majoritaire (ALG-03),
    effectifs corrigés (ALG-06 B). `position_majoritaire_source` n'est jamais exporté.
    """
    s, t = lot.scrutin, lot.totaux
    classification = classifier(s.id, s.type_vote_code, s.titre, contexte.corrections)
    corrections = {c.rang: c for c in corriger_effectifs(lot)}

    # ALG-11.5 : groupes d'un scrutin par effectif décroissant, puis identifiant, puis rang
    groupes = []
    sans_vote_total: int | None = 0
    for g in sorted(
        lot.groupes, key=lambda g: (-g.membres, g.groupe_id is None, g.groupe_id or "", g.rang)
    ):
        identifie = g.groupe_id is not None
        if identifie:
            sans_vote = g.membres - (g.pour + g.contre + g.abstentions + g.non_votants)
            if sans_vote < 0:
                raise ErreurDonnee(f"{s.id} rang {g.rang} : E + N > membres")
            position = calculer_position(g.pour, g.contre, g.abstentions, g.membres)
            correction = corrections.get(g.rang)
            if sans_vote_total is not None:
                sans_vote_total += sans_vote
        else:
            # groupe non identifié : chiffres officiels conservés, aucun indicateur
            sans_vote, position, correction = None, None, None
            sans_vote_total = None
        groupes.append(
            {
                "rang": g.rang,
                "groupe_id": g.groupe_id,
                "ventilation_disponible": identifie,
                "membres": g.membres,
                "pour": g.pour,
                "contre": g.contre,
                "abstentions": g.abstentions,
                "non_votants": g.non_votants,
                "sans_vote_enregistre": sans_vote,
                "position_majoritaire": _position_dict(position) if position else None,
                "correction_mise_au_point": (
                    {
                        "pour_corrige": correction.pour_corrige,
                        "contre_corrige": correction.contre_corrige,
                        "abstentions_corrigees": correction.abstentions_corrigees,
                        "position_officielle": correction.position_officielle,
                        "position_corrigee": correction.position_corrigee,
                        "raison_absence_corrigee": correction.raison_absence_corrigee,
                        "change_position_majoritaire": correction.change_position_majoritaire,
                        "nb_mises_au_point": correction.nb_mises_au_point,
                    }
                    if correction
                    else None
                ),
            }
        )

    # ALG-11.5 : votes par rang du groupe, position, identifiant du député
    votes = [
        [v.depute_id, v.groupe_rang, v.position, v.par_delegation, v.cause]
        for v in sorted(
            lot.votes,
            key=lambda v: (v.groupe_rang, _ORDRE_POSITION.get(v.position, 99), v.depute_id),
        )
    ]
    mises = [m for m in lot.mises_au_point if m.origine == "mise_au_point"]
    dysfonctionnements = [m for m in lot.mises_au_point if m.origine == "dysfonctionnement"]
    document = {
        "id": s.id,
        "numero": s.numero,
        "date": s.date_scrutin,
        "titre": s.titre,
        "type_vote": {"code": s.type_vote_code, "libelle": s.type_vote_libelle},
        "resultat": s.resultat_code,
        "categorie": {
            "valeur": classification.categorie,
            "methode": classification.methode,
            "confiance": classification.confiance,
            "a_verifier": classification.a_verifier,
        },
        "source": {
            "fichier": f"json/{s.id}.json",
            "sha256": s.source_hash,
            "archive_sha256": contexte.archive_sha256,
            "lien_officiel": lien_officiel(s.numero),
        },
        "totaux": {
            "pour": t.pour,
            "contre": t.contre,
            "abstentions": t.abstentions,
            "non_votants": t.non_votants,
            "suffrages_exprimes": t.suffrages_exprimes,
            "nombre_votants": t.nombre_votants,
            "sans_vote_enregistre": sans_vote_total,
        },
        "groupes": groupes,
        "votes": votes,
        "mises_au_point": [_mise_au_point_dict(m) for m in sorted(mises, key=lambda m: m.depute_id)],
        "dysfonctionnements": [
            _mise_au_point_dict(m) for m in sorted(dysfonctionnements, key=lambda m: m.depute_id)
        ],
    }
    return document, classification


def _cumuler(cumuls: _Cumuls, lot: LotScrutin, document: dict, classification, serie: int,
             params: ParametresExport) -> bytes:  # fmt: skip
    s = lot.scrutin
    cat = classification.categorie
    cumuls.categories[cat] += 1
    cumuls.a_verifier += int(classification.a_verifier)
    # ALG-11.6 : index par mois de date_scrutin
    cumuls.index_par_mois[s.date_scrutin[:7]].append(
        {
            "id": s.id,
            "numero": s.numero,
            "date": s.date_scrutin,
            "titre": s.titre,
            "categorie": {
                "valeur": cat,
                "methode": classification.methode,
                "a_verifier": classification.a_verifier,
            },
            "resultat": s.resultat_code,
            "totaux": {k: document["totaux"][k] for k in (
                "pour", "contre", "abstentions", "non_votants", "suffrages_exprimes",
                "nombre_votants")},  # fmt: skip
        }
    )
    octets = serialiser(document)
    cumuls.manifeste[s.id] = {
        "source_hash": s.source_hash,
        "empreinte_chiffres": empreinte_chiffres(document),
    }
    for g in document["groupes"]:
        if g["groupe_id"] is not None:
            cumuls.groupes_vus[g["groupe_id"]] += 1
            pm = g["position_majoritaire"]
            # ligne compacte, dans l'ordre de COLONNES_GROUPE (position majoritaire à plat)
            cumuls.lignes_groupes[g["groupe_id"]].append(
                [
                    s.id, s.numero, s.date_scrutin, cat, g["membres"], g["pour"], g["contre"],
                    g["abstentions"], g["non_votants"], g["sans_vote_enregistre"],
                    pm["position"], pm["raison_absence"], pm["exprimes"], pm["m"],
                    pm["majorite_absolue"],
                ]
            )  # fmt: skip
    cumuls.deputes_vus.update(v.depute_id for v in lot.votes)
    cumuls.deputes_vus.update(m.depute_id for m in lot.mises_au_point)
    # lignes pour ALG-10
    for g in lot.groupes:
        cumuls.lignes_stats.append(
            LigneGroupeScrutin(s.id, s.date_scrutin, cat, s.resultat_code, s.type_vote_code,
                               g.groupe_id, g.membres, g.pour, g.contre, g.abstentions,
                               g.non_votants)  # fmt: skip
        )
    cumuls.votes_stats.extend(
        LigneVoteSelection(s.id, v.groupe_id, v.depute_id, v.position) for v in lot.votes
    )
    # ALG-11.13 : un scrutin sur `pas_echantillon` est conservé pour la relecture
    if serie % params.pas_echantillon == 0:
        cumuls.echantillon[s.id] = lot
    return octets


def _stats(cumuls: _Cumuls, referentiels: ReferentielsExport, params: ParametresExport) -> dict:
    """ALG-11.7 : ALG-10 pour toutes les sélections, par catégorie et par année."""
    libelles = {g: lib for g, (lib, _) in referentiels.groupes.items()}
    selections: list[tuple[str, str, set[str] | None]] = [("toutes", "tous les scrutins", None)]
    par_cat: dict[str, set[str]] = defaultdict(set)
    par_annee: dict[str, set[str]] = defaultdict(set)
    for lg in cumuls.lignes_stats:
        par_cat[lg.categorie].add(lg.scrutin_id)
        par_annee[lg.date_scrutin[:4]].add(lg.scrutin_id)
    selections += [(f"categorie:{c}", f"catégorie {c}", ids) for c, ids in sorted(par_cat.items())]
    selections += [(f"annee:{a}", f"année {a}", ids) for a, ids in sorted(par_annee.items())]
    resultat = []
    for sid, filtres, ids in selections:
        if ids is None:
            lignes, votes = cumuls.lignes_stats, cumuls.votes_stats
        else:
            lignes = [lg for lg in cumuls.lignes_stats if lg.scrutin_id in ids]
            votes = [v for v in cumuls.votes_stats if v.scrutin_id in ids]
        indicateurs = calculer_indicateurs(lignes, votes, filtres, params.bornes, libelles)
        resultat.append(
            {
                "id": sid,
                "filtres": filtres,
                "nombre_scrutins": len({lg.scrutin_id for lg in lignes}),
                "groupes": [
                    {
                        "groupe_id": i.groupe_id,
                        "nb_scrutins": i.nb_scrutins,
                        "nb_scrutins_exclus_groupe_non_identifie": i.nb_scrutins_exclus_groupe_non_identifie,
                        "membres_scrutins": i.membres_scrutins,
                        "personnes_exprimees": i.personnes_exprimees,
                        "personnes_avec_vote": i.personnes_avec_vote,
                        "pour": i.pour,
                        "contre": i.contre,
                        "abstentions": i.abstentions,
                        "non_votants": i.non_votants,
                        "sans_vote_enregistre": i.sans_vote_enregistre,
                        "exprimes": i.exprimes,
                        "scrutins_par_position_majoritaire": i.scrutins_par_position_majoritaire,
                        "repartition_part_majoritaire": list(i.repartition_part_majoritaire),
                    }
                    for i in indicateurs
                ],
            }
        )
    return {
        "bornes": list(params.bornes),
        "libelles_tranches": list(libelles_tranches(params.bornes)),
        "selections": resultat,
    }


def _type_de(chemin: str) -> str:
    """Famille d'un fichier pour le rapport : `dossier/` ou nom sans extension."""
    return chemin.split("/", 1)[0] + "/" if "/" in chemin else chemin.removesuffix(".json")


def exporter(
    scrutins: Iterable[LotScrutin],
    referentiels: ReferentielsExport,
    contexte: ContexteExport,
    params: ParametresExport = ParametresExport(),
) -> tuple[dict[str, bytes], RapportExport]:
    """Construit tous les fichiers publics ; `echec` si quoi que ce soit n'est pas valide.

    `scrutins` : une liste (triée ici par numéro) ou un flux déjà trié par numéro croissant (le
    chargeur de la base), pour ne pas tout garder en mémoire.

    Renvoie (fichiers, rapport) : les fichiers (chemin relatif à `/data/v1/` -> octets) ne sont à
    publier que si `rapport.statut == "ok"` (ALG-11.14, fait par etl/io/fs.py).
    """
    rapport = RapportExport()

    def echec(cause: str, detail: str = "") -> tuple[dict[str, bytes], RapportExport]:
        rapport.statut, rapport.cause_echec, rapport.detail_echec = "echec", cause, detail
        return {}, rapport

    # ALG-11.1 : on n'exporte jamais une base dont les totaux ne se recoupent pas
    if contexte.statut_reconciliation not in _RECONCILIATION_ADMISE:
        return echec("reconciliation_refusee", contexte.statut_reconciliation)

    fichiers: dict[str, bytes] = {}
    cumuls = _Cumuls()
    serie = 0
    try:
        # ALG-11.3 et 5 : scrutins par numéro croissant, un document chacun
        dernier = 0
        flux = sorted(scrutins, key=lambda lot: lot.scrutin.numero) if isinstance(scrutins, list) else scrutins
        for lot in flux:
            if lot.scrutin.numero <= dernier:
                return echec("ordre_invalide", f"{lot.scrutin.id} après le numéro {dernier}")
            dernier = lot.scrutin.numero
            serie += 1
            document, classification = construire_document(lot, contexte)
            fichiers[f"scrutins/{lot.scrutin.id}.json"] = _cumuler(
                cumuls, lot, document, classification, serie, params
            )
    except ErreurDonnee as exc:
        return echec("erreur_donnee", str(exc))
    # ALG-11 : on ne publie jamais un site vide
    if serie == 0:
        return echec("aucun_scrutin")
    rapport.nombre_scrutins = serie

    # ALG-11.6 : index par mois (pas de fichier pour un mois sans scrutin)
    fragments = []
    for mois in sorted(cumuls.index_par_mois):
        lignes = sorted(cumuls.index_par_mois[mois], key=lambda x: x["numero"])
        fichiers[f"scrutins-index/{mois}.json"] = serialiser({"mois": mois, "scrutins": lignes})
        fragments.append(
            {"mois": mois, "nombre_scrutins": len(lignes), "fichier": f"scrutins-index/{mois}.json"}
        )
    fichiers["scrutins-index.json"] = serialiser({"fragments": fragments})

    # ALG-11.4 et 5 : groupes (libellé puis identifiant ; non résolus à la fin), députés
    def nom_groupe(gid: str) -> tuple[bool, str, str]:
        lib = referentiels.groupes.get(gid, (None, None))[0]
        return (lib is None, (lib or "").casefold(), gid)

    ids_groupes = sorted(cumuls.groupes_vus, key=nom_groupe)
    rapport.nombre_groupes = len(ids_groupes)
    fichiers["groupes.json"] = serialiser(
        {
            "groupes": [
                {
                    "id": gid,
                    "libelle": referentiels.groupes.get(gid, (None, None))[0],
                    "sigle": referentiels.groupes.get(gid, (None, None))[1],
                    "nombre_scrutins": cumuls.groupes_vus[gid],
                }
                for gid in ids_groupes
            ]
        }
    )
    for gid in ids_groupes:
        lib, sigle = referentiels.groupes.get(gid, (None, None))
        lignes = sorted(cumuls.lignes_groupes[gid], key=lambda x: x[1])  # par numéro de scrutin
        fichiers[f"groupes/{gid}.json"] = serialiser(
            {
                "groupe_id": gid,
                "libelle": lib,
                "sigle": sigle,
                "colonnes": list(COLONNES_GROUPE),
                "scrutins": lignes,
            }
        )
    fichiers["deputes.json"] = serialiser(
        {
            "deputes": [
                {
                    "id": did,
                    "nom": referentiels.deputes.get(did, (None, None, None))[0],
                    "prenom": referentiels.deputes.get(did, (None, None, None))[1],
                    "civilite": referentiels.deputes.get(did, (None, None, None))[2],
                }
                for did in sorted(cumuls.deputes_vus)
            ]
        }
    )

    # ALG-11.7 : indicateurs d'ALG-10
    fichiers["stats.json"] = serialiser(_stats(cumuls, referentiels, params))

    # ALG-11.8 : qualité (différence avec la version publiée), puis manifeste et meta ;
    # aucune heure lue sur l'horloge : `donnees_du` vient de la base
    diff = calculer_diff(cumuls.manifeste, contexte.manifeste_precedent)
    fichiers["qualite.json"] = serialiser(
        {
            "schema": SCHEMA,
            "statut_reconciliation": contexte.statut_reconciliation,
            "nombre_scrutins": serie,
            "archive_sha256": contexte.archive_sha256,
            "donnees_du": contexte.donnees_du,
            "ecarts_connus": contexte.ecarts_connus,
            "classification": {
                "par_categorie": dict(sorted(cumuls.categories.items())),
                "a_verifier": cumuls.a_verifier,
                "indetermine": cumuls.categories.get("indetermine", 0),
            },
            "noms_non_resolus": {
                "groupes": sum(1 for g in ids_groupes if referentiels.groupes.get(g, (None,))[0] is None),
                "deputes": sum(1 for d in cumuls.deputes_vus if referentiels.deputes.get(d, (None,))[0] is None),
            },
            "modifications": diff,
        }
    )
    # empreinte composite des entrées (ALG-12.1) : tout ce qui peut changer les données publiées
    entrees = {
        **contexte.entrees,
        "archive_sha256": contexte.archive_sha256,
        "version_etl": contexte.version_etl,
        "version_regles_classification": contexte.version_regles_classification,
    }
    empreinte_composite = empreinte_entrees(entrees)
    # donnees_sha256 : empreinte de tous les fichiers sauf manifeste.json et meta.json
    lignes_donnees = "".join(f"{c}\t{_sha256(o)}\n" for c, o in sorted(fichiers.items()))
    donnees_sha256 = _sha256(lignes_donnees.encode("utf-8"))
    fichiers["manifeste.json"] = serialiser(
        {
            "schema": SCHEMA,
            "entrees": entrees,
            "empreinte_entrees": empreinte_composite,
            "donnees_sha256": donnees_sha256,
            "scrutins": cumuls.manifeste,
        }
    )
    dates = sorted(lg.date_scrutin for lg in cumuls.lignes_stats)
    rapport.donnees_sha256 = donnees_sha256
    rapport.version_donnees = donnees_sha256[:16]
    fichiers["meta.json"] = serialiser(
        {
            "schema": SCHEMA,
            "nombre_scrutins": serie,
            "nombre_groupes": rapport.nombre_groupes,
            "premiere_date": dates[0],
            "derniere_date": dates[-1],
            "donnees_du": contexte.donnees_du,
            "version_donnees": rapport.version_donnees,
            "archive_sha256": contexte.archive_sha256,
            "type_empreinte": contexte.type_empreinte,
            "version_etl": contexte.version_etl,
            "version_regles_classification": contexte.version_regles_classification,
        }
    )

    # ALG-11.10 : chaque fichier se relit en JSON et respecte son schéma
    for chemin in sorted(fichiers):
        try:
            document = json.loads(fichiers[chemin].decode("utf-8"))
        except ValueError as exc:
            return echec("json_invalide", f"{chemin} : {exc}")
        erreurs = valider(chemin, document)
        if erreurs:
            return echec("schema_invalide", "; ".join(erreurs[:5]))

    # ALG-11.11 : limites de l'hébergement (échec plutôt qu'un déploiement refusé)
    rapport.nombre_fichiers = len(fichiers)
    rapport.octets_total = sum(len(o) for o in fichiers.values())
    plus_gros = max(fichiers, key=lambda c: len(fichiers[c]))
    rapport.plus_gros_fichier = (plus_gros, len(fichiers[plus_gros]))
    rapport.fichiers_par_type = dict(sorted(Counter(_type_de(c) for c in fichiers).items()))
    if rapport.nombre_fichiers > params.max_fichiers_echec:
        return echec("trop_de_fichiers", f"{rapport.nombre_fichiers} > {params.max_fichiers_echec}")
    if rapport.plus_gros_fichier[1] > params.max_octets_fichier_echec:
        return echec("fichier_trop_gros", f"{plus_gros} : {rapport.plus_gros_fichier[1]} octets")
    if rapport.nombre_fichiers > params.max_fichiers_avertissement:
        rapport.avertissements.append(f"nombre_fichiers_eleve : {rapport.nombre_fichiers}")
    # l'avertissement de taille vise les fichiers chargés par le navigateur : `manifeste.json`
    # (une empreinte par scrutin, lu seulement par le garde-fou de déploiement) en est exclu
    pour_le_site = [c for c in fichiers if c != "manifeste.json"]
    plus_gros_site = max(pour_le_site, key=lambda c: len(fichiers[c]))
    if len(fichiers[plus_gros_site]) > params.max_octets_fichier_avertissement:
        rapport.avertissements.append(f"fichier_volumineux : {plus_gros_site}")

    # ALG-11.12 : intégrité des références, meta égal aux comptes de la base
    erreur = _verifier_references(fichiers, contexte)
    if erreur:
        return echec("references_invalides", erreur)

    # ALG-11.13 : relecture d'un échantillon comparé aux lignes de la base
    erreur = _verifier_echantillon(fichiers, cumuls.echantillon)
    if erreur:
        return echec("echantillon_different", erreur)

    rapport.statut = "ok"
    return fichiers, rapport


def _verifier_references(fichiers: dict[str, bytes], contexte: ContexteExport) -> str | None:
    meta = json.loads(fichiers["meta.json"])
    if meta["nombre_scrutins"] != contexte.nombre_scrutins_base:
        return f"meta.nombre_scrutins {meta['nombre_scrutins']} ≠ base {contexte.nombre_scrutins_base}"
    groupes = {g["id"] for g in json.loads(fichiers["groupes.json"])["groupes"]}
    if meta["nombre_groupes"] != len(groupes):
        return "meta.nombre_groupes ≠ groupes.json"
    deputes = {d["id"] for d in json.loads(fichiers["deputes.json"])["deputes"]}
    for fragment in json.loads(fichiers["scrutins-index.json"])["fragments"]:
        if fragment["fichier"] not in fichiers:
            return f"fragment sans fichier : {fragment['fichier']}"
        for ligne in json.loads(fichiers[fragment["fichier"]])["scrutins"]:
            if f"scrutins/{ligne['id']}.json" not in fichiers:
                return f"ligne d'index sans fichier : {ligne['id']}"
    for chemin, octets in fichiers.items():
        if not chemin.startswith("scrutins/"):
            continue
        doc = json.loads(octets)
        for g in doc["groupes"]:
            if g["groupe_id"] is not None and g["groupe_id"] not in groupes:
                return f"{chemin} : groupe inconnu {g['groupe_id']}"
        for v in doc["votes"]:
            if v[0] not in deputes:
                return f"{chemin} : député inconnu {v[0]}"
        for m in doc["mises_au_point"] + doc["dysfonctionnements"]:
            if m["depute_id"] not in deputes:
                return f"{chemin} : député inconnu {m['depute_id']}"
    return None


def _verifier_echantillon(fichiers: dict[str, bytes], echantillon: dict[str, LotScrutin]) -> str | None:
    """Relit les fichiers produits et compare chaque chiffre aux lignes d'entrée."""
    for sid, lot in sorted(echantillon.items()):
        doc = json.loads(fichiers[f"scrutins/{sid}.json"])
        t = lot.totaux
        attendus = {
            "pour": t.pour, "contre": t.contre, "abstentions": t.abstentions,
            "non_votants": t.non_votants, "suffrages_exprimes": t.suffrages_exprimes,
            "nombre_votants": t.nombre_votants,
        }  # fmt: skip
        for cle, attendu in attendus.items():
            if doc["totaux"][cle] != attendu:
                return f"{sid} totaux.{cle} : {doc['totaux'][cle]} ≠ {attendu}"
        par_rang = {g["rang"]: g for g in doc["groupes"]}
        for g in lot.groupes:
            f = par_rang.get(g.rang)
            if f is None or (f["groupe_id"], f["membres"], f["pour"], f["contre"], f["abstentions"],
                             f["non_votants"]) != (g.groupe_id, g.membres, g.pour, g.contre,
                                                   g.abstentions, g.non_votants):  # fmt: skip
                return f"{sid} groupe de rang {g.rang} différent"
        attendus_votes = sorted((v.depute_id, v.groupe_rang, v.position, v.par_delegation, v.cause) for v in lot.votes)
        if sorted(tuple(v) for v in doc["votes"]) != attendus_votes:
            return f"{sid} votes différents"
        if len(doc["mises_au_point"]) + len(doc["dysfonctionnements"]) != len(lot.mises_au_point):
            return f"{sid} mises au point différentes"
    return None
