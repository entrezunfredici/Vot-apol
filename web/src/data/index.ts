// Seul endroit autorisé à faire fetch sur /data/v1/… (contrat ETL → front, cahier §8).
import type {
  DeputeListe,
  FichierDeputes,
  FichierGroupes,
  FichierIndex,
  FichierGroupe,
  FichierStats,
  FragmentScrutins,
  LigneGroupe,
  GroupeListe,
  LigneIndex,
  Meta,
  Qualite,
  Scrutin,
  StatsGroupe,
} from './types'
import { lireLignesGroupe } from './groupe'

export * from './types'
export { FormatGroupeInvalide, lireLignesGroupe } from './groupe'

const BASE = '/data/v1'

/** Erreur de chargement : `status` vaut 0 quand le réseau lui-même a échoué. */
export class ErreurChargement extends Error {
  constructor(
    public readonly chemin: string,
    public readonly status: number,
  ) {
    super(`Chargement impossible : ${chemin} (${status || 'réseau'})`)
  }
}

export async function getJson<T>(path: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}/${path}`)
  } catch {
    throw new ErreurChargement(path, 0)
  }
  if (!res.ok) throw new ErreurChargement(path, res.status)
  try {
    return (await res.json()) as T
  } catch {
    throw new ErreurChargement(path, res.status)
  }
}

// Un fichier n'est chargé qu'une fois par visite ; un échec n'est jamais mémorisé (nouvelle tentative).
const cache = new Map<string, Promise<unknown>>()

function memo<T>(path: string): Promise<T> {
  let p = cache.get(path) as Promise<T> | undefined
  if (!p) {
    p = getJson<T>(path)
    cache.set(path, p)
    p.catch(() => cache.delete(path))
  }
  return p
}

export const chargerMeta = () => memo<Meta>('meta.json')
export const chargerScrutin = (id: string) => memo<Scrutin>(`scrutins/${id}.json`)

export async function chargerGroupes(): Promise<Map<string, GroupeListe>> {
  const f = await memo<FichierGroupes>('groupes.json')
  return new Map(f.groupes.map((g) => [g.id, g]))
}

/** L'historique d'un groupe : une ligne par scrutin, du plus petit numéro au plus grand. */
export async function chargerGroupe(
  id: string,
): Promise<{ groupe_id: string; libelle: string | null; sigle: string | null; lignes: LigneGroupe[] }> {
  const f = await memo<FichierGroupe>(`groupes/${id}.json`)
  return { groupe_id: f.groupe_id, libelle: f.libelle, sigle: f.sigle, lignes: lireLignesGroupe(f) }
}

/** Les agrégats sur tous les scrutins (sélection « toutes » de `stats.json`), par identifiant de groupe. */
export const chargerQualite = () => memo<Qualite>('qualite.json')
export const chargerStats = () => memo<FichierStats>('stats.json')

export async function chargerStatsGroupes(): Promise<Map<string, StatsGroupe>> {
  const f = await chargerStats()
  const toutes = f.selections.find((s) => s.id === 'toutes')
  return new Map((toutes?.groupes ?? []).map((g) => [g.groupe_id, g]))
}

export async function chargerDeputes(): Promise<Map<string, DeputeListe>> {
  const f = await memo<FichierDeputes>('deputes.json')
  return new Map(f.deputes.map((d) => [d.id, d]))
}

/** Les lignes de l'index d'un ou plusieurs mois (fragments `scrutins-index/AAAA-MM.json`). */
export async function chargerLignesIndex(fichiers: string[]): Promise<LigneIndex[]> {
  const fragments = await Promise.all(fichiers.map((f) => memo<FragmentScrutins>(f)))
  return fragments.flatMap((f) => f.scrutins)
}

/** L'index complet : tous les fragments, du plus ancien au plus récent. */
export async function chargerIndexComplet(): Promise<LigneIndex[]> {
  const index = await memo<FichierIndex>('scrutins-index.json')
  return chargerLignesIndex(index.fragments.map((f) => f.fichier))
}

/** Les derniers scrutins : charge les fragments les plus récents jusqu'à en avoir assez. */
export async function chargerDerniersScrutins(nombre: number): Promise<LigneIndex[]> {
  const index = await memo<FichierIndex>('scrutins-index.json')
  const lignes: LigneIndex[] = []
  for (const fragment of [...index.fragments].reverse()) {
    lignes.push(...(await chargerLignesIndex([fragment.fichier])))
    if (lignes.length >= nombre) break
  }
  return trierRecents(lignes).slice(0, nombre)
}

function trierRecents(lignes: LigneIndex[]): LigneIndex[] {
  return [...lignes].sort((a, b) => b.date.localeCompare(a.date) || b.numero - a.numero)
}
