// Recherche plein texte dans le navigateur (MiniSearch, provisoire : voir DECISIONS.md).
import MiniSearch from 'minisearch'
import type { LigneIndex } from '../data'

export interface Recherche {
  /** Identifiants des scrutins qui correspondent ; `null` si la requête est vide (aucune restriction). */
  chercher(requete: string): Set<string> | null
}

/** Minuscules, sans accents : « Écologistes » et « ecologistes » se valent. */
export function normaliser(texte: string): string {
  return texte
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

export function creerRecherche(lignes: LigneIndex[]): Recherche {
  const index = new MiniSearch<{ id: string; titre: string; numero: string }>({
    fields: ['titre', 'numero'],
    idField: 'id',
    processTerm: (terme) => normaliser(terme) || null,
    searchOptions: { prefix: true, combineWith: 'AND' },
  })
  index.addAll(lignes.map((l) => ({ id: l.id, titre: l.titre, numero: String(l.numero) })))
  return {
    chercher(requete) {
      if (!requete.trim()) return null
      return new Set(index.search(requete).map((r) => String(r.id)))
    },
  }
}
