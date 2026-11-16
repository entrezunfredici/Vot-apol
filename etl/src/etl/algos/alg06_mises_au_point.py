"""ALG-06 : Mises au point.

Spécification : docs/algorithmes/ALG-06-mises-au-point.md (statut « Validé »).
Fonctions pures : pas de disque, pas de réseau, pas de SQL (voir etl/io/).
Chaque bloc de code est précédé de « # ALG-06.k : <résumé> ».
Deux temps : A. `rattacher` (à l'import) ; B. `corriger_effectifs` (à l'export, rien n'est stocké).
"""

import dataclasses

from ..models import CorrectionGroupe, LigneMiseAuPoint, LotScrutin
from .alg03_position_majoritaire import ErreurDonnee, calculer_position

_EXPRIMEES = ("pour", "contre", "abstention")


def rattacher(lot: LotScrutin) -> LotScrutin:
    """Partie A : groupe et position initiale de chaque ligne retrouvée dans les votes du lot."""
    # ALG-06.1 : index depute_id -> (groupe_rang, groupe_id, position), lu dans les votes du scrutin
    index = {v.depute_id: (v.groupe_rang, v.groupe_id, v.position) for v in lot.votes}

    lignes: list[LigneMiseAuPoint] = []
    for m in lot.mises_au_point:
        # ALG-06.2 et 3 : député absent des votes -> introuvable, NULL partout (jamais deviné)
        if m.depute_id not in index:
            lignes.append(
                dataclasses.replace(
                    m,
                    groupe_rang=None,
                    groupe_id=None,
                    position_initiale=None,
                    statut_rattachement="introuvable",
                    effet=None,
                )
            )
            continue
        # ALG-06.2 : copie du groupe et de la position initiale ; ALG-06.5 : valable aussi pour
        # un dysfonctionnement (l'exclusion des effectifs se fait en B)
        rang, groupe_id, initiale = index[m.depute_id]
        # ALG-06.4 : position déclarée identique à l'initiale -> sans effet
        effet = "sans_effet" if m.position_declaree == initiale else "modifie_position"
        lignes.append(
            dataclasses.replace(
                m,
                groupe_rang=rang,
                groupe_id=groupe_id,
                position_initiale=initiale,
                statut_rattachement="rattachee",
                effet=effet,
            )
        )
    return dataclasses.replace(lot, mises_au_point=lignes)


def corriger_effectifs(lot: LotScrutin) -> list[CorrectionGroupe]:
    """Partie B : effectifs corrigés par groupe identifié (lot déjà passé dans `rattacher`)."""
    # ALG-06.5 et 6 : mises au point à effet (hors dysfonctionnements), regroupées par rang ;
    # groupes non identifiés ignorés
    par_rang: dict[int, list[LigneMiseAuPoint]] = {}
    for m in lot.mises_au_point:
        if (
            m.origine == "mise_au_point"
            and m.statut_rattachement == "rattachee"
            and m.effet == "modifie_position"
            and m.groupe_id is not None
            and m.groupe_rang is not None
        ):
            par_rang.setdefault(m.groupe_rang, []).append(m)

    groupes = {g.rang: g for g in lot.groupes}
    corrections: list[CorrectionGroupe] = []
    for rang in sorted(par_rang):
        g = groupes[rang]
        # ALG-06.7 : compteurs officiels de départ ; retirer l'initiale, ajouter la déclarée,
        # seulement si la position est exprimée (un non-vote n'est pas une abstention)
        eff = {"pour": g.pour, "contre": g.contre, "abstention": g.abstentions}
        for m in par_rang[rang]:
            if m.position_initiale in _EXPRIMEES:
                eff[m.position_initiale] -= 1
            if m.position_declaree in _EXPRIMEES:
                eff[m.position_declaree] += 1

        # ALG-06.10 : effectif négatif = défaut de rattachement ou de réconciliation
        if min(eff.values()) < 0:
            raise ErreurDonnee(f"effectif corrigé négatif pour le groupe de rang {rang} : {eff}")

        # ALG-06.8 : même règle ALG-03 pour les compteurs officiels et corrigés
        officielle = calculer_position(g.pour, g.contre, g.abstentions, g.membres)
        corrigee = calculer_position(eff["pour"], eff["contre"], eff["abstention"], g.membres)

        # ALG-06.9 : on compare les positions, pas les effectifs
        corrections.append(
            CorrectionGroupe(
                rang=rang,
                groupe_id=m.groupe_id,  # type: ignore[arg-type]  # non nul : filtré en ALG-06.6
                pour_corrige=eff["pour"],
                contre_corrige=eff["contre"],
                abstentions_corrigees=eff["abstention"],
                position_officielle=officielle.position,
                position_corrigee=corrigee.position,
                raison_absence_corrigee=corrigee.raison_absence,
                change_position_majoritaire=corrigee.position != officielle.position,
                nb_mises_au_point=len(par_rang[rang]),
            )
        )
    # ALG-06.11 : triées par rang (boucle sur rang trié), aucune écriture
    return corrections
