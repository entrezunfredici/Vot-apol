// Interface de recherche : l'implémentation (MiniSearch, provisoire) reste remplaçable
// (DECISIONS.md, « Recherche côté navigateur »). Les filtres sont purs et ne dépendent pas d'elle.
export { creerRecherche } from './minisearch'
export type { Recherche } from './minisearch'
export * from './filtres'
