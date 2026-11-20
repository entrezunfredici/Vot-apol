import { describe, expect, it } from 'vitest'
import { dateCourte, dateLongue, nombre, periode, pourcentage, surTotal, titreAffiche } from './format'

describe('format', () => {
  it('nombre : séparateur de milliers français', () => {
    expect(nombre(9895).replace(/\s/g, ' ')).toBe('9 895')
    expect(nombre(0)).toBe('0')
  })

  it('dates : lues comme dates civiles, sans décalage de fuseau', () => {
    expect(dateLongue('2026-10-21')).toBe('21 octobre 2026')
    expect(dateLongue('2024-01-01')).toBe('1 janvier 2024')
    expect(dateCourte('2026-10-21')).toMatch(/^21 oct\.? 2026$/)
    expect(dateLongue('pas une date')).toBe('pas une date')
  })

  it('période : une seule année ou deux', () => {
    expect(periode('2024-10-08', '2026-11-12')).toBe('2024–2026')
    expect(periode('2024-10-08', '2024-12-01')).toBe('2024')
  })

  it('pourcentage : entier arrondi, nul si le dénominateur est nul', () => {
    expect(pourcentage(334, 564)).toBe(59)
    expect(pourcentage(0, 10)).toBe(0)
    expect(pourcentage(5, 0)).toBeNull()
  })

  it('surTotal : toujours avec le dénominateur', () => {
    expect(surTotal(334, 564)).toMatch(/^334 sur 564$/)
  })

  it('titreAffiche : seule la première lettre change', () => {
    expect(titreAffiche('l’article 8 du projet de loi')).toBe('L’article 8 du projet de loi')
    expect(titreAffiche('  élargissement…')).toBe('Élargissement…')
    expect(titreAffiche('')).toBe('')
  })
})
