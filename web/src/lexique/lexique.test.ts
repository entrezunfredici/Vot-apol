import { describe, expect, it } from 'vitest'
import { L, MOTS_INTERDITS } from './index'

// Code source des pages, composants et modules, lu tel quel (sans dépendance à Node).
const SOURCES = import.meta.glob(['../**/*.vue', '../**/*.ts', '!../**/*.test.ts'], {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>
const chemins = Object.keys(SOURCES)

describe('lexique contrôlé', () => {
  it('ne contient aucun mot proscrit', () => {
    const texte = JSON.stringify(L).toLowerCase()
    for (const mot of MOTS_INTERDITS) expect(texte).not.toContain(mot)
  })

  it('aucun mot proscrit dans le code source des pages et composants', () => {
    expect(chemins.length).toBeGreaterThan(10)
    for (const chemin of chemins) {
      // le fichier qui définit la liste des mots interdits la cite forcément
      if (chemin === './index.ts') continue
      const texte = SOURCES[chemin].toLowerCase()
      for (const mot of MOTS_INTERDITS) expect(texte, `${mot} dans ${chemin}`).not.toContain(mot)
    }
  })

  it('les couleurs de vote ne sont associées qu’à voteStyles.ts (charte de neutralité)', () => {
    const interdites = /(?:bg|text|border|fill|stroke)-(?:pour|contre|abstention|nonvotant)\b/
    for (const chemin of chemins) {
      if (chemin.endsWith('voteStyles.ts')) continue
      expect(SOURCES[chemin], chemin).not.toMatch(interdites)
    }
  })

  it('aucune couleur codée en dur dans les composants et pages', () => {
    for (const chemin of chemins.filter((c) => c.endsWith('.vue'))) {
      expect(SOURCES[chemin], chemin).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    }
  })
})
