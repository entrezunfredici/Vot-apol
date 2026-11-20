// Comparaison de la position majoritaire de 2 ou 3 groupes. Pur : testé sans réseau.
import type { LigneGroupe } from '../data'

export type TypeComparaison = 'meme' | 'differente' | 'sans'

export interface LigneComparee {
  scrutin_id: string
  numero: number
  date: string
  type: TypeComparaison
  /** Une ligne par groupe, dans l'ordre demandé. */
  lignes: LigneGroupe[]
}

/**
 * Compare les groupes sur les scrutins qu'ils ont tous. `meme` : tous ont une position majoritaire et
 * c'est la même ; `differente` : tous en ont une et elles ne sont pas toutes égales ; `sans` : au moins
 * un groupe n'en a pas (égalité ou aucun vote exprimé) — jamais rangé dans les deux autres.
 */
export function comparer(historiques: LigneGroupe[][]): LigneComparee[] {
  if (historiques.length < 2) return []
  const parId = historiques.map((h) => new Map(h.map((l) => [l.scrutin_id, l])))
  const resultat: LigneComparee[] = []
  for (const base of historiques[0]) {
    const lignes = parId.map((m) => m.get(base.scrutin_id))
    if (lignes.some((l) => l === undefined)) continue
    const toutes = lignes as LigneGroupe[]
    let type: TypeComparaison
    if (toutes.some((l) => l.position === 'aucune')) type = 'sans'
    else type = toutes.every((l) => l.position === toutes[0].position) ? 'meme' : 'differente'
    resultat.push({ scrutin_id: base.scrutin_id, numero: base.numero, date: base.date, type, lignes: toutes })
  }
  return resultat
}

export function compter(lignes: LigneComparee[]): Record<TypeComparaison, number> {
  const n = { meme: 0, differente: 0, sans: 0 }
  for (const l of lignes) n[l.type]++
  return n
}
