<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import ScrutinRow from '../components/ScrutinRow.vue'
import SkeletonRows from '../components/SkeletonRows.vue'
import { useAsync } from '../composables/useAsync'
import { chargerIndexComplet, type Categorie, type Resultat } from '../data'
import { nombre } from '../format'
import { L, libelleCategorie, libelleResultat } from '../lexique'
import {
  appliquerFiltres,
  compterFiltresActifs,
  creerRecherche,
  numerosDePage,
  paginer,
  trier,
  type Filtres,
  type Recherche,
  type Tri,
} from '../search'

const TAILLE_PAGE = 25
const CATEGORIES: Categorie[] = [
  'texte_ensemble',
  'article',
  'amendement',
  'sous_amendement',
  'motion_censure',
  'motion_rejet',
  'autre_motion',
  'procedure',
  'declaration_gouvernement',
  'partie_loi_finances',
  'autre',
  'indetermine',
]
const RESULTATS: Resultat[] = ['adopte', 'rejete']
const TRIS: Tri[] = ['recent', 'ancien', 'numero']

const route = useRoute()
const router = useRouter()
const index = useAsync(chargerIndexComplet)
const recherche = shallowRef<Recherche | null>(null)
const filtresMobileOuverts = ref(false)

watch(
  () => index.donnees.value,
  (lignes) => {
    recherche.value = lignes ? creerRecherche(lignes) : null
  },
  { immediate: true },
)

// --- État dans l'adresse : une recherche filtrée se partage par son lien --------------------------

function texte(cle: string): string {
  const v = route.query[cle]
  return typeof v === 'string' ? v : ''
}
function liste<T extends string>(cle: string, permis: readonly T[]): T[] {
  return texte(cle)
    .split(',')
    .filter((v): v is T => (permis as readonly string[]).includes(v))
}

const requete = computed(() => texte('q'))
const filtres = computed<Filtres>(() => ({
  dateDebut: texte('du') || undefined,
  dateFin: texte('au') || undefined,
  categories: liste('nature', CATEGORIES),
  resultats: liste('resultat', RESULTATS),
}))
const tri = computed<Tri>(() => (TRIS as string[]).includes(texte('tri')) ? (texte('tri') as Tri) : 'recent')
const pageDemandee = computed(() => Number(texte('page')) || 1)

function maj(patch: Record<string, string | undefined>, garderPage = false): void {
  const query: LocationQueryRaw = { ...route.query, ...patch }
  if (!garderPage) delete query.page
  for (const cle of Object.keys(query)) if (!query[cle]) delete query[cle]
  void router.replace({ query })
}

function basculer<T extends string>(cle: string, courantes: T[], valeur: T): void {
  const suivantes = courantes.includes(valeur) ? courantes.filter((v) => v !== valeur) : [...courantes, valeur]
  maj({ [cle]: suivantes.join(',') })
}

// Saisie avec délai : la liste ne se recalcule pas à chaque frappe.
const saisie = ref(requete.value)
let minuteur: ReturnType<typeof setTimeout> | undefined
watch(saisie, (valeur) => {
  clearTimeout(minuteur)
  minuteur = setTimeout(() => maj({ q: valeur.trim() }), 200)
})
watch(requete, (valeur) => {
  if (valeur !== saisie.value.trim()) saisie.value = valeur
})
onBeforeUnmount(() => clearTimeout(minuteur))

function reinitialiser(): void {
  saisie.value = ''
  void router.replace({ query: {} })
}

// --- Résultats ----------------------------------------------------------------------------------------

const lignes = computed(() => index.donnees.value ?? [])
const trouves = computed(() => {
  const ids = recherche.value?.chercher(requete.value) ?? null
  return ids ? lignes.value.filter((l) => ids.has(l.id)) : lignes.value
})
const retenus = computed(() => trier(appliquerFiltres(trouves.value, filtres.value), tri.value))
const page = computed(() => paginer(retenus.value, pageDemandee.value, TAILLE_PAGE))
const nbFiltres = computed(() => compterFiltresActifs(filtres.value))
const effectifs = computed(() => {
  const n = new Map<Categorie, number>()
  for (const l of lignes.value) n.set(l.categorie.valeur, (n.get(l.categorie.valeur) ?? 0) + 1)
  return n
})
const categoriesPresentes = computed(() => CATEGORIES.filter((c) => effectifs.value.has(c)))
const filtreOuRecherche = computed(() => nbFiltres.value > 0 || requete.value.trim() !== '')
</script>

