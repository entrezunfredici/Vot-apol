// Tous les libellés visibles passent par ici : le test lexique.test.ts interdit les mots proscrits
// (charte de neutralité, DECISIONS.md « Indicateurs sur les groupes ») dans ce fichier et dans le
// code source des pages et composants.
import type { Categorie, Position, PositionMajoritaireValeur, RaisonAbsence, Resultat } from '../data'

export const L = {
  marque: 'Voteapol',
  nav: {
    accueil: 'Accueil',
    scrutins: 'Scrutins',
    groupes: 'Groupes politiques',
    comparateur: 'Comparateur',
    statistiques: 'Statistiques',
    methodologie: 'Méthodologie',
    qualite: 'Qualité des données',
    principale: 'Navigation principale',
    codeSource: 'Code source',
    ouvrirMenu: 'Ouvrir le menu',
    fermerMenu: 'Fermer le menu',
    allerAuContenu: 'Aller au contenu',
  },
  etat: {
    prevueTitre: 'Cette page arrive bientôt',
    prevueAide: 'Elle n’est pas encore disponible.',
    chargement: 'Chargement…',
    erreurTitre: 'Les données n’ont pas pu être chargées.',
    erreurAide: 'Vérifiez votre connexion, puis réessayez.',
    reessayer: 'Réessayer',
    retour: 'Retour',
    introuvableTitre: 'Page introuvable',
    introuvableAide: 'Cette adresse ne correspond à aucune page de Voteapol.',
    aVenir: 'à venir',
  },
  positions: {
    pour: 'Pour',
    contre: 'Contre',
    abstention: 'Abstention',
    non_votant: 'Non-votant',
    resultat: 'Résultat',
  },
  resultat: { adopte: 'Adopté', rejete: 'Rejeté' },
  categorie: {
    texte_ensemble: 'Vote sur l’ensemble d’un texte',
    article: 'Vote sur un article',
    amendement: 'Amendement',
    sous_amendement: 'Sous-amendement',
    motion_censure: 'Motion de censure',
    motion_rejet: 'Motion de rejet',
    autre_motion: 'Autre motion',
    procedure: 'Procédure',
    declaration_gouvernement: 'Déclaration du gouvernement',
    partie_loi_finances: 'Partie d’une loi de finances',
    autre: 'Autre',
    indetermine: 'Non déterminé',
  },
  accueil: {
    badge: 'Données officielles de l’Assemblée nationale, code ouvert',
    titre: 'Comprenez ce que votent vos représentants.',
    intro:
      'Explorez les scrutins publics de l’Assemblée nationale, voyez comment chaque groupe politique a voté et remontez à la source officielle.',
    recherchePlaceholder: 'Rechercher un scrutin par titre ou par numéro…',
    rechercher: 'Rechercher',
    kpiScrutins: 'Scrutins enregistrés',
    kpiScrutinsSous: 'Scrutins publics de la XVIIᵉ législature',
    kpiGroupes: 'Groupes politiques',
    kpiGroupesSous: 'Présents dans au moins un scrutin',
    kpiPeriode: 'Période couverte',
    kpiPeriodeSous: 'Du premier au dernier scrutin',
    kpiSynchro: 'Dernière synchronisation',
    kpiSynchroSous: (heure: string) => `à ${heure} · mise à jour automatique quotidienne`,
    derniers: 'Derniers scrutins',
    voirTous: 'Voir tous les scrutins',
    avertissementTitre: 'À savoir avant de lire les chiffres',
    avertissement:
      'Un scrutin public ne représente pas l’ensemble des votes parlementaires. Voteapol décrit des votes, sans note ni classement : une position « contre » n’est pas une opposition au thème général du texte, et une absence n’est jamais comptée comme une abstention.',
    lireMethodologie: 'Lire la méthodologie',
  },
  scrutins: {
    titre: 'Explorateur de scrutins',
    chapeau: (n: string) =>
      `${n} scrutins recensés — recherchez, filtrez et triez. Les chiffres sont ceux de l’Assemblée nationale.`,
    recherche: 'Rechercher par titre ou numéro',
    recherchePlaceholder: 'Titre, mot-clé ou numéro…',
    filtres: 'Filtres',
    reinitialiser: 'Réinitialiser',
    categorie: 'Nature du vote',
    categorieNote:
      'Les natures de vote sont déduites des titres officiels : celles qui restent à vérifier sont signalées.',
    periode: 'Période',
    du: 'Du',
    au: 'Au',
    resultat: 'Résultat',
    legislature: 'Législature',
    legislatureValeur: 'XVIIᵉ (depuis 2024)',
    trier: 'Trier par',
    triRecent: 'Date (plus récent)',
    triAncien: 'Date (plus ancien)',
    triNumero: 'Numéro de scrutin',
    numero: 'N°',
    voirDetail: (n: number) => `Voir le détail du scrutin ${n}`,
    aucun: 'Aucun scrutin ne correspond à ces critères.',
    aucunAide: 'Modifiez la recherche ou réinitialisez les filtres.',
    affichage: (de: string, a: string, total: string) =>
      `Affichage de ${de} à ${a} sur ${total} scrutins`,
    precedent: 'Page précédente',
    suivant: 'Page suivante',
    page: (n: number) => `Page ${n}`,
    pagination: 'Pagination',
    finListe: 'Fin de la liste.',
    indexChargement: 'Préparation de la recherche…',
    filtresActifs: (n: number) => `${n} filtre${n > 1 ? 's' : ''} appliqué${n > 1 ? 's' : ''}`,
    nombreRetenu: (n: string, total: string) => `${n} scrutins retenus sur ${total}`,
  },
  scrutin: {
    retour: 'Retour à l’explorateur de scrutins',
    numero: 'Scrutin N°',
    repartitionTitre: (n: string) => `Répartition des positions exprimées (${n})`,
    positionsNote:
      'Positions exprimées = pour + contre + abstentions, comme pour les groupes. Les pourcentages sont calculés sur ce total.',
    suffragesOfficiels: (n: string) =>
      `Suffrages exprimés au sens de l’Assemblée nationale (pour + contre) : ${n}. Les abstentions n’en font pas partie.`,
    sur: (partie: string, total: string, pct: number | null) =>
      pct === null ? `${partie} sur ${total}` : `${partie} sur ${total} (${pct} %)`,
    pour: 'Pour',
    contre: 'Contre',
    abstentions: 'Abstentions',
    nonVotants: 'Non-votants',
    horsExprimes: 'hors suffrages exprimés',
    causes: {
      MG: 'membres du gouvernement',
      PSE: 'présidents de séance',
      PAN: 'président de l’Assemblée nationale',
    } as Record<string, string>,
    nonVotantsNote:
      'Un non-votant n’est pas compté comme une abstention. Le nombre de non-votants est celui publié par l’Assemblée nationale.',
    parmiNonVotants: 'Parmi les non-votants :',
    sansVoteTitre: 'Sans vote enregistré',
    sansVote: (n: string) =>
      `${n} membres de groupes n’ont aucun vote enregistré (effectif du groupe moins les positions et non-votants publiés). La source ne dit pas pourquoi : ce n’est pas une abstention.`,
    sansVoteIndisponible:
      'Non calculable : au moins un groupe n’est pas identifié dans la source de ce scrutin.',
    groupesTitre: 'Positions par groupe politique',
    groupesNote: 'Groupes classés par effectif · ouvrez un groupe pour voir le vote de ses députés',
    definition:
      'La position majoritaire d’un groupe est la position la plus fréquente parmi ses positions exprimées (pour, contre, abstention). Les non-votants ne sont pas comptés. En cas d’égalité ou sans vote exprimé, aucune position majoritaire n’est affichée.',
    exprimesSur: (e: string, membres: string) => `${e} exprimés sur ${membres} membres`,
    positionDetail: (m: string, e: string, absolue: boolean) =>
      `${m} sur ${e} exprimés · majorité ${absolue ? 'absolue' : 'relative'}`,
    pasDePosition: 'Pas de position majoritaire',
    egalite: 'Égalité entre plusieurs positions',
    aucunVote: 'Aucun vote exprimé',
    groupeNonIdentifie: 'Groupe non identifié',
    nonCalculee: 'Position majoritaire non calculée',
    groupeNonIdentifieNote:
      'La source ne désigne pas ce groupe : la position majoritaire et le détail ne sont pas calculés.',
    libelleNonResolu: 'libellé non résolu',
    deputeNonResolu: 'député non résolu',
    voteDeputes: (n: number) => `Vote des ${n} députés ayant une position enregistrée`,
    delegation: 'Vote par délégation',
    miseAuPointSignalee: 'Mise au point signalée',
    ouvrirGroupe: (nom: string) => `Afficher le vote des députés du groupe ${nom}`,
    fermerGroupe: (nom: string) => `Masquer le vote des députés du groupe ${nom}`,
    miseAuPointModifie: 'Une mise au point modifie ce résultat.',
    miseAuPointSansChangement:
      'Des mises au point modifient les effectifs sans changer la position majoritaire.',
    voirGroupe: 'Voir la fiche du groupe →',
    miseAuPointChiffres: (p: number, c: number, a: number) =>
      `Après mises au point : pour ${p}, contre ${c}, abstentions ${a}. Les chiffres officiels restent ceux affichés ci-dessus.`,
    miseAuPointTitre: (n: number) => `Mises au point (${n})`,
    miseAuPointIntro:
      'Après le scrutin, des députés ont signalé une position différente de celle enregistrée. Les résultats officiels restent ceux publiés par l’Assemblée nationale et ne sont pas modifiés.',
    colDepute: 'Député',
    colGroupe: 'Groupe',
    colPosition: 'Position enregistrée → position déclarée',
    nonRetrouvee: 'Position enregistrée non retrouvée',
    groupeNonDetermine: 'Groupe non déterminé',
    dysfonctionnementsTitre: (n: number) => `Dysfonctionnements du boîtier de vote (${n})`,
    dysfonctionnementsIntro:
      'Positions déclarées par des députés après un dysfonctionnement de leur boîtier. Elles ne sont jamais appliquées aux effectifs.',
    sourceOfficielle: 'Source officielle — assemblee-nationale.fr',
    sourceNote: 'Un scrutin public ne représente pas nécessairement l’ensemble des votes parlementaires.',
    introuvable: 'Scrutin introuvable',
    introuvableAide: 'Aucun scrutin ne porte ce numéro.',
    provenance: 'Provenance',
    typeVote: 'Type de vote',
    natureVote: 'Nature du vote',
    natureADeduire: 'Nature déduite du titre officiel, à vérifier.',
  },
  pied: {
    donnees: 'Données',
    donneesTexte:
      'Scrutins publics de l’Assemblée nationale, publiés en open data (Licence Ouverte / Open Licence). Voteapol n’est pas affilié à l’Assemblée nationale.',
    neutralite:
      'Voteapol décrit des votes : aucune note, aucun classement, aucune couleur par groupe politique.',
    liens: 'Liens',
    derniereMaj: (date: string) => `Données du ${date}`,
  },
} as const

export const MOTS_INTERDITS = [
  'cohésion',
  'discipline',
  'loyauté',
  'dissident',
  'frondeur',
  'rebelle',
]

export function libelleCategorie(c: Categorie): string {
  return L.categorie[c] ?? L.categorie.indetermine
}

export function libellePosition(p: Position): string {
  return L.positions[p]
}

export function libelleResultat(r: Resultat): string {
  return L.resultat[r]
}

export function libellePositionMajoritaire(p: PositionMajoritaireValeur): string {
  return p === 'aucune' ? L.scrutin.pasDePosition : L.positions[p]
}

export function libelleRaisonAbsence(r: RaisonAbsence | null): string {
  if (r === 'egalite') return L.scrutin.egalite
  if (r === 'aucun_vote_exprime') return L.scrutin.aucunVote
  return L.scrutin.pasDePosition
}
