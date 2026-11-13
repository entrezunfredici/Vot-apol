"""ALG-04 : Extraction d'un scrutin.

Spécification : docs/algorithmes/ALG-04-extraction-scrutin.md.
Fonctions pures : pas de disque, pas de réseau, pas de SQL (voir etl/io/).
Aucune horloge : l'horodatage est fourni par l'appelant.
Chaque bloc de code est précédé de « # ALG-04.k : <résumé> ».
"""

from ..models import (
    POSITIONS_VOTE,
    Comptages,
    LigneGroupe,
    LigneMiseAuPoint,
    LigneScrutin,
    LigneTotaux,
    LigneVote,
    LotScrutin,
    ScrutinNormalise,
)


class ErreurExtraction(Exception):
    """Lot impossible à construire ; `motif` vaut `identite` ou `cle_dupliquee`."""

    def __init__(self, motif: str, detail: str = "") -> None:
        super().__init__(f"{motif}: {detail}" if detail else motif)
        self.motif = motif


def extraire_scrutin(
    scrutin: ScrutinNormalise,
    nom: str,
    sha256_fichier: str,
    source_url: str | None,
    importe_le: str,
    version_etl: str,
) -> LotScrutin:
    """Projette un `ScrutinNormalise` valide en lignes de tables, sans rien écrire."""
    if not importe_le:
        # pas d'horloge cachée : une valeur par défaut serait une donnée inventée
        raise ValueError("importe_le est obligatoire (fourni par l'appelant)")

    # ALG-04.1 : le contenu doit correspondre à l'empreinte du fichier de même nom
    sans_extension = nom.rsplit("/", 1)[-1].removesuffix(".json")
    if sans_extension != scrutin.id:
        raise ErreurExtraction("identite", f"{nom} / {scrutin.id}")

    sid = scrutin.id

    # ALG-04.2 et 3 : une ligne scrutin, une ligne de totaux officiels (jamais recalculés)
    ligne_scrutin = LigneScrutin(
        id=sid,
        numero=scrutin.numero,
        legislature=scrutin.legislature,
        date_scrutin=scrutin.date_scrutin,
        titre=scrutin.titre,
        objet=scrutin.objet_libelle,
        type_vote_code=scrutin.type_vote_code,
        type_vote_libelle=scrutin.type_vote_libelle,
        resultat_code=scrutin.sort_code,
        source_url=source_url,
        source_hash=sha256_fichier,
        imported_at=importe_le,
        etl_version=version_etl,
    )
    totaux = LigneTotaux(
        scrutin_id=sid,
        pour=scrutin.pour,
        contre=scrutin.contre,
        abstentions=scrutin.abstentions,
        non_votants=scrutin.non_votants,
        suffrages_exprimes=scrutin.suffrages_exprimes,
        nombre_votants=scrutin.nombre_votants,
    )

    groupes: list[LigneGroupe] = []
    votes: list[LigneVote] = []
    par_groupe: dict[int, dict[str, int]] = {}
    par_scrutin = dict.fromkeys(POSITIONS_VOTE, 0)

    # ALG-04.4 et 5 : groupes dans l'ordre du fichier, puis leurs votants
    for g in scrutin.groupes:
        groupes.append(
            LigneGroupe(
                scrutin_id=sid,
                rang=g.rang,
                groupe_id=g.organe_ref,
                membres=g.membres,
                pour=g.pour,
                contre=g.contre,
                abstentions=g.abstentions,
                non_votants=g.non_votants,
                position_majoritaire_source=g.position_majoritaire_source,
            )
        )
        compte = dict.fromkeys(POSITIONS_VOTE, 0)
        for v in g.votants:
            votes.append(
                LigneVote(
                    scrutin_id=sid,
                    depute_id=v.acteur_ref,
                    groupe_rang=g.rang,
                    groupe_id=g.organe_ref,
                    mandat_id=v.mandat_ref,
                    position=v.position,
                    par_delegation=int(v.par_delegation),
                    cause=v.cause,
                )
            )
            # ALG-04.9 : comptage des lignes produites, pas des compteurs de la source
            compte[v.position] += 1
            par_scrutin[v.position] += 1
        par_groupe[g.rang] = compte

    # ALG-04.6 : mises au point puis dysfonctionnements ; rattachement laissé à ALG-06
    mises: list[LigneMiseAuPoint] = [
        LigneMiseAuPoint(
            scrutin_id=sid,
            depute_id=m.acteur_ref,
            origine=m.origine,
            position_declaree=m.position_declaree,
            par_delegation=int(m.par_delegation),
        )
        for m in [*scrutin.mises_au_point, *scrutin.dysfonctionnements]
    ]

    # ALG-04.7 : unicité des clés (rang ; député dans les votes ; député dans les mises au point)
    _verifier_unicite([g.rang for g in groupes], "rang de groupe")
    _verifier_unicite([v.depute_id for v in votes], "député (votes)")
    _verifier_unicite([m.depute_id for m in mises], "député (mises au point)")

    # ALG-04.8 : identifiants rencontrés, pour créer les lignes `groupes` et `deputes`
    groupes_vus = sorted({g.groupe_id for g in groupes if g.groupe_id is not None})
    deputes_vus = sorted({v.depute_id for v in votes} | {m.depute_id for m in mises})

    # ALG-04.10 : tri par clé primaire (sortie déterministe)
    return LotScrutin(
        scrutin=ligne_scrutin,
        totaux=totaux,
        groupes=sorted(groupes, key=lambda g: g.rang),
        votes=sorted(votes, key=lambda v: v.depute_id),
        mises_au_point=sorted(mises, key=lambda m: m.depute_id),
        groupes_vus=groupes_vus,
        deputes_vus=deputes_vus,
        comptages=Comptages(par_groupe=par_groupe, scrutin=par_scrutin),
    )


def _verifier_unicite(cles: list, description: str) -> None:
    if len(set(cles)) != len(cles):
        doublon = next(c for c in cles if cles.count(c) > 1)
        raise ErreurExtraction("cle_dupliquee", f"{description} : {doublon!r}")
