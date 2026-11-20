// Lecture du format compact de `groupes/<id>.json` (docs/data-dictionary.md). Pur : testé sans réseau.
import {
  COLONNES_GROUPE,
  type FichierGroupe,
  type LigneGroupe,
} from './types'

/** Erreur levée si le fichier ne suit pas le contrat : on n'affiche jamais des colonnes décalées. */
export class FormatGroupeInvalide extends Error {}

/** Transforme les lignes-tableaux en objets, après avoir vérifié que les colonnes sont celles du contrat. */
export function lireLignesGroupe(f: FichierGroupe): LigneGroupe[] {
  if (f.colonnes.length !== COLONNES_GROUPE.length || f.colonnes.some((c, i) => c !== COLONNES_GROUPE[i])) {
    throw new FormatGroupeInvalide('Colonnes de groupes/<id>.json inattendues')
  }
  return f.scrutins.map((l) => {
    if (l.length !== COLONNES_GROUPE.length) throw new FormatGroupeInvalide('Ligne de longueur inattendue')
    const [scrutin_id, numero, date, categorie, membres, pour, contre, abstentions, non_votants,
      sans_vote_enregistre, position, raison_absence, exprimes, m, majorite_absolue] = l
    return {
      scrutin_id, numero, date, categorie, membres, pour, contre, abstentions, non_votants,
      sans_vote_enregistre, position, raison_absence, exprimes, m, majorite_absolue,
    } as LigneGroupe
  })
}
