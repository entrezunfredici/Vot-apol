"""ALG-02 : Normalisation d'un scrutin (valeurs, collections, positions).

Spécification : docs/algorithmes/ALG-02-normalisation.md (statut « Validé », version 2).
Fonctions pures : le document JSON (sortie d'ALG-01) entre, un résultat typé sort.
Fonctions de base « # ALG-02.Nk » ; étapes d'assemblage « # ALG-02.k ».
Une valeur inattendue est signalée, jamais devinée ; un scrutin en erreur n'est jamais
renvoyé à moitié normalisé.
"""

import datetime
import re
import unicodedata
from typing import Any

from ..models import (
    Anomalie,
    GroupeNormalise,
    LigneCorrection,
    ResultatNormalisation,
    ScrutinNormalise,
    Votant,
)

MAX_ERREURS = 50  # ALG-02.23

XMLNS_ATTENDU = "http://schemas.assemblee-nationale.fr/referentiel"
XMLNS_XSI_ATTENDU = "http://www.w3.org/2001/XMLSchema-instance"

_ENTIER = re.compile(r"0|[1-9][0-9]*")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# Tables de vocabulaire fermées (fiche, « Tables de vocabulaire »)
TABLE_NOMINATIF = {
    "pours": "pour",
    "contres": "contre",
    "abstentions": "abstention",
    "nonVotants": "non_votant",
}
TABLE_MISE_AU_POINT = {
    "pours": "pour",
    "contres": "contre",
    "abstentions": "abstention",
    "nonVotants": "non_votant",
    "nonVotantsVolontaires": "non_votant_volontaire",
}
TABLE_DYSFONCTIONNEMENT = {
    "pour": "pour",
    "contre": "contre",
    "abstentions": "abstention",
    "nonVotants": "non_votant",
    "nonVotantsVolontaires": "non_votant_volontaire",
}
TABLE_SORT = {"adopté": "adopte", "rejeté": "rejete"}
TABLE_TYPE_VOTE = {"SPO": "SPO", "SPS": "SPS", "MOC": "MOC"}
TABLE_CAUSE = {"MG": "MG", "PSE": "PSE", "PAN": "PAN"}
POSITIONS_MAJORITAIRES = ("pour", "contre", "abstention")
_ORDRE_POSITION = {"pour": 0, "contre": 1, "abstention": 2, "non_votant": 3}


class _Contexte:
    """Collecte des erreurs (plafonnées, mais toutes comptées) et des avertissements."""

    def __init__(self) -> None:
        self.erreurs: list[Anomalie] = []
        self.avertissements: list[Anomalie] = []
        self.nb_erreurs = 0

    def err(self, chemin: str, code: str, detail: str = "") -> None:
        self.nb_erreurs += 1
        if len(self.erreurs) < MAX_ERREURS:
            self.erreurs.append(Anomalie(chemin, code, detail))

    def warn(self, chemin: str, code: str, detail: str = "") -> None:
        self.avertissements.append(Anomalie(chemin, code, detail))


# --- Fonctions de base -----------------------------------------------------------------------


def entier(v: Any, ctx: _Contexte, chemin: str) -> int | None:
    """ALG-02.N1 : chaîne d'entier canonique ou entier JSON >= 0 (booléen exclu)."""
    if isinstance(v, bool):
        ctx.err(chemin, "format_entier", repr(v))
    elif isinstance(v, int):
        if v >= 0:
            return v
        ctx.err(chemin, "format_entier", repr(v))
    elif isinstance(v, str) and _ENTIER.fullmatch(v):
        return int(v)
    else:
        ctx.err(chemin, "format_entier", repr(v))
    return None


def booleen(v: Any, ctx: _Contexte, chemin: str) -> bool | None:
    """ALG-02.N3 : exactement « true » ou « false » (chaînes)."""
    if v == "true" and isinstance(v, str):
        return True
    if v == "false" and isinstance(v, str):
        return False
    ctx.err(chemin, "format_booleen", repr(v))
    return None


def date_iso(v: Any, ctx: _Contexte, chemin: str) -> str | None:
    """ALG-02.N4 : AAAA-MM-JJ, date du calendrier valide, conservée telle quelle."""
    if isinstance(v, str) and _DATE.fullmatch(v):
        try:
            datetime.date.fromisoformat(v)
        except ValueError:
            pass
        else:
            return v
    ctx.err(chemin, "format_date", repr(v))
    return None


