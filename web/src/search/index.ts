// Interface de recherche : l'implémentation (MiniSearch, provisoire) reste remplaçable.
export interface Filtres {
  dateDebut?: string
  dateFin?: string
  categorie?: string
  resultat?: string
}

export interface Recherche {
  search(query: string, filtres: Filtres): string[] // identifiants de scrutins
}
