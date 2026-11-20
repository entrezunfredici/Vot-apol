// Filtres, tri et pagination de la liste des scrutins : fonctions pures, testées.
import type { Categorie, LigneIndex, Resultat } from '../data'

export interface Filtres {
  dateDebut?: string // AAAA-MM-JJ, inclus
  dateFin?: string // AAAA-MM-JJ, inclus
  categories: Categorie[] // vide = toutes
  resultats: Resultat[] // vide = tous
}

export const FILTRES_VIDES: Filtres = { categories: [], resultats: [] }

export type Tri = 'recent' | 'ancien' | 'numero'

export function appliquerFiltres(lignes: LigneIndex[], f: Filtres): LigneIndex[] {
  return lignes.filter(
    (l) =>
      (!f.dateDebut || l.date >= f.dateDebut) &&
      (!f.dateFin || l.date <= f.dateFin) &&
      (f.categories.length === 0 || f.categories.includes(l.categorie.valeur)) &&
      (f.resultats.length === 0 || f.resultats.includes(l.resultat)),
  )
}

export function trier(lignes: LigneIndex[], tri: Tri): LigneIndex[] {
  const copie = [...lignes]
  if (tri === 'ancien') return copie.sort((a, b) => a.date.localeCompare(b.date) || a.numero - b.numero)
  if (tri === 'numero') return copie.sort((a, b) => a.numero - b.numero)
  return copie.sort((a, b) => b.date.localeCompare(a.date) || b.numero - a.numero)
}

export function compterFiltresActifs(f: Filtres): number {
  return (
    (f.dateDebut ? 1 : 0) + (f.dateFin ? 1 : 0) + (f.categories.length ? 1 : 0) + (f.resultats.length ? 1 : 0)
  )
}

export interface Page<T> {
  items: T[]
  page: number // page courante, bornée à [1, pages]
  pages: number
  de: number // rang du premier élément (1-based), 0 si vide
  a: number
  total: number
}

export function paginer<T>(items: T[], page: number, taille: number): Page<T> {
  const total = items.length
  const pages = Math.max(1, Math.ceil(total / taille))
  const courante = Math.min(Math.max(1, Math.trunc(page) || 1), pages)
  const debut = (courante - 1) * taille
  const tranche = items.slice(debut, debut + taille)
  return {
    items: tranche,
    page: courante,
    pages,
    de: total === 0 ? 0 : debut + 1,
    a: debut + tranche.length,
    total,
  }
}

/** Numéros de page à afficher : première, dernière et voisines de la page courante, « null » = « … ». */
export function numerosDePage(courante: number, pages: number): (number | null)[] {
  const voulus = new Set([1, pages, courante - 1, courante, courante + 1])
  const tries = [...voulus].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b)
  const sortie: (number | null)[] = []
  tries.forEach((n, i) => {
    if (i > 0 && n - tries[i - 1] > 1) sortie.push(null)
    sortie.push(n)
  })
  return sortie
}
