// Mise en forme (fr-FR). Fonctions pures, testées dans format.test.ts.

const NOMBRE = new Intl.NumberFormat('fr-FR')

/** 12345 → « 12 345 » (espace insécable). */
export function nombre(n: number): string {
  return NOMBRE.format(n)
}

function dateLocale(iso: string): Date | null {
  // « AAAA-MM-JJ » lu comme une date civile : aucun décalage de fuseau.
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return null
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
}

/** « 2026-10-21 » → « 21 octobre 2026 ». */
export function dateLongue(iso: string): string {
  const d = dateLocale(iso)
  return d ? d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) : iso
}

/** « 2026-10-21 » → « 21 oct. 2026 ». */
export function dateCourte(iso: string): string {
  const d = dateLocale(iso)
  return d ? d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }) : iso
}

/** Date et heure de synchronisation, lues dans `meta.json` (ISO avec fuseau). */
export function dateHeure(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Parties « jj/mm/aaaa » et « hh:mm » d'une date ISO avec fuseau. */
export function dateEtHeure(iso: string): { date: string; heure: string } {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return { date: iso, heure: '' }
  return {
    date: d.toLocaleDateString('fr-FR'),
    heure: d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
  }
}

/**
 * Titre officiel affiché avec une majuscule initiale : la source le formule à la suite de « Scrutin
 * sur … » (« l'article 8 du projet… »). Seule la première lettre change ; rien n'est réécrit.
 */
export function titreAffiche(titre: string): string {
  const t = titre.trim()
  return t ? t.charAt(0).toLocaleUpperCase('fr-FR') + t.slice(1) : t
}

/** « 2024-10-08 » et « 2026-11-18 » → « 2024–2026 ». */
export function periode(debut: string, fin: string): string {
  const a = debut.slice(0, 4)
  const b = fin.slice(0, 4)
  return a === b ? a : `${a}–${b}`
}

/**
 * Part en pourcentage entier, toujours accompagnée de son dénominateur par l'appelant.
 * Dénominateur nul : `null` (on n'affiche pas « 0 % » d'une population vide).
 */
export function pourcentage(partie: number, total: number): number | null {
  if (total <= 0) return null
  return Math.round((partie / total) * 100)
}

/** « 334 sur 564 » : un effectif toujours présenté avec son dénominateur. */
export function surTotal(partie: number, total: number): string {
  return `${nombre(partie)} sur ${nombre(total)}`
}
