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
  groupes: {
    titre: 'Groupes politiques',
    chapeau: (n: string) =>
      `${n} groupes politiques de la XVIIᵉ législature. Un groupe parlementaire n’est pas un parti.`,
    ordre: 'Groupes classés par ordre alphabétique, sans classement ni note.',
    definition:
      'L’affiliation retenue est celle enregistrée au moment de chaque scrutin, pas l’affiliation actuelle des députés. Deux groupes peuvent porter le même sigle (groupe renommé) : ils restent distincts.',
    scrutinsIdentifie: (n: string) => `${n} scrutins où le groupe est identifié`,
    personnes: (avec: string) => `${avec} personnes distinctes ayant un vote enregistré`,
    positionsTitre: 'Scrutins par position majoritaire',
    voirFiche: (nom: string) => `Voir la fiche du groupe ${nom}`,
    aucun: 'Aucun groupe disponible.',
    retour: 'Retour aux groupes politiques',
    introuvable: 'Groupe introuvable',
    introuvableAide: 'Aucun groupe ne porte cet identifiant.',
    identifiant: 'Identifiant',
    kpiScrutins: 'Scrutins du groupe',
    kpiScrutinsSous: 'Scrutins où le groupe est identifié dans la source',
    kpiPeriode: 'Période',
    kpiPeriodeSous: 'Premier et dernier scrutin du groupe',
    kpiMembres: 'Effectif au dernier scrutin',
    kpiMembresSous: (n: number) => `Au scrutin n° ${n}`,
    repartitionTitre: 'Répartition des scrutins selon la position majoritaire du groupe',
    repartitionNote:
      'Nombre de scrutins, sur le total des scrutins du groupe. Ce n’est pas un score : une position « contre » n’est pas une opposition au thème général du texte.',
    sansPositionNote:
      'Pas de position majoritaire en cas d’égalité entre positions ou lorsqu’aucun membre n’a exprimé de vote.',
    egalite: 'Égalité entre positions',
    aucunVote: 'Aucun vote exprimé',
    historiqueTitre: 'Historique des scrutins',
    historiqueNote:
      'Pour chaque scrutin : la position majoritaire, calculée par Voteapol sur les positions exprimées, et la participation du groupe. Les non-votants et les membres sans vote enregistré ne sont pas des abstentions.',
    colScrutin: 'Scrutin',
    colNature: 'Nature',
    colPosition: 'Position majoritaire',
    colParticipation: 'Votes exprimés',
    exprimesSur: (e: string, membres: string) => `${e} sur ${membres} membres`,
    partMajoritaire: (m: string, e: string, absolue: boolean) =>
      `${m} sur ${e} exprimés · majorité ${absolue ? 'absolue' : 'relative'}`,
    filtreNature: 'Nature du vote',
    filtreNatureToutes: 'Toutes',
    filtrePosition: 'Position majoritaire',
    filtrePositionToutes: 'Toutes',
    filtrePositionAucune: 'Pas de position majoritaire',
    nombreRetenu: (n: string, total: string) => `${n} scrutins retenus sur ${total}`,
    aucunScrutin: 'Aucun scrutin ne correspond à ces critères.',
    reinitialiser: 'Réinitialiser',
  },
  stats: {
    titre: 'Statistiques',
    chapeau:
      'Effectifs et positions majoritaires par groupe politique, sur l’ensemble des scrutins ou sur une sélection. Ce sont des décomptes, pas des notes : aucun classement n’est proposé.',
    selection: 'Sélection de scrutins',
    toutes: 'Tous les scrutins',
    categorie: (c: string) => `Nature : ${c}`,
    annee: (a: string) => `Année ${a}`,
    nombreRetenu: (n: string) => `${n} scrutins retenus`,
    filtreApplique: (f: string) => `Filtre appliqué : ${f}`,
    avertissement:
      'Les scrutins sont additionnés comme des votes distincts, pas comme des lois distinctes. Les effectifs sur plusieurs scrutins sont des membres-scrutins : un même député compte une fois par scrutin.',
    ordre: 'Groupes classés par ordre alphabétique.',
    effectifsTitre: 'Positions enregistrées par groupe',
    effectifsNote:
      'Membres-scrutins : somme, scrutin par scrutin, des effectifs du groupe. Les non-votants et les membres sans vote enregistré ne sont pas des abstentions.',
    colGroupe: 'Groupe',
    colScrutins: 'Scrutins',
    colMembres: 'Membres-scrutins',
    colPour: 'Pour',
    colContre: 'Contre',
    colAbstentions: 'Abstentions',
    colNonVotants: 'Non-votants',
    colSansVote: 'Sans vote enregistré',
    colPersonnes: 'Personnes avec un vote',
    exclus: (n: string) => `${n} scrutins écartés : groupe non identifié dans la source`,
    positionsTitre: 'Scrutins selon la position majoritaire du groupe',
    positionsNote:
      'Nombre de scrutins où chaque position est majoritaire dans le groupe. Égalité et absence de vote exprimé ne donnent pas de position majoritaire.',
    colEgalite: 'Égalité',
    colAucunVote: 'Aucun vote exprimé',
    partTitre: 'Part de la position majoritaire dans le groupe',
    partNote:
      'Pour chaque scrutin, la part des positions exprimées du groupe qui suivent sa position majoritaire. Les scrutins sont répartis par tranche, en nombre de scrutins : ce n’est pas une moyenne.',
    sur: (n: string, total: string) => `${n} sur ${total}`,
    aucunGroupe: 'Aucun groupe pour cette sélection.',
    voirFiche: 'Fiche',
  },
  qualite: {
    titre: 'Qualité des données',
    chapeau:
      'Ce que Voteapol a contrôlé avant de publier, ce qui reste imparfait dans la source officielle, et ce qui a changé depuis la dernière publication.',
    statutTitre: 'Réconciliation des totaux',
    statutOk: 'Tous les totaux de la source sont cohérents entre eux : aucun écart constaté.',
    statutEcarts: (n: string) =>
      `Les totaux sont cohérents, sauf ${n} écart${n === '1' ? '' : 's'} constaté${n === '1' ? '' : 's'} dans la source officielle. Ils sont listés ci-dessous, jamais corrigés ni masqués.`,
    scrutins: 'Scrutins publiés',
    donneesDu: 'Données du',
    archive: 'Empreinte SHA-256 de l’archive source',
    ecartsTitre: 'Écarts connus dans la source',
    ecartsAucun: 'Aucun écart connu.',
    colControle: 'Contrôle',
    colScrutin: 'Scrutin',
    colAttendu: 'Attendu',
    colObtenu: 'Obtenu',
    colMotif: 'Constat',
    valideLe: (d: string) => `Validé le ${d}`,
    classificationTitre: 'Nature des votes',
    classificationNote:
      'La nature d’un vote (amendement, article…) est déduite du titre officiel par des règles explicites : ce n’est pas une certitude.',
    aVerifier: (a: string, total: string) => `${a} scrutins sur ${total} ont une nature à vérifier`,
    indetermine: (n: string) => `${n} scrutins de nature non déterminée`,
    nomsTitre: 'Noms non résolus',
    nomsGroupes: (n: string) => `${n} groupes sans libellé`,
    nomsDeputes: (n: string) => `${n} députés sans nom`,
    nomsNote: 'Un nom non résolu s’affiche « libellé non résolu » avec son identifiant : aucun nom n’est inventé.',
    modificationsTitre: 'Changements depuis la publication précédente',
    modificationsAucune: 'Pas de publication précédente à comparer.',
    nouveaux: (n: string) => `${n} nouveaux scrutins`,
    supprimes: (n: string) => `${n} scrutins supprimés`,
    chiffres: (n: string) => `${n} scrutins dont des chiffres officiels ont changé`,
    autres: (n: string) => `${n} scrutins modifiés sans changement de chiffres`,
    listeLimitee: 'Les listes d’identifiants sont limitées à 200 ; les nombres sont exacts.',
    voirMethodo: 'Lire la méthodologie',
  },
  methodo: {
    titre: 'Méthodologie',
    chapeau:
      'Comment Voteapol calcule ce qu’il affiche. Tout chiffre du site peut être retrouvé avec ces définitions et vérifié sur la page officielle du scrutin.',
    sommaire: 'Sur cette page',
    sections: [
      {
        id: 'position',
        titre: 'Position majoritaire d’un groupe',
        paragraphes: [
          'Pour un groupe et un scrutin, on compte P (pour), C (contre) et A (abstentions). E = P + C + A est le nombre de positions exprimées. Les non-votants ne sont pas comptés dans E : une absence n’est pas une abstention.',
          'La position majoritaire est la plus fréquente parmi les positions exprimées (majorité relative). Si plusieurs positions sont à égalité, ou si E vaut 0, il n’y a pas de position majoritaire et le site indique pourquoi.',
          'La majorité est dite absolue lorsque la position réunit plus de la moitié des positions exprimées, relative sinon. La position n’est jamais affichée seule : elle l’est avec ses effectifs, par exemple « 12 sur 14 exprimés ».',
          'Voteapol recalcule cette position à partir des décomptes. La valeur « position majoritaire » fournie par la source officielle n’est pas utilisée : elle contredit les décomptes dans plusieurs centaines de cas.',
          'Aucune interprétation : « contre » signifie « a voté contre sur ce scrutin », pas une opposition au thème général du texte.',
        ],
      },
      {
        id: 'part',
        titre: 'Part de la position majoritaire',
        paragraphes: [
          'Pour un scrutin, il s’agit de « m sur E » : le nombre de membres ayant voté comme la position majoritaire, sur les positions exprimées. Ce n’est pas un score : aucun seuil, aucun qualificatif, et les groupes ne sont jamais classés selon cet indicateur.',
          'Sur plusieurs scrutins, le site affiche une répartition brute en nombre de scrutins par tranche, jamais une moyenne unique.',
        ],
      },
      {
        id: 'participation',
        titre: 'Participation au vote enregistrée',
        paragraphes: [
          'Ce n’est pas une présence physique : un vote par délégation compte comme une position exprimée. Le site indique E membres sur l’effectif du groupe, et les non-votants à part, avec leur cause lorsqu’elle est connue.',
          'La source ne liste pas les députés sans vote. Leur nombre se déduit : effectif moins (pour + contre + abstentions + non-votants). Il est affiché sous « Sans vote enregistré », jamais comme des absents (la source ne dit pas pourquoi) ni comme des abstentions.',
          'Les non-votants de la source sont les personnes dont la fonction empêche de voter : membres du gouvernement, présidents de séance, président de l’Assemblée nationale.',
        ],
      },
      {
        id: 'mises-au-point',
        titre: 'Mises au point',
        paragraphes: [
          'Après un scrutin, un député peut signaler qu’il souhaitait voter autrement. Les chiffres principaux restent les chiffres officiels, qui ne tiennent pas compte de ces signalements.',
          'Quand un scrutin en comporte, la fiche les affiche dans un encart distinct. Si une mise au point change la position majoritaire d’un groupe, la ligne du groupe le signale avec les effectifs corrigés, jamais présentés comme le résultat officiel.',
        ],
      },
      {
        id: 'classification',
        titre: 'Nature des votes',
        paragraphes: [
          'La nature d’un vote (amendement, article, motion…) est déduite du titre officiel par des règles explicites et versionnées. Ce n’est pas une certitude : les natures à vérifier sont signalées.',
        ],
      },
      {
        id: 'garanties',
        titre: 'Garanties d’exactitude',
        liste: [
          'Aucune donnée inventée : une valeur absente ou non résolue s’affiche comme telle. Seuls les identifiants officiels font foi.',
          'Les totaux sont vérifiés à chaque import (pour + contre, votants, somme des groupes, votes nominatifs). Un écart n’est jamais corrigé en silence ; un écart nouveau interrompt la publication.',
          'Un script indépendant du pipeline relit des fichiers sources tirés au hasard et compare chaque chiffre publié.',
          'Chaque scrutin porte son fichier source, son empreinte SHA-256 et un lien vers la page officielle.',
          'Un changement anormal entre deux publications attend une validation humaine.',
        ],
      },
      {
        id: 'neutralite',
        titre: 'Garanties de neutralité',
        liste: [
          'Voteapol ne note et n’évalue aucun élu ni groupe, et ne propose aucun classement.',
          'Ordre alphabétique ou chronologique par défaut, jamais par « importance ». Aucun scrutin n’est mis en avant à la main.',
          'Les couleurs de vote (pour, contre, abstention, non-votant) sont les seules couleurs sémantiques. Aucune couleur n’est associée à un groupe politique.',
          'Les textes de l’interface suivent un lexique descriptif contrôlé par un test automatique.',
          'Les scrutins publics ne représentent qu’une partie de l’activité parlementaire.',
        ],
      },
    ],
    casTitre: 'Cas limites',
    casNote: 'Exemples chiffrés testés dans le code.',
    casColonnes: ['Pour', 'Contre', 'Abstentions', 'Résultat'],
    cas: [
      ['12', '2', '0', 'Pour, 12 sur 14, majorité absolue'],
      ['5', '6', '49', 'Abstention, 49 sur 60, majorité absolue'],
      ['6', '6', '1', 'Pas de position majoritaire (égalité)'],
      ['0', '0', '0', 'Pas de position majoritaire (aucun vote exprimé)'],
      ['3', '2', '2', 'Pour, 3 sur 7, majorité relative'],
    ],
    correctionTitre: 'Signaler une erreur',
    correction: 'Vous avez repéré un chiffre ou un libellé qui semble inexact ? Signalez-le sur le dépôt public du projet ; les corrections publiées sont datées.',
    correctionLien: 'Ouvrir un signalement',
    qualiteLien: 'Voir la qualité des données',
  },
  comparateur: {
    titre: 'Comparateur de groupes',
    chapeau:
      'Comparez la position majoritaire de 2 ou 3 groupes sur les scrutins où ils sont tous identifiés. C’est un décompte, pas un jugement : « positions différentes » ne dit rien du fond des textes.',
    choix: 'Groupes à comparer',
    choixAide: 'Choisissez 2 ou 3 groupes.',
    maximum: 'Trois groupes au maximum.',
    pasAssez: 'Choisissez au moins deux groupes pour lancer la comparaison.',
    communs: (n: string) => `${n} scrutins où les groupes sont tous identifiés`,
    memePosition: 'Même position majoritaire',
    positionsDifferentes: 'Positions majoritaires différentes',
    sansPosition: 'Pas de position majoritaire pour au moins un groupe',
    sur: (n: string, total: string) => `${n} sur ${total}`,
    resumeTitre: 'Résumé',
    resumeNote:
      'Chaque scrutin est compté une fois. Un scrutin sans position majoritaire pour l’un des groupes (égalité ou aucun vote exprimé) n’est ni « même position » ni « positions différentes ».',
    listeTitre: 'Scrutins',
    filtre: 'Afficher',
    filtreTous: 'Tous les scrutins',
    colScrutin: 'Scrutin',
    colGroupe: 'Position majoritaire',
    categorieMemePos: 'même position',
    categorieDiff: 'positions différentes',
    categorieSans: 'sans position pour au moins un groupe',
    aucun: 'Aucun scrutin ne correspond à ce filtre.',
    retenus: (n: string, total: string) => `${n} scrutins retenus sur ${total}`,
    aucunCommun: 'Ces groupes n’ont aucun scrutin en commun.',
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
