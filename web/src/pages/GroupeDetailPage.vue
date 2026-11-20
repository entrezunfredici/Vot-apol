<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import KpiCard from '../components/KpiCard.vue'
import VoteBadge from '../components/VoteBadge.vue'
import { useAsync } from '../composables/useAsync'
import {
  chargerGroupe,
  ErreurChargement,
  type Categorie,
  type LigneGroupe,
  type PositionMajoritaireValeur,
} from '../data'
import { dateCourte, nombre, periode } from '../format'
import { L, libelleCategorie, libelleRaisonAbsence } from '../lexique'
import { numerosDePage, paginer } from '../search'

const TAILLE_PAGE = 25
const POSITIONS: PositionMajoritaireValeur[] = ['pour', 'contre', 'abstention', 'aucune']

const route = useRoute()
const router = useRouter()
const identifiant = computed(() => String(route.params.id))
const groupe = useAsync(() => chargerGroupe(identifiant.value))
watch(identifiant, () => void groupe.recharger())

const introuvable = computed(
  () => groupe.erreur.value instanceof ErreurChargement && groupe.erreur.value.status === 404,
)

const nom = computed(() => {
  const g = groupe.donnees.value
  return g ? (g.sigle ?? g.libelle ?? g.groupe_id) : ''
})
const lignes = computed(() => groupe.donnees.value?.lignes ?? [])
const dernier = computed(() => lignes.value[lignes.value.length - 1])

// --- Répartition brute des scrutins par position majoritaire (jamais une moyenne) ----------------

const repartition = computed(() => {
  const n = { pour: 0, contre: 0, abstention: 0, egalite: 0, aucun_vote_exprime: 0 }
  for (const l of lignes.value) {
    if (l.position !== 'aucune') n[l.position]++
    else if (l.raison_absence === 'egalite') n.egalite++
    else n.aucun_vote_exprime++
  }
  return n
})

// --- Filtres et pagination, dans l'adresse ---------------------------------------------------------

function texte(cle: string): string {
  const v = route.query[cle]
  return typeof v === 'string' ? v : ''
}
const nature = computed(() => texte('nature'))
const position = computed(() => ((POSITIONS as string[]).includes(texte('position')) ? texte('position') : ''))
const pageDemandee = computed(() => Number(texte('page')) || 1)

function maj(patch: Record<string, string>, garderPage = false): void {
  const query: LocationQueryRaw = { ...route.query, ...patch }
  if (!garderPage) delete query.page
  for (const cle of Object.keys(query)) if (!query[cle]) delete query[cle]
  void router.replace({ query })
}

const natures = computed(() => {
  const vues = new Set<Categorie>(lignes.value.map((l) => l.categorie))
  return [...vues].sort((a, b) => libelleCategorie(a).localeCompare(libelleCategorie(b), 'fr'))
})

const retenues = computed(() =>
  lignes.value
    .filter((l) => (!nature.value || l.categorie === nature.value) && (!position.value || l.position === position.value))
    .sort((a, b) => b.numero - a.numero), // plus récent d'abord
)
const page = computed(() => paginer(retenues.value, pageDemandee.value, TAILLE_PAGE))
const filtreActif = computed(() => nature.value !== '' || position.value !== '')

function detailPosition(l: LigneGroupe): string {
  return l.position === 'aucune'
    ? libelleRaisonAbsence(l.raison_absence)
    : L.groupes.partMajoritaire(nombre(l.m), nombre(l.exprimes), l.majorite_absolue)
}
function libellePosition(p: PositionMajoritaireValeur): string {
  return p === 'aucune' ? L.groupes.filtrePositionAucune : L.positions[p]
}
</script>

