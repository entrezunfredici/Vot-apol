<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { RouterLink, useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import SkeletonRows from '../components/SkeletonRows.vue'
import VoteBadge from '../components/VoteBadge.vue'
import {
  chargerGroupe,
  chargerGroupes,
  chargerIndexComplet,
  type GroupeListe,
  type LigneGroupe,
  type LigneIndex,
} from '../data'
import { dateCourte, nombre, titreAffiche } from '../format'
import { L, libelleRaisonAbsence } from '../lexique'
import { comparer, compter, numerosDePage, paginer, type TypeComparaison } from '../search'

const TAILLE_PAGE = 25
const MAX_GROUPES = 3
const TYPES: TypeComparaison[] = ['meme', 'differente', 'sans']

const route = useRoute()
const router = useRouter()

const groupes = shallowRef<Map<string, GroupeListe> | null>(null)
const erreurGroupes = ref(false)
function chargerListe(): void {
  erreurGroupes.value = false
  chargerGroupes().then((g) => (groupes.value = g), () => (erreurGroupes.value = true))
}
chargerListe()

function texte(cle: string): string {
  const v = route.query[cle]
  return typeof v === 'string' ? v : ''
}
const choisis = computed(() => {
  const ids = texte('g').split(',').filter((id) => groupes.value?.has(id))
  return [...new Set(ids)].slice(0, MAX_GROUPES)
})
const typeFiltre = computed(() => (TYPES as string[]).includes(texte('type')) ? (texte('type') as TypeComparaison) : '')
const pageDemandee = computed(() => Number(texte('page')) || 1)

function maj(patch: Record<string, string>, garderPage = false): void {
  const query: LocationQueryRaw = { ...route.query, ...patch }
  if (!garderPage) delete query.page
  for (const cle of Object.keys(query)) if (!query[cle]) delete query[cle]
  void router.replace({ query })
}
function basculer(id: string): void {
  const suivants = choisis.value.includes(id) ? choisis.value.filter((g) => g !== id) : [...choisis.value, id]
  maj({ g: suivants.join(',') })
}

function nomDe(id: string): string {
  const g = groupes.value?.get(id)
  return g?.sigle ?? g?.libelle ?? id
}

// --- Historiques des groupes choisis ----------------------------------------------------------------

const historiques = shallowRef<LigneGroupe[][] | null>(null)
const chargement = ref(false)
const erreur = ref(false)
let envoi = 0

async function charger(): Promise<void> {
  const ids = choisis.value
  if (ids.length < 2) {
    historiques.value = null
    return
  }
  const mien = ++envoi
  chargement.value = true
  erreur.value = false
  try {
    const h = await Promise.all(ids.map((id) => chargerGroupe(id)))
    if (mien === envoi) historiques.value = h.map((x) => x.lignes)
  } catch {
    if (mien === envoi) erreur.value = true
  } finally {
    if (mien === envoi) chargement.value = false
  }
}
watch(() => choisis.value.join(','), charger)
watch(groupes, charger)

// Les titres ne bloquent jamais la comparaison.
const titres = shallowRef<Map<string, LigneIndex> | null>(null)
watch(historiques, (h) => {
  if (h && !titres.value) {
    chargerIndexComplet().then((l) => (titres.value = new Map(l.map((x) => [x.id, x]))), () => undefined)
  }
})

const comparees = computed(() => (historiques.value ? comparer(historiques.value) : []))
const compte = computed(() => compter(comparees.value))
const retenues = computed(() =>
  comparees.value.filter((c) => !typeFiltre.value || c.type === typeFiltre.value).sort((a, b) => b.numero - a.numero),
)
const page = computed(() => paginer(retenues.value, pageDemandee.value, TAILLE_PAGE))

const LIBELLES_TYPE: Record<TypeComparaison, string> = {
  meme: L.comparateur.memePosition,
  differente: L.comparateur.positionsDifferentes,
  sans: L.comparateur.sansPosition,
}
const LIBELLES_COURTS: Record<TypeComparaison, string> = {
  meme: L.comparateur.categorieMemePos,
  differente: L.comparateur.categorieDiff,
  sans: L.comparateur.categorieSans,
}
</script>

<template>
  <div class="mx-auto max-w-[1120px] px-5 pt-10 pb-[72px] md:px-10">
    <div class="mb-6">
      <h1 class="mb-1.5 text-[28px] font-bold">{{ L.comparateur.titre }}</h1>
      <p class="max-w-3xl text-[15px] text-ink-2">{{ L.comparateur.chapeau }}</p>
    </div>

    <ErrorPanel
      v-if="erreurGroupes"
      @reessayer="chargerListe"
    />
    <SkeletonRows
      v-else-if="!groupes"
      :lignes="2"
    />

    <template v-else>
      <fieldset class="card mb-6 p-5">
        <legend class="px-1 text-sm font-bold">{{ L.comparateur.choix }}</legend>
        <p class="mb-3 text-[13px] text-ink-2">{{ L.comparateur.choixAide }}</p>
        <div class="flex flex-wrap gap-x-5 gap-y-2">
          <label
            v-for="g in groupes.values()"
            :key="g.id"
            class="flex items-center gap-2 text-sm"
          >
            <input
              type="checkbox"
              :checked="choisis.includes(g.id)"
              :disabled="!choisis.includes(g.id) && choisis.length >= MAX_GROUPES"
              @change="basculer(g.id)"
            >
            <span :title="g.libelle ?? undefined">{{ g.sigle ?? g.libelle ?? g.id }}</span>
          </label>
        </div>
        <p
          v-if="choisis.length >= MAX_GROUPES"
          class="mt-2 text-xs text-ink-3"
        >
          {{ L.comparateur.maximum }}
        </p>
      </fieldset>

      <EmptyPanel
        v-if="choisis.length < 2"
        :titre="L.comparateur.pasAssez"
      />
      <SkeletonRows
        v-else-if="chargement"
        :lignes="3"
      />
      <ErrorPanel
        v-else-if="erreur"
        @reessayer="charger"
      />
      <EmptyPanel
        v-else-if="historiques && !comparees.length"
        :titre="L.comparateur.aucunCommun"
      />

      <template v-else-if="historiques">
        <section
          class="mb-8"
          aria-labelledby="resume"
        >
          <h2
            id="resume"
            class="mb-1 text-lg font-bold"
          >
            {{ L.comparateur.resumeTitre }}
          </h2>
          <p class="mb-1 text-[14px] text-ink-2">
            {{ choisis.map(nomDe).join(' · ') }} — {{ L.comparateur.communs(nombre(comparees.length)) }}
          </p>
          <p class="mb-3 text-[13px] text-ink-3">{{ L.comparateur.resumeNote }}</p>
          <ul class="grid gap-3 sm:grid-cols-3">
            <li
              v-for="t in TYPES"
              :key="t"
              class="card p-4"
            >
              <p class="text-[13px] font-bold">{{ LIBELLES_TYPE[t] }}</p>
              <p class="mt-2 font-mono text-xl font-semibold">{{ nombre(compte[t]) }}</p>
              <p class="text-xs text-ink-3">{{ L.comparateur.sur(nombre(compte[t]), nombre(comparees.length)) }}</p>
            </li>
          </ul>
        </section>

        <section aria-labelledby="liste">
          <h2
            id="liste"
            class="mb-3 text-lg font-bold"
          >
            {{ L.comparateur.listeTitre }}
          </h2>
          <div class="mb-3">
            <label
              for="filtre-type"
              class="mb-1 block text-xs font-semibold text-ink-2"
            >{{ L.comparateur.filtre }}</label>
            <select
              id="filtre-type"
              class="btn"
              :value="typeFiltre"
              @change="maj({ type: ($event.target as HTMLSelectElement).value })"
            >
              <option value="">{{ L.comparateur.filtreTous }}</option>
              <option
                v-for="t in TYPES"
                :key="t"
                :value="t"
              >
                {{ LIBELLES_TYPE[t] }}
              </option>
            </select>
          </div>
          <p
            class="mb-3 text-[13px] text-ink-2"
            aria-live="polite"
          >
            {{ L.comparateur.retenus(nombre(retenues.length), nombre(comparees.length)) }}
          </p>

          <EmptyPanel
            v-if="!retenues.length"
            :titre="L.comparateur.aucun"
          />
          <div
            v-else
            class="card divide-y divide-line"
          >
            <div
              v-for="c in page.items"
              :key="c.scrutin_id"
              class="px-5 py-4"
            >
              <div class="mb-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-ink-3">
                <span class="font-mono">{{ L.scrutins.numero }} {{ c.numero }}</span>
                <span aria-hidden="true">·</span>
                <time :datetime="c.date">{{ dateCourte(c.date) }}</time>
                <span class="tag">{{ LIBELLES_COURTS[c.type] }}</span>
              </div>
              <RouterLink
                :to="`/scrutins/${c.scrutin_id}`"
                class="mb-3 block text-[15px] leading-snug font-semibold text-ink"
              >
                {{ titres?.get(c.scrutin_id) ? titreAffiche(titres.get(c.scrutin_id)!.titre) : `${L.scrutins.numero} ${c.numero}` }}
              </RouterLink>
              <ul class="grid gap-2 sm:grid-cols-3">
                <li
                  v-for="(ligne, i) in c.lignes"
                  :key="choisis[i]"
                  class="text-[13px]"
                >
                  <p class="mb-1 font-semibold text-ink-2">{{ nomDe(choisis[i]) }}</p>
                  <VoteBadge
                    v-if="ligne.position !== 'aucune'"
                    :type="ligne.position"
                    compact
                  />
                  <span
                    v-else
                    class="font-semibold text-ink-2"
                  >{{ L.scrutin.pasDePosition }}</span>
                  <p class="mt-1 text-xs text-ink-3">
                    {{
                      ligne.position === 'aucune'
                        ? libelleRaisonAbsence(ligne.raison_absence)
                        : L.groupes.partMajoritaire(nombre(ligne.m), nombre(ligne.exprimes), ligne.majorite_absolue)
                    }}
                  </p>
                  <p class="text-xs text-ink-3">{{ L.groupes.exprimesSur(nombre(ligne.exprimes), nombre(ligne.membres)) }}</p>
                </li>
              </ul>
            </div>
          </div>

          <div
            v-if="retenues.length"
            class="mt-4 flex flex-wrap items-center justify-between gap-3"
          >
            <p class="text-[13px] text-ink-2">
              {{ L.scrutins.affichage(nombre(page.de), nombre(page.a), nombre(page.total)) }}
            </p>
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
        </section>
      </template>
    </template>
  </div>
</template>
