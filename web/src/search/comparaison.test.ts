import { describe, expect, it } from 'vitest'
import type { LigneGroupe, PositionMajoritaireValeur } from '../data'
import { comparer, compter } from './comparaison'

function l(id: string, position: PositionMajoritaireValeur): LigneGroupe {
  return {
    scrutin_id: id,
    numero: Number(id.slice(1)),
    date: '2025-01-01',
    categorie: 'article',
    membres: 10,
    pour: 0,
    contre: 0,
    abstentions: 0,
    non_votants: 0,
    sans_vote_enregistre: 0,
    position,
    raison_absence: position === 'aucune' ? 'egalite' : null,
    exprimes: 1,
    m: 1,
    majorite_absolue: true,
  }
}

describe('comparer', () => {
  it('distingue même position, positions différentes et absence de position', () => {
    const a = [l('V1', 'pour'), l('V2', 'pour'), l('V3', 'aucune'), l('V4', 'contre')]
    const b = [l('V1', 'pour'), l('V2', 'contre'), l('V3', 'pour')]
    const r = comparer([a, b])
    expect(r.map((x) => [x.scrutin_id, x.type])).toEqual([
      ['V1', 'meme'],
      ['V2', 'differente'],
      ['V3', 'sans'],
    ])
    expect(compter(r)).toEqual({ meme: 1, differente: 1, sans: 1 })
  })
  it('ne garde que les scrutins communs à tous les groupes (3 groupes)', () => {
    const r = comparer([[l('V1', 'pour'), l('V2', 'pour')], [l('V1', 'pour'), l('V2', 'pour')], [l('V2', 'pour')]])
    expect(r.map((x) => x.scrutin_id)).toEqual(['V2'])
  })
  it('exige au moins deux groupes', () => {
    expect(comparer([[l('V1', 'pour')]])).toEqual([])
  })
})
