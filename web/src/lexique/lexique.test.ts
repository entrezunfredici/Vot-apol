import { describe, expect, it } from 'vitest'
import { L, MOTS_INTERDITS } from './index'

describe('lexique contrôlé', () => {
  it('ne contient aucun mot proscrit', () => {
    const texte = JSON.stringify(L).toLowerCase()
    for (const mot of MOTS_INTERDITS) expect(texte).not.toContain(mot)
  })
})
