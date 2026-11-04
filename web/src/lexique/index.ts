// Tous les libellés visibles passent par ici : le test lexique.test.ts interdit les mots proscrits (charte).
export const L = {
  nav: {
    accueil: 'Accueil',
    scrutins: 'Scrutins',
    comparateur: 'Comparateur',
    methodologie: 'Méthodologie',
  },
} as const

export const MOTS_INTERDITS = ['cohésion', 'discipline', 'loyauté', 'dissident', 'frondeur']