<template>
  <div class="mx-auto max-w-[1120px] px-5 pt-9 pb-[72px] md:px-10">
    <RouterLink
      to="/groupes"
      class="mb-5 inline-flex items-center gap-1.5 text-[13px] font-semibold text-ink-2"
    >
      ← {{ L.groupes.retour }}
    </RouterLink>

    <div
      v-if="groupe.chargement.value"
      class="space-y-4"
      role="status"
    >
      <span class="sr-only">{{ L.etat.chargement }}</span>
      <div class="skeleton h-8 w-72" />
      <div class="skeleton h-24 w-full" />
      <div class="skeleton h-48 w-full" />
    </div>
    <EmptyPanel
      v-else-if="introuvable"
      :titre="L.groupes.introuvable"
      :aide="L.groupes.introuvableAide"
    />
    <ErrorPanel
      v-else-if="groupe.erreur.value"
      @reessayer="groupe.recharger"
    />

    <template v-else-if="groupe.donnees.value">
      <header class="mb-6">
        <h1 class="mb-1 text-[28px] font-bold">{{ nom }}</h1>
        <p class="text-[15px] text-ink-2">
          {{ groupe.donnees.value.libelle ?? L.scrutin.libelleNonResolu }}
        </p>
        <p class="mt-1 text-xs text-ink-3">
          {{ L.groupes.identifiant }} : <span class="font-mono">{{ groupe.donnees.value.groupe_id }}</span>
          · {{ L.groupes.definition }}
        </p>
      </header>

      <EmptyPanel
        v-if="!lignes.length"
        :titre="L.groupes.aucunScrutin"
      />

      <template v-else>
        <div class="mb-8 grid gap-4 sm:grid-cols-3">
          <KpiCard
            :label="L.groupes.kpiScrutins"
            :valeur="nombre(lignes.length)"
            :sous="L.groupes.kpiScrutinsSous"
          />
          <KpiCard
            :label="L.groupes.kpiPeriode"
            :valeur="periode(lignes[0].date, dernier.date)"
            :sous="L.groupes.kpiPeriodeSous"
          />
          <KpiCard
            :label="L.groupes.kpiMembres"
            :valeur="nombre(dernier.membres)"
            :sous="L.groupes.kpiMembresSous(dernier.numero)"
          />
        </div>

        <section
          class="mb-8"
          aria-labelledby="repartition"
        >
          <h2
            id="repartition"
            class="mb-1 text-lg font-bold"
          >
            {{ L.groupes.repartitionTitre }}
          </h2>
          <p class="mb-3 text-[13px] text-ink-2">{{ L.groupes.repartitionNote }}</p>
          <ul class="grid gap-3 sm:grid-cols-5">
            <li
              v-for="p in (['pour', 'contre', 'abstention'] as const)"
              :key="p"
              class="card p-4"
            >
              <VoteBadge
                :type="p"
                compact
              />
              <p class="mt-2 font-mono text-xl font-semibold">{{ nombre(repartition[p]) }}</p>
              <p class="text-xs text-ink-3">{{ L.scrutin.sur(nombre(repartition[p]), nombre(lignes.length), null) }}</p>
            </li>
            <li class="card p-4">
              <p class="text-[13px] font-bold">{{ L.groupes.egalite }}</p>
              <p class="mt-2 font-mono text-xl font-semibold">{{ nombre(repartition.egalite) }}</p>
              <p class="text-xs text-ink-3">{{ L.scrutin.sur(nombre(repartition.egalite), nombre(lignes.length), null) }}</p>
            </li>
            <li class="card p-4">
              <p class="text-[13px] font-bold">{{ L.groupes.aucunVote }}</p>
              <p class="mt-2 font-mono text-xl font-semibold">{{ nombre(repartition.aucun_vote_exprime) }}</p>
              <p class="text-xs text-ink-3">
                {{ L.scrutin.sur(nombre(repartition.aucun_vote_exprime), nombre(lignes.length), null) }}
              </p>
            </li>
          </ul>
          <p class="mt-2 text-xs text-ink-3">{{ L.groupes.sansPositionNote }}</p>
        </section>

        <section aria-labelledby="historique">
          <h2
            id="historique"
            class="mb-1 text-lg font-bold"
          >
            {{ L.groupes.historiqueTitre }}
          </h2>
          <p class="mb-4 text-[13px] text-ink-2">{{ L.groupes.historiqueNote }}</p>

          <div class="mb-4 flex flex-wrap items-end gap-4">
            <div>
              <label
                for="filtre-nature"
                class="mb-1 block text-xs font-semibold text-ink-2"
              >{{ L.groupes.filtreNature }}</label>
              <select
                id="filtre-nature"
                class="btn"
                :value="nature"
                @change="maj({ nature: ($event.target as HTMLSelectElement).value })"
              >
                <option value="">{{ L.groupes.filtreNatureToutes }}</option>
                <option
                  v-for="c in natures"
                  :key="c"
                  :value="c"
                >
                  {{ libelleCategorie(c) }}
                </option>
              </select>
            </div>
            <div>
              <label
                for="filtre-position"
                class="mb-1 block text-xs font-semibold text-ink-2"
              >{{ L.groupes.filtrePosition }}</label>
              <select
                id="filtre-position"
                class="btn"
                :value="position"
                @change="maj({ position: ($event.target as HTMLSelectElement).value })"
              >
                <option value="">{{ L.groupes.filtrePositionToutes }}</option>
                <option
                  v-for="p in POSITIONS"
                  :key="p"
                  :value="p"
                >
                  {{ libellePosition(p) }}
                </option>
              </select>
            </div>
            <button
              v-if="filtreActif"
              type="button"
              class="btn"
              @click="router.replace({ query: {} })"
            >
              {{ L.groupes.reinitialiser }}
            </button>
          </div>
          <p
            class="mb-3 text-[13px] text-ink-2"
            aria-live="polite"
          >
            {{ L.groupes.nombreRetenu(nombre(retenues.length), nombre(lignes.length)) }}
          </p>

          <EmptyPanel
            v-if="!retenues.length"
            :titre="L.groupes.aucunScrutin"
          />
          <div
            v-else
            class="card overflow-x-auto"
          >
            <table class="w-full min-w-[640px] text-left text-sm">
              <thead class="border-b border-line text-xs font-semibold tracking-wider text-ink-3 uppercase">
                <tr>
                  <th
                    class="px-4 py-3"
                    scope="col"
                  >
                    {{ L.groupes.colScrutin }}
                  </th>
                  <th
                    class="px-4 py-3"
                    scope="col"
                  >
                    {{ L.groupes.colNature }}
                  </th>
                  <th
                    class="px-4 py-3"
                    scope="col"
                  >
                    {{ L.groupes.colPosition }}
                  </th>
                  <th
                    class="px-4 py-3"
                    scope="col"
                  >
                    {{ L.groupes.colParticipation }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line">
                <tr
                  v-for="l in page.items"
                  :key="l.scrutin_id"
                >
                  <td class="px-4 py-3 align-top">
                    <RouterLink
                      :to="`/scrutins/${l.scrutin_id}`"
                      class="font-semibold"
                    >
                      {{ L.scrutins.numero }} {{ l.numero }}
                    </RouterLink>
                    <div class="text-xs text-ink-3">
                      <time :datetime="l.date">{{ dateCourte(l.date) }}</time>
                    </div>
                  </td>
                  <td class="px-4 py-3 align-top text-ink-2">{{ libelleCategorie(l.categorie) }}</td>
                  <td class="px-4 py-3 align-top">
                    <VoteBadge
                      v-if="l.position !== 'aucune'"
                      :type="l.position"
                      compact
                    />
                    <span
                      v-else
                      class="text-[13px] font-semibold text-ink-2"
                    >{{ L.scrutin.pasDePosition }}</span>
                    <div class="mt-1 text-xs text-ink-3">{{ detailPosition(l) }}</div>
                  </td>
                  <td class="px-4 py-3 align-top text-ink-2">
                    {{ L.groupes.exprimesSur(nombre(l.exprimes), nombre(l.membres)) }}
                    <div class="text-xs text-ink-3">{{ L.positions.non_votant }} : {{ nombre(l.non_votants) }}</div>
                  </td>
                </tr>
              </tbody>
            </table>
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
