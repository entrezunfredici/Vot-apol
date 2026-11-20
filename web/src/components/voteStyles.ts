// Seul fichier qui associe une couleur à une position de vote (charte : les couleurs de vote sont
// les seules couleurs sémantiques). Utilisé par VoteBadge et VoteBar ; les classes sont écrites en
// toutes lettres pour que Tailwind les détecte.
import type { Position } from '../data'

export type TypeBadge = Position | 'resultat'

export const STYLES_VOTE: Record<TypeBadge, { badge: string; segment: string; texte: string }> = {
  pour: { badge: 'bg-pour-bg text-pour', segment: 'bg-pour', texte: 'text-pour' },
  contre: { badge: 'bg-contre-bg text-contre', segment: 'bg-contre', texte: 'text-contre' },
  abstention: {
    badge: 'bg-abstention-bg text-abstention',
    segment: 'bg-abstention',
    texte: 'text-abstention',
  },
  non_votant: {
    badge: 'bg-nonvotant-bg text-nonvotant',
    segment: 'bg-nonvotant',
    texte: 'text-nonvotant',
  },
  // Le résultat d'un scrutin n'est pas un vote : couleur neutre (revue de la maquette, écart n° 6).
  resultat: { badge: 'bg-surface-alt text-ink', segment: 'bg-ink-2', texte: 'text-ink' },
}