<template>
  <div class="mx-auto max-w-[1360px] px-5 pt-10 pb-[72px] md:px-10">
    <div class="mb-6">
      <h1 class="mb-1.5 text-[28px] font-bold">{{ L.scrutins.titre }}</h1>
      <p
        v-if="index.donnees.value"
        class="text-[15px] text-ink-2"
      >
        {{ L.scrutins.chapeau(nombre(index.donnees.value.length)) }}
      </p>
    </div>

    <form
      role="search"
      class="mb-5 flex max-w-[640px] gap-2 rounded-xl border border-line bg-surface py-1.5 pr-2 pl-4"
      @submit.prevent
    >
      <label
        for="recherche-scrutins"
        class="sr-only"
      >{{ L.scrutins.recherche }}</label>
      <input
        id="recherche-scrutins"
        v-model="saisie"
        type="search"
        :placeholder="L.scrutins.recherchePlaceholder"
        class="min-w-0 flex-1 bg-transparent py-2 text-sm outline-none"
      >
    </form>

    <ErrorPanel
      v-if="index.erreur.value"
      @reessayer="index.recharger"
    />

    <div
      v-else
      class="flex flex-wrap items-start gap-7"
    >
      <button
        type="button"
        class="btn md:hidden"
        :aria-expanded="filtresMobileOuverts"
        aria-controls="filtres"
        @click="filtresMobileOuverts = !filtresMobileOuverts"
      >
        {{ L.scrutins.filtres }}<template v-if="nbFiltres"> ({{ nbFiltres }})</template>
      </button>

      <aside
        id="filtres"
        class="card w-full shrink-0 px-5 py-1 md:block md:w-[280px]"
        :class="filtresMobileOuverts ? 'block' : 'hidden'"
        :aria-label="L.scrutins.filtres"
      >
        <div class="flex items-center justify-between pt-4 pb-3">
          <h2 class="text-sm font-bold">{{ L.scrutins.filtres }}</h2>
          <button
            type="button"
            class="btn px-2.5 py-1 text-xs"
            @click="reinitialiser"
          >
            {{ L.scrutins.reinitialiser }}
          </button>
        </div>

        <fieldset class="border-t border-line py-3">
          <legend class="float-left mb-2 w-full text-[13px] font-bold">{{ L.scrutins.categorie }}</legend>
          <div class="clear-both">
            <label
              v-for="c in categoriesPresentes"
              :key="c"
              class="flex cursor-pointer items-center gap-2 py-1 text-[13px]"
            >
              <input
                type="checkbox"
                :checked="filtres.categories.includes(c)"
                @change="basculer('nature', filtres.categories, c)"
              >
              <span class="flex-1">{{ libelleCategorie(c) }}</span>
              <span class="font-mono text-xs text-ink-3">{{ nombre(effectifs.get(c) ?? 0) }}</span>
            </label>
            <p class="mt-2 text-xs text-ink-3">{{ L.scrutins.categorieNote }}</p>
          </div>
        </fieldset>

        <fieldset class="border-t border-line py-3">
          <legend class="float-left mb-2 w-full text-[13px] font-bold">{{ L.scrutins.periode }}</legend>
          <div class="clear-both flex gap-2">
            <label class="flex-1 text-xs text-ink-2">
              {{ L.scrutins.du }}
              <input
                type="date"
                class="mt-1 w-full rounded-md border border-line px-2 py-1.5 text-xs"
                :value="filtres.dateDebut ?? ''"
                @change="maj({ du: ($event.target as HTMLInputElement).value })"
              >
            </label>
            <label class="flex-1 text-xs text-ink-2">
              {{ L.scrutins.au }}
              <input
                type="date"
                class="mt-1 w-full rounded-md border border-line px-2 py-1.5 text-xs"
                :value="filtres.dateFin ?? ''"
                @change="maj({ au: ($event.target as HTMLInputElement).value })"
              >
            </label>
          </div>
        </fieldset>

        <fieldset class="border-t border-line py-3">
          <legend class="float-left mb-2 w-full text-[13px] font-bold">{{ L.scrutins.resultat }}</legend>
          <div class="clear-both">
            <label
              v-for="r in RESULTATS"
              :key="r"
              class="flex cursor-pointer items-center gap-2 py-1 text-[13px]"
            >
              <input
                type="checkbox"
                :checked="filtres.resultats.includes(r)"
                @change="basculer('resultat', filtres.resultats, r)"
              >
              {{ libelleResultat(r) }}
            </label>
          </div>
        </fieldset>

        <div class="border-t border-line py-3 text-[13px]">
          <span class="font-bold">{{ L.scrutins.legislature }}</span>
          <p class="mt-1 text-ink-2">{{ L.scrutins.legislatureValeur }}</p>
        </div>
      </aside>

      <section
        class="min-w-0 flex-[999_1_560px]"
        aria-live="polite"
      >
        <div class="mb-3.5 flex flex-wrap items-center justify-between gap-3">
          <p
            v-if="!index.chargement.value"
            class="text-[13px] text-ink-2"
          >
            {{ L.scrutins.nombreRetenu(nombre(retenus.length), nombre(lignes.length)) }}<template v-if="nbFiltres">
              · {{ L.scrutins.filtresActifs(nbFiltres) }}
            </template>
          </p>
          <label class="ml-auto flex items-center gap-2 text-[13px] text-ink-2">
            {{ L.scrutins.trier }}
            <select
              class="rounded-md border border-line bg-surface px-2.5 py-1.5 text-[13px] text-ink"
              :value="tri"
              @change="maj({ tri: ($event.target as HTMLSelectElement).value === 'recent' ? '' : ($event.target as HTMLSelectElement).value })"
            >
              <option value="recent">{{ L.scrutins.triRecent }}</option>
              <option value="ancien">{{ L.scrutins.triAncien }}</option>
              <option value="numero">{{ L.scrutins.triNumero }}</option>
            </select>
          </label>
        </div>

        <SkeletonRows
          v-if="index.chargement.value"
          :lignes="8"
        />
        <EmptyPanel
          v-else-if="retenus.length === 0"
          :titre="L.scrutins.aucun"
          :aide="L.scrutins.aucunAide"
        >
          <button
            v-if="filtreOuRecherche"
            type="button"
            class="btn mt-4"
            @click="reinitialiser"
          >
            {{ L.scrutins.reinitialiser }}
          </button>
        </EmptyPanel>
        <template v-else>
          <div class="card px-6 py-2">
            <ScrutinRow
              v-for="s in page.items"
              :key="s.id"
              :scrutin="s"
            />
          </div>
          <div class="mt-5 flex flex-wrap items-center justify-between gap-2.5">
            <p class="text-[13px] text-ink-2">{{ L.scrutins.affichage(nombre(page.de), nombre(page.a), nombre(page.total)) }}</p>
            <nav
              v-if="page.pages > 1"
              :aria-label="L.scrutins.pagination"
              class="flex items-center gap-1.5"
            >
              <button
                type="button"
                class="btn px-2.5"
                :disabled="page.page <= 1"
                :aria-label="L.scrutins.precedent"
                @click="maj({ page: String(page.page - 1) }, true)"
              >
                ‹
              </button>
              <template
                v-for="(n, i) in numerosDePage(page.page, page.pages)"
                :key="i"
              >
                <span
                  v-if="n === null"
                  class="px-1 text-ink-3"
                  aria-hidden="true"
                >…</span>
                <button
                  v-else
                  type="button"
                  class="btn min-w-9 justify-center px-2.5"
                  :class="n === page.page ? 'btn-primary' : ''"
                  :aria-current="n === page.page ? 'page' : undefined"
                  :aria-label="L.scrutins.page(n)"
                  @click="maj({ page: String(n) }, true)"
                >
                  {{ n }}
                </button>
              </template>
              <button
                type="button"
                class="btn px-2.5"
                :disabled="page.page >= page.pages"
                :aria-label="L.scrutins.suivant"
                @click="maj({ page: String(page.page + 1) }, true)"
              >
                ›
              </button>
            </nav>
            <p
              v-else
              class="text-[13px] text-ink-3"
            >
              {{ L.scrutins.finListe }}
            </p>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
