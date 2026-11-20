import { onMounted, ref, shallowRef, type Ref } from 'vue'

export interface EtatAsync<T> {
  donnees: Ref<T | null>
  erreur: Ref<Error | null>
  chargement: Ref<boolean>
  recharger: () => Promise<void>
}

/** Charge une donnée au montage et expose les trois états obligatoires : chargement, erreur, résultat. */
export function useAsync<T>(chargeur: () => Promise<T>): EtatAsync<T> {
  const donnees = shallowRef<T | null>(null)
  const erreur = ref<Error | null>(null)
  const chargement = ref(true)

  async function recharger(): Promise<void> {
    chargement.value = true
    erreur.value = null
    try {
      donnees.value = await chargeur()
    } catch (e) {
      erreur.value = e instanceof Error ? e : new Error(String(e))
    } finally {
      chargement.value = false
    }
  }

  onMounted(recharger)
  return { donnees, erreur, chargement, recharger }
}
