import { describe, expect, it } from 'vitest'
import { FormatGroupeInvalide, lireLignesGroupe } from './groupe'
import { COLONNES_GROUPE, type FichierGroupe } from './types'

const fichier = (colonnes: string[], scrutins: FichierGroupe['scrutins']): FichierGroupe => ({
  groupe_id: 'PO1',
  libelle: null,
  sigle: null,
  colonnes,
  scrutins,
})

describe('lireLignesGroupe', () => {
  it('met à plat une ligne compacte en objet nommé', () => {
    const [l] = lireLignesGroupe(
      fichier(
        [...COLONNES_GROUPE],
        [['VTANR5L17V5', 5, '2024-10-15', 'motion_rejet', 10, 1, 1, 0, 0, 8, 'aucune', 'egalite', 2, 1, false]],
      ),
    )
    expect(l).toMatchObject({ numero: 5, position: 'aucune', raison_absence: 'egalite', exprimes: 2, m: 1, majorite_absolue: false })
  })
  it('refuse des colonnes différentes du contrat', () => {
    expect(() => lireLignesGroupe(fichier(['a'], []))).toThrow(FormatGroupeInvalide)
  })
  it('refuse une ligne de mauvaise longueur', () => {
    expect(() => lireLignesGroupe(fichier([...COLONNES_GROUPE], [['x']]))).toThrow(FormatGroupeInvalide)
  })
})
