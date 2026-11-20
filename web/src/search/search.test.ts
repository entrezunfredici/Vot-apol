import { describe, expect, it } from 'vitest'
import type { Categorie, LigneIndex, Resultat } from '../data'
import {
  appliquerFiltres,
  compterFiltresActifs,
  creerRecherche,
  FILTRES_VIDES,
  numerosDePage,
  paginer,
  trier,
} from './index'

function ligne(numero: number, date: string, titre: string, categorie: Categorie = 'amendement', resultat: Resultat = 'adopte'): LigneIndex {
  return {
    id: `VTANR5L17V${numero}`,
    numero,
    date,
    titre,
    categorie: { valeur: categorie, methode: 'regle_titre', a_verifier: true },
    resultat,
    totaux: { pour: 1, contre: 0, abstentions: 0, non_votants: 0, suffrages_exprimes: 1, nombre_votants: 1 },
  }
}

const LIGNES = [
  ligne(1, '2024-10-08', 'la motion de censure déposée par Écologistes', 'motion_censure', 'rejete'),
  ligne(2, '2024-12-02', 'l’article premier de la proposition de loi', 'article'),
  ligne(3, '2025-03-15', 'l’ensemble du projet de loi de finances', 'texte_ensemble'),
  ligne(489, '2025-03-15', 'l’amendement n° 12 sur le logement', 'amendement', 'rejete'),
]

describe('filtres', () => {
  it('sans filtre, tout est retenu', () => {
    expect(appliquerFiltres(LIGNES, FILTRES_VIDES)).toHaveLength(4)
  })

  it('catégorie, résultat et période se combinent (ET)', () => {
    const f = { categories: ['amendement', 'article'] as Categorie[], resultats: ['rejete'] as Resultat[], dateDebut: '2025-01-01' }
    expect(appliquerFiltres(LIGNES, f).map((l) => l.numero)).toEqual([489])
  })

  it('bornes de date incluses', () => {
    const f = { ...FILTRES_VIDES, dateDebut: '2024-12-02', dateFin: '2025-03-15' }
    expect(appliquerFiltres(LIGNES, f).map((l) => l.numero)).toEqual([2, 3, 489])
  })

  it('compte les filtres actifs', () => {
    expect(compterFiltresActifs(FILTRES_VIDES)).toBe(0)
    expect(compterFiltresActifs({ categories: ['article'], resultats: ['adopte'], dateDebut: '2024-01-01' })).toBe(3)
  })
})

describe('tri', () => {
  it('récent : date décroissante puis numéro décroissant', () => {
    expect(trier(LIGNES, 'recent').map((l) => l.numero)).toEqual([489, 3, 2, 1])
  })
  it('ancien et numéro', () => {
    expect(trier(LIGNES, 'ancien').map((l) => l.numero)).toEqual([1, 2, 3, 489])
    expect(trier([...LIGNES].reverse(), 'numero').map((l) => l.numero)).toEqual([1, 2, 3, 489])
  })
  it('ne modifie pas la liste d’origine', () => {
    const avant = LIGNES.map((l) => l.numero)
    trier(LIGNES, 'recent')
    expect(LIGNES.map((l) => l.numero)).toEqual(avant)
  })
})

describe('pagination', () => {
  const items = Array.from({ length: 53 }, (_, i) => i + 1)
  it('découpe et borne la page', () => {
    const p = paginer(items, 3, 25)
    expect(p).toMatchObject({ page: 3, pages: 3, de: 51, a: 53, total: 53 })
    expect(p.items).toHaveLength(3)
    expect(paginer(items, 99, 25).page).toBe(3)
    expect(paginer(items, -4, 25).page).toBe(1)
    expect(paginer(items, Number.NaN, 25).page).toBe(1)
  })
  it('liste vide : une page, aucun élément', () => {
    expect(paginer([], 1, 25)).toMatchObject({ pages: 1, de: 0, a: 0, total: 0 })
  })
  it('numéros de page avec ellipses', () => {
    expect(numerosDePage(1, 3)).toEqual([1, 2, 3])
    expect(numerosDePage(10, 100)).toEqual([1, null, 9, 10, 11, null, 100])
    expect(numerosDePage(1, 100)).toEqual([1, 2, null, 100])
  })
})

describe('recherche', () => {
  const recherche = creerRecherche(LIGNES)
  it('requête vide : aucune restriction', () => {
    expect(recherche.chercher('  ')).toBeNull()
  })
  it('insensible aux accents et à la casse, préfixes admis', () => {
    expect([...(recherche.chercher('ecologistes') ?? [])]).toEqual(['VTANR5L17V1'])
    expect([...(recherche.chercher('FINANC') ?? [])]).toEqual(['VTANR5L17V3'])
  })
  it('tous les mots doivent correspondre (ET)', () => {
    expect([...(recherche.chercher('projet loi finances') ?? [])]).toEqual(['VTANR5L17V3'])
    expect(recherche.chercher('projet censure')?.size).toBe(0)
  })
  it('retrouve un scrutin par son numéro', () => {
    expect(recherche.chercher('489')?.has('VTANR5L17V489')).toBe(true)
  })
})