def texte(v: Any, ctx: _Contexte, chemin: str, requis: bool = True) -> str | None:
    """ALG-02.N5 : NFC, espaces de bord retirés (avertissement), vide -> None."""
    if v is not None and not isinstance(v, str):
        ctx.err(chemin, "format_texte", repr(v))
        return None
    resultat: str | None = None
    if v is not None:
        nfc = unicodedata.normalize("NFC", v)
        resultat = nfc.strip()
        if resultat != nfc:
            ctx.warn(chemin, "espaces_retires")
        if resultat == "":
            resultat = None
    if resultat is None and requis:
        ctx.err(chemin, "texte_requis")
    return resultat


def reference(v: Any, prefixe: str, ctx: _Contexte, chemin: str) -> tuple[str | None, bool]:
    """ALG-02.N6 : référence `<préfixe><entier>` ; renvoie (valeur, résolue).

    `PO0` donne (None, False) : référence non résolue, pas une erreur de format.
    """
    if isinstance(v, str):
        if prefixe == "PO" and v == "PO0":
            return None, False
        if v.startswith(prefixe) and _ENTIER.fullmatch(v[len(prefixe) :]) and v != prefixe + "0":
            return v, True
    ctx.err(chemin, "format_reference", repr(v))
    return None, True


def enum_ferme(v: Any, table: dict[str, str], ctx: _Contexte, chemin: str) -> str | None:
    """ALG-02.N7 : la valeur doit être une clé de la table ; sinon `valeur_inconnue`."""
    if isinstance(v, str) and v in table:
        return table[v]
    ctx.err(chemin, "valeur_inconnue", repr(v))
    return None


def objet(
    d: Any,
    requises: tuple[str, ...],
    optionnelles: tuple[str, ...],
    ctx: _Contexte,
    chemin: str,
) -> dict[str, Any] | None:
    """ALG-02.N8 : dictionnaire avec clés requises ; clés inconnues -> avertissement.

    Renvoie None (erreur enregistrée) si `d` n'est pas un dictionnaire ou s'il manque une clé
    requise, pour ne pas multiplier les erreurs en cascade.
    """
    if not isinstance(d, dict):
        ctx.err(chemin, "type_objet", type(d).__name__)
        return None
    manque = [k for k in requises if k not in d]
    for k in manque:
        ctx.err(f"{chemin}.{k}", "champ_requis")
    for k in d:
        if k not in requises and k not in optionnelles:
            ctx.warn(f"{chemin}.{k}", "champ_inconnu")
    return None if manque else d


def aplatir_votants(noeud: Any, ctx: _Contexte, chemin: str) -> list[dict[str, Any]]:
    """ALG-02.N9 : null, liste, ou {"votant": objet | liste} -> liste de dictionnaires."""
    if noeud is None:
        return []
    if isinstance(noeud, list):
        resultat: list[dict[str, Any]] = []
        for i, element in enumerate(noeud):
            resultat.extend(aplatir_votants(element, ctx, f"{chemin}[{i}]"))
        return resultat
    if isinstance(noeud, dict):
        if set(noeud) != {"votant"}:
            ctx.err(chemin, "forme_votants", repr(sorted(noeud)))
            return []
        x = noeud["votant"]
        if isinstance(x, dict):
            return [x]
        if isinstance(x, list):
            if all(isinstance(e, dict) for e in x):
                return list(x)
            ctx.err(chemin, "forme_votants", "élément de liste qui n'est pas un objet")
            return []
    ctx.err(chemin, "forme_votants", type(noeud).__name__)
    return []


# --- Assemblage ------------------------------------------------------------------------------


def _lire_votant(
    v: dict[str, Any], ctx: _Contexte, chemin: str
) -> tuple[str | None, str | None, bool | None]:
    """ALG-02.17 : acteurRef, mandatRef, parDelegation d'un votant (numPlace ignoré)."""
    acteur, _ = reference(v.get("acteurRef"), "PA", ctx, f"{chemin}.acteurRef")
    mandat, _ = reference(v.get("mandatRef"), "PM", ctx, f"{chemin}.mandatRef")
    delegation = booleen(v.get("parDelegation"), ctx, f"{chemin}.parDelegation")
    return acteur, mandat, delegation


