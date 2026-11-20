// Types du contrat ETL → site (`/data/v1/`), d'après docs/data-dictionary.md (schéma v1).
// Source de vérité exécutable : etl/src/etl/algos/alg11_schemas.py.

export type Position = 'pour' | 'contre' | 'abstention' | 'non_votant'
export type PositionMajoritaireValeur = 'pour' | 'contre' | 'abstention' | 'aucune'
export type RaisonAbsence = 'aucun_vote_exprime' | 'egalite'
export type Resultat = 'adopte' | 'rejete'

export type Categorie =
  | 'texte_ensemble'
  | 'article'
  | 'amendement'
  | 'sous_amendement'
  | 'motion_censure'
  | 'motion_rejet'
  | 'autre_motion'
  | 'procedure'
  | 'declaration_gouvernement'
  | 'partie_loi_finances'
  | 'autre'
  | 'indetermine'

export interface Meta {
  schema: string
  nombre_scrutins: number
  nombre_groupes: number
  premiere_date: string
  derniere_date: string
  donnees_du: string
  version_donnees: string
  archive_sha256: string
  type_empreinte: string
  version_etl: string
  version_regles_classification: string
}

export interface Totaux {
  pour: number
  contre: number
  abstentions: number
  non_votants: number
  suffrages_exprimes: number
  nombre_votants: number
}

export interface CategorieIndex {
  valeur: Categorie
  methode: string
  a_verifier: boolean
}

export interface LigneIndex {
  id: string
  numero: number
  date: string
  titre: string
  categorie: CategorieIndex
  resultat: Resultat
  totaux: Totaux
}

export interface FragmentIndex {
  mois: string
  nombre_scrutins: number
  fichier: string
}

export interface FichierIndex {
  fragments: FragmentIndex[]
}

export interface FragmentScrutins {
  mois: string
  scrutins: LigneIndex[]
}

export interface PositionMajoritaire {
  position: PositionMajoritaireValeur
  raison_absence: RaisonAbsence | null
  exprimes: number
  m: number
  majorite_absolue: boolean
}

export interface CorrectionMiseAuPoint {
  pour_corrige: number
  contre_corrige: number
  abstentions_corrigees: number
  position_officielle: PositionMajoritaireValeur
  position_corrigee: PositionMajoritaireValeur
  raison_absence_corrigee: RaisonAbsence | null
  change_position_majoritaire: boolean
  nb_mises_au_point: number
}

export interface GroupeScrutin {
  rang: number
  groupe_id: string | null
  ventilation_disponible: boolean
  membres: number
  pour: number
  contre: number
  abstentions: number
  non_votants: number
  sans_vote_enregistre: number | null
  position_majoritaire: PositionMajoritaire | null
  correction_mise_au_point: CorrectionMiseAuPoint | null
}

/** [depute_id, groupe_rang, position, par_delegation (0 ou 1), cause (MG, PSE, PAN) ou null] */
export type Vote = [string, number, Position, 0 | 1, string | null]

export interface MiseAuPoint {
  depute_id: string
  groupe_rang: number | null
  groupe_id: string | null
  position_initiale: Position | null
  position_declaree: Position
  par_delegation: number
  statut: 'rattachee' | 'introuvable'
  effet: 'sans_effet' | 'modifie_position' | null
}

export interface Scrutin {
  id: string
  numero: number
  date: string
  titre: string
  type_vote: { code: string; libelle: string }
  resultat: Resultat
  categorie: CategorieIndex & { confiance: string }
  source: { fichier: string; sha256: string; archive_sha256: string; lien_officiel: string }
  totaux: Totaux & { sans_vote_enregistre: number | null }
  groupes: GroupeScrutin[]
  votes: Vote[]
  mises_au_point: MiseAuPoint[]
  dysfonctionnements: MiseAuPoint[]
}

export interface GroupeListe {
  id: string
  libelle: string | null
  sigle: string | null
  nombre_scrutins: number
}

export interface FichierGroupes {
  groupes: GroupeListe[]
}

export interface DeputeListe {
  id: string
  nom: string | null
  prenom: string | null
  civilite: string | null
}

export interface FichierDeputes {
  deputes: DeputeListe[]
}

/** Colonnes de `groupes/<id>.json`, dans l'ordre (nommées une seule fois dans le fichier). */
export const COLONNES_GROUPE = [
  'scrutin_id',
  'numero',
  'date',
  'categorie',
  'membres',
  'pour',
  'contre',
  'abstentions',
  'non_votants',
  'sans_vote_enregistre',
  'position',
  'raison_absence',
  'exprimes',
  'm',
  'majorite_absolue',
] as const

/** Format compact : une ligne = un tableau dans l'ordre de `colonnes`. */
export interface FichierGroupe {
  groupe_id: string
  libelle: string | null
  sigle: string | null
  colonnes: string[]
  scrutins: (string | number | boolean | null)[][]
}

/** Une ligne de l'historique d'un groupe : ce que le groupe a fait dans un scrutin. */
export interface LigneGroupe {
  scrutin_id: string
  numero: number
  date: string
  categorie: Categorie
  membres: number
  pour: number
  contre: number
  abstentions: number
  non_votants: number
  sans_vote_enregistre: number | null
  position: PositionMajoritaireValeur
  raison_absence: RaisonAbsence | null
  exprimes: number
  m: number
  majorite_absolue: boolean
}

export interface StatsGroupe {
  groupe_id: string
  nb_scrutins: number
  nb_scrutins_exclus_groupe_non_identifie: number
  membres_scrutins: number
  personnes_exprimees: number
  personnes_avec_vote: number
  pour: number
  contre: number
  abstentions: number
  non_votants: number
  sans_vote_enregistre: number
  exprimes: number
  scrutins_par_position_majoritaire: {
    pour: number
    contre: number
    abstention: number
    egalite: number
    aucun_vote_exprime: number
  }
  repartition_part_majoritaire: number[]
}

export interface FichierStats {
  bornes: number[]
  libelles_tranches: string[]
  selections: { id: string; filtres: string; nombre_scrutins: number; groupes: StatsGroupe[] }[]
}

export interface EcartConnu {
  controle: string
  scrutin_id: string
  detail: string | null
  attendu: number | string | null
  obtenu: number | string | null
  motif: string
  valide_le: string
}

export interface ModificationsPubliees {
  nouveaux: number
  supprimes: string[]
  nombre_supprimes: number
  modifies_chiffres: string[]
  nombre_modifies_chiffres: number
  modifies_autres: string[]
  nombre_modifies_autres: number
}

export interface Qualite {
  schema: string
  statut_reconciliation: 'ok' | 'ecarts_connus'
  nombre_scrutins: number
  archive_sha256: string
  donnees_du: string
  ecarts_connus: EcartConnu[]
  classification: { par_categorie: Record<string, number>; a_verifier: number; indetermine: number }
  noms_non_resolus: { groupes: number; deputes: number }
  modifications: ModificationsPubliees | null
}