def _lire_corrections(
    noeud: dict[str, Any],
    table: dict[str, str],
    origine: str,
    ctx: _Contexte,
    chemin: str,
) -> list[LigneCorrection]:
    """ALG-02.21 / 22 : mises au point et dysfonctionnements (mêmes règles, tables distinctes)."""
    lignes: list[LigneCorrection] = []
    for cle, position in table.items():
        for i, brut in enumerate(aplatir_votants(noeud.get(cle), ctx, f"{chemin}.{cle}")):
            ch = f"{chemin}.{cle}[{i}]"
            v = objet(
                brut, ("acteurRef", "mandatRef", "parDelegation"), ("numPlace",), ctx, ch
            )
            if v is None:
                continue
            acteur, mandat, delegation = _lire_votant(v, ctx, ch)
            if acteur and mandat and delegation is not None:
                lignes.append(LigneCorrection(acteur, mandat, position, delegation, origine))
    return lignes


def _lire_groupe(
    g: Any, rang: int, ctx: _Contexte, chemin: str, numero: Any
) -> GroupeNormalise | None:
    """ALG-02.12 à 19 : un groupe, ses effectifs et ses votes nominatifs."""
    # ALG-02.12 : clés du groupe, rang = position dans le fichier
    g = objet(g, ("organeRef", "nombreMembresGroupe", "vote"), (), ctx, chemin)
    if g is None:
        return None
    membres = entier(g["nombreMembresGroupe"], ctx, f"{chemin}.nombreMembresGroupe")

    # ALG-02.13 : référence du groupe, « PO0 » = non résolue (jamais devinée)
    organe_ref, resolue = reference(g["organeRef"], "PO", ctx, f"{chemin}.organeRef")
    if not resolue:
        ctx.warn(chemin, "groupe_non_identifie", f"scrutin {numero}, rang {rang}")

    # ALG-02.14 : vote ; positionMajoritaire conservée pour audit uniquement
    vote = objet(
        g["vote"], ("positionMajoritaire", "decompteVoix", "decompteNominatif"), (), ctx,
        f"{chemin}.vote",
    )
    if vote is None:
        return None
    position_source = texte(vote["positionMajoritaire"], ctx, f"{chemin}.vote.positionMajoritaire")
    if position_source is not None:
        position_source = position_source.lower()
        if position_source not in POSITIONS_MAJORITAIRES:
            ctx.warn(
                f"{chemin}.vote.positionMajoritaire", "position_majoritaire_inconnue",
                position_source,
            )

    # ALG-02.15 : effectifs par groupe (nonVotantsVolontaires lu, validé, non stocké comme position)
    voix = objet(
        vote["decompteVoix"],
        ("pour", "contre", "abstentions", "nonVotants", "nonVotantsVolontaires"),
        (),
        ctx,
        f"{chemin}.vote.decompteVoix",
    )
    compteurs: dict[str, int | None] = {}
    if voix is not None:
        for cle in ("pour", "contre", "abstentions", "nonVotants", "nonVotantsVolontaires"):
            compteurs[cle] = entier(voix[cle], ctx, f"{chemin}.vote.decompteVoix.{cle}")

    # ALG-02.16 : les quatre listes nominatives (null admis)
    nominatif = objet(
        vote["decompteNominatif"],
        ("pours", "contres", "abstentions", "nonVotants"),
        (),
        ctx,
        f"{chemin}.vote.decompteNominatif",
    )
    votants: list[Votant] = []
    if nominatif is not None:
        for cle, position in TABLE_NOMINATIF.items():
            chemin_liste = f"{chemin}.vote.decompteNominatif.{cle}"
            # ALG-02.17 : une ligne par vote individuel
            for i, brut in enumerate(aplatir_votants(nominatif[cle], ctx, chemin_liste)):
                ch = f"{chemin_liste}[{i}]"
                v = objet(
                    brut,
                    ("acteurRef", "mandatRef", "parDelegation"),
                    ("numPlace", "causePositionVote"),
                    ctx,
                    ch,
                )
                if v is None:
                    continue
                acteur, mandat, delegation = _lire_votant(v, ctx, ch)
                # ALG-02.18 : cause de non-vote
                cause: str | None = None
                if position == "non_votant":
                    if v.get("causePositionVote") is None:
                        ctx.warn(ch, "non_votant_sans_cause")
                    else:
                        cause = enum_ferme(v["causePositionVote"], TABLE_CAUSE, ctx,
                                           f"{ch}.causePositionVote")
                elif v.get("causePositionVote") is not None:
                    ctx.err(ch, "cause_incoherente", position)
                if acteur and mandat and delegation is not None:
                    votants.append(Votant(acteur, mandat, position, delegation, cause))

    # ALG-02.19 : tri déterministe (position, acteur_ref)
    votants.sort(key=lambda x: (_ORDRE_POSITION[x.position], x.acteur_ref))

    if (
        membres is None
        or position_source is None
        or voix is None
        or None in compteurs.values()
    ):
        return None
    return GroupeNormalise(
        rang=rang,
        organe_ref=organe_ref,
        membres=membres,
        pour=compteurs["pour"] or 0,
        contre=compteurs["contre"] or 0,
        abstentions=compteurs["abstentions"] or 0,
        non_votants=compteurs["nonVotants"] or 0,
        position_majoritaire_source=position_source,
        abstentions_doublon_source=compteurs["nonVotantsVolontaires"] or 0,
        votants=votants,
    )


_REQUISES_SCRUTIN = (
    "uid", "numero", "organeRef", "legislature", "sessionRef", "seanceRef", "dateScrutin",
    "quantiemeJourSeance", "typeVote", "sort", "titre", "demandeur", "objet",
    "modePublicationDesVotes", "syntheseVote", "ventilationVotes", "miseAuPoint", "lieuVote",
)  # fmt: skip


def normaliser_scrutin(document: Any) -> ResultatNormalisation:
    """Normalise le document brut d'un scrutin (ALG-02).

    Returns:
        Un `ResultatNormalisation` : soit `scrutin` renseigné (et aucune erreur), soit des
        erreurs (au plus 50 rapportées, avec leur chemin) et `scrutin` à None. Les
        avertissements sont toujours renvoyés.
    """
    ctx = _Contexte()

    # ALG-02.1 : racine exactement {"scrutin": {...}}
    if not (
        isinstance(document, dict) and set(document) == {"scrutin"}
        and isinstance(document["scrutin"], dict)
    ):
        ctx.err("", "structure", "racine différente de {'scrutin': {...}}")
        return ResultatNormalisation(None, ctx.erreurs, ctx.avertissements)

    # ALG-02.2 : dix-huit clés requises, deux optionnelles
    s = objet(document["scrutin"], _REQUISES_SCRUTIN, ("@xmlns", "@xmlns:xsi"), ctx, "scrutin")
    if s is None:
        return ResultatNormalisation(None, ctx.erreurs[:MAX_ERREURS], ctx.avertissements)

    # ALG-02.3 : espaces de noms XML comparés à leurs valeurs observées
    for cle, attendu in (("@xmlns", XMLNS_ATTENDU), ("@xmlns:xsi", XMLNS_XSI_ATTENDU)):
        if cle in s and s[cle] != attendu:
            ctx.warn(f"scrutin.{cle}", "schema_modifie", repr(s[cle]))

    # ALG-02.4 : identité et provenance de la séance
    id_ = texte(s["uid"], ctx, "scrutin.uid")
    numero = entier(s["numero"], ctx, "scrutin.numero")
    legislature = entier(s["legislature"], ctx, "scrutin.legislature")
    quantieme = entier(s["quantiemeJourSeance"], ctx, "scrutin.quantiemeJourSeance")
    date_scrutin = date_iso(s["dateScrutin"], ctx, "scrutin.dateScrutin")
    session_ref = texte(s["sessionRef"], ctx, "scrutin.sessionRef")
    seance_ref = texte(s["seanceRef"], ctx, "scrutin.seanceRef")
    lieu_vote = texte(s["lieuVote"], ctx, "scrutin.lieuVote")
    organe_ref, resolue = reference(s["organeRef"], "PO", ctx, "scrutin.organeRef")
    if not resolue:
        # CHOIX: « PO0 » au niveau du scrutin est une erreur, seul un groupe peut être non résolu
        # RAISON: la fiche ne prévoit de référence non résolue que pour les groupes (ALG-02.13)
        ctx.err("scrutin.organeRef", "reference_non_resolue", "PO0")

    # ALG-02.5 : type de vote
    tv = objet(
        s["typeVote"], ("codeTypeVote", "libelleTypeVote", "typeMajorite"), (), ctx,
        "scrutin.typeVote",
    )
    type_code = type_libelle = type_majorite = None
    if tv is not None:
        type_code = enum_ferme(tv["codeTypeVote"], TABLE_TYPE_VOTE, ctx,
                               "scrutin.typeVote.codeTypeVote")
        type_libelle = texte(tv["libelleTypeVote"], ctx, "scrutin.typeVote.libelleTypeVote")
        type_majorite = texte(tv["typeMajorite"], ctx, "scrutin.typeVote.typeMajorite")

    # ALG-02.6 : résultat
    so = objet(s["sort"], ("code", "libelle"), (), ctx, "scrutin.sort")
    sort_code = sort_libelle = None
    if so is not None:
        sort_code = enum_ferme(so["code"], TABLE_SORT, ctx, "scrutin.sort.code")
        sort_libelle = texte(so["libelle"], ctx, "scrutin.sort.libelle")

    # ALG-02.7 : titre, objet, dossier législatif (null = cas normal, non signalé)
    titre = texte(s["titre"], ctx, "scrutin.titre")
    ob = objet(
        s["objet"], ("libelle",), ("dossierLegislatif", "referenceLegislative"), ctx,
        "scrutin.objet",
    )
    objet_libelle = dossier_ref = dossier_libelle = None
    if ob is not None:
        objet_libelle = texte(ob["libelle"], ctx, "scrutin.objet.libelle")
        if ob.get("dossierLegislatif") is not None:
            dl = objet(ob["dossierLegislatif"], ("dossierRef", "libelle"), (), ctx,
                       "scrutin.objet.dossierLegislatif")
            if dl is not None:
                dossier_ref = texte(dl["dossierRef"], ctx, "scrutin.objet.dossierLegislatif.dossierRef")
                dossier_libelle = texte(dl["libelle"], ctx, "scrutin.objet.dossierLegislatif.libelle")

    # ALG-02.8 : demandeur (texte null dans 30 scrutins : cas normal)
    de = objet(s["demandeur"], (), ("texte", "referenceLegislative"), ctx, "scrutin.demandeur")
    demandeur_texte = texte(de.get("texte"), ctx, "scrutin.demandeur.texte", requis=False) if de else None

    # ALG-02.9 : seul le mode « DecompteNominatif » est géré
    mode = texte(s["modePublicationDesVotes"], ctx, "scrutin.modePublicationDesVotes")
    if mode is not None and mode != "DecompteNominatif":
        ctx.err("scrutin.modePublicationDesVotes", "mode_publication_non_gere", mode)

    # ALG-02.10 : totaux officiels, sans aucun calcul
    sv = objet(
        s["syntheseVote"],
        ("nombreVotants", "suffragesExprimes", "nbrSuffragesRequis", "decompte"),
        ("annonce",),
        ctx,
        "scrutin.syntheseVote",
    )
    totaux: dict[str, int | None] = {}
    if sv is not None:
        for cle in ("nombreVotants", "suffragesExprimes", "nbrSuffragesRequis"):
            totaux[cle] = entier(sv[cle], ctx, f"scrutin.syntheseVote.{cle}")
        dc = objet(
            sv["decompte"],
            ("pour", "contre", "abstentions", "nonVotants", "nonVotantsVolontaires"),
            (),
            ctx,
            "scrutin.syntheseVote.decompte",
        )
        if dc is not None:
            for cle in ("pour", "contre", "abstentions", "nonVotants", "nonVotantsVolontaires"):
                totaux[cle] = entier(dc[cle], ctx, f"scrutin.syntheseVote.decompte.{cle}")

    # ALG-02.11 : chemin ventilationVotes.organe.groupes.groupe, mis en liste
    groupes_bruts: list[Any] = []
    chemin_v = "scrutin.ventilationVotes"
    vv = objet(s["ventilationVotes"], ("organe",), (), ctx, chemin_v)
    org = objet(vv["organe"], ("organeRef", "groupes"), (), ctx, f"{chemin_v}.organe") if vv else None
    gs = objet(org["groupes"], ("groupe",), (), ctx, f"{chemin_v}.organe.groupes") if org else None
    if gs is not None:
        noeud = gs["groupe"]
        if noeud is None:
            ctx.err(f"{chemin_v}.organe.groupes.groupe", "groupe_null")
        elif isinstance(noeud, list):
            groupes_bruts = noeud
        else:
            groupes_bruts = [noeud]
        if not groupes_bruts and noeud is not None:
            ctx.err(f"{chemin_v}.organe.groupes.groupe", "aucun_groupe")

    # ALG-02.12 à 19 : chaque groupe, rang = position dans le fichier (1, 2, …)
    groupes: list[GroupeNormalise] = []
    for rang, brut in enumerate(groupes_bruts, start=1):
        groupe = _lire_groupe(brut, rang, ctx, f"{chemin_v}.organe.groupes.groupe[{rang - 1}]", numero)
        if groupe is not None:
            groupes.append(groupe)

    # ALG-02.20 : un député ne vote qu'une fois par scrutin
    vus: set[str] = set()
    doublons: set[str] = set()
    for groupe in groupes:
        for v in groupe.votants:
            (doublons if v.acteur_ref in vus else vus).add(v.acteur_ref)
    for acteur in sorted(doublons):
        ctx.err("scrutin.ventilationVotes", "depute_en_double", acteur)

    # ALG-02.21 et 22 : mises au point, puis dysfonctionnements (information distincte)
    cles_mp = tuple(TABLE_MISE_AU_POINT) + ("dysfonctionnement",)
    mp = objet(s["miseAuPoint"], cles_mp, (), ctx, "scrutin.miseAuPoint")
    mises_au_point: list[LigneCorrection] = []
    dysfonctionnements: list[LigneCorrection] = []
    if mp is not None:
        mises_au_point = _lire_corrections(
            mp, TABLE_MISE_AU_POINT, "mise_au_point", ctx, "scrutin.miseAuPoint"
        )
        dys = objet(mp["dysfonctionnement"], tuple(TABLE_DYSFONCTIONNEMENT), (), ctx,
                    "scrutin.miseAuPoint.dysfonctionnement")
        if dys is not None:
            dysfonctionnements = _lire_corrections(
                dys, TABLE_DYSFONCTIONNEMENT, "dysfonctionnement", ctx,
                "scrutin.miseAuPoint.dysfonctionnement",
            )

    # ALG-02.23 : jamais de scrutin à moitié normalisé
    if ctx.nb_erreurs:
        return ResultatNormalisation(None, ctx.erreurs, ctx.avertissements)

    # ALG-02.24 : scrutin normalisé et avertissements
    assert id_ and numero is not None and legislature is not None and date_scrutin
    assert organe_ref and session_ref and seance_ref and lieu_vote and quantieme is not None
    assert type_code and type_libelle and type_majorite and sort_code and sort_libelle
    assert titre and objet_libelle and mode
    return ResultatNormalisation(
        ScrutinNormalise(
            id=id_,
            numero=numero,
            legislature=legislature,
            date_scrutin=date_scrutin,
            session_ref=session_ref,
            seance_ref=seance_ref,
            organe_ref=organe_ref,
            quantieme_jour_seance=quantieme,
            lieu_vote=lieu_vote,
            type_vote_code=type_code,
            type_vote_libelle=type_libelle,
            type_majorite=type_majorite,
            titre=titre,
            objet_libelle=objet_libelle,
            dossier_ref=dossier_ref,
            dossier_libelle=dossier_libelle,
            demandeur_texte=demandeur_texte,
            mode_publication=mode,
            sort_code=sort_code,
            sort_libelle=sort_libelle,
            nombre_votants=totaux["nombreVotants"] or 0,
            suffrages_exprimes=totaux["suffragesExprimes"] or 0,
            nbr_suffrages_requis=totaux["nbrSuffragesRequis"] or 0,
            pour=totaux["pour"] or 0,
            contre=totaux["contre"] or 0,
            abstentions=totaux["abstentions"] or 0,
            non_votants=totaux["nonVotants"] or 0,
            non_votants_volontaires=totaux["nonVotantsVolontaires"] or 0,
            groupes=groupes,
            mises_au_point=mises_au_point,
            dysfonctionnements=dysfonctionnements,
        ),
        [],
        ctx.avertissements,
    )
