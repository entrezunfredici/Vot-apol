<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import SkeletonRows from '../components/SkeletonRows.vue'
import { useAsync } from '../composables/useAsync'
import { chargerGroupes, chargerStats, type Categorie, type GroupeListe } from '../data'
import { nombre } from '../format'
import { L, libelleCategorie } from '../lexique'

const route = useRoute()
const router = useRouter()
const stats = useAsync(chargerStats)

// Les noms ne bloquent jamais la page : sans eux, l'identifiant s'affiche.
const groupes = shallowRef<Map<string, GroupeListe> | null>(null)
void chargerGroupes().then((g) => (groupes.value = g), () => undefined)

function libelleSelection(id: string): string {
  if (id === 'toutes') return L.stats.toutes
  const [type, valeur] = id.split(':')
  if (type === 'categorie') return L.stats.categorie(libelleCategorie(valeur as Categorie))
  if (type === 'annee') return L.stats.annee(valeur)
  return id
}

const selections = computed(() => stats.donnees.value?.selections ?? [])
const choisie = computed(() => {
  const demande = typeof route.query.selection === 'string' ? route.query.selection : 'toutes'
  return selections.value.find((s) => s.id === demande) ?? selections.value[0]
})

function choisir(id: string): void {
  void router.replace({ query: id === 'toutes' ? {} : { selection: id } })
}

function nomDe(id: string): string {
  const g = groupes.value?.get(id)
  return g?.sigle ?? g?.libelle ?? id
}

// Ordre alphabétique : jamais selon un indicateur (charte de neutralité).
const lignes = computed(() =>
  [...(choisie.value?.groupes ?? [])].sort((a, b) => nomDe(a.groupe_id).localeCompare(nomDe(b.groupe_id), 'fr') || a.groupe_id.localeCompare(b.groupe_id)),
)
const exclus = computed(() => lignes.value.reduce((n, g) => n + g.nb_scrutins_exclus_groupe_non_identifie, 0))
</script>

<template>
  <div class="mx-auto max-w-[1360px] px-5 pt-10 pb-[72px] md:px-10">
    <div class="mb-6">
      <h1 class="mb-1.5 text-[28px] font-bold">{{ L.stats.titre }}</h1>
      <p class="max-w-3xl text-[15px] text-ink-2">{{ L.stats.chapeau }}</p>
      <p class="mt-1 max-w-3xl text-[13px] text-ink-3">{{ L.stats.avertissement }}</p>
    </div>

    <SkeletonRows
      v-if="stats.chargement.value"
      :lignes="4"
    />
    <ErrorPanel
      v-else-if="stats.erreur.value"
      @reessayer="stats.recharger"
    />
    <EmptyPanel
      v-else-if="!choisie"
      :titre="L.stats.aucunGroupe"
    />

    <template v-else>
      <div class="mb-4 flex flex-wrap items-end gap-4">
        <div>
          <label
            for="selection"
            class="mb-1 block text-xs font-semibold text-ink-2"
          >{{ L.stats.selection }}</label>
          <select
            id="selection"
            class="btn"
            :value="choisie.id"
            @change="choisir(($event.target as HTMLSelectElement).value)"
          >
            <option
              v-for="s in selections"
              :key="s.id"
              :value="s.id"
            >
              {{ libelleSelection(s.id) }}
            </option>
          </select>
        </div>
        <p
          class="text-[13px] text-ink-2"
          aria-live="polite"
        >
          {{ L.stats.nombreRetenu(nombre(choisie.nombre_scrutins)) }}
          <template v-if="choisie.id !== 'toutes'"> · {{ L.stats.filtreApplique(libelleSelection(choisie.id)) }}</template>
        </p>
      </div>

      <EmptyPanel
        v-if="!lignes.length"
        :titre="L.stats.aucunGroupe"
      />

      <template v-else>
        <section
          class="mb-10"
          aria-labelledby="effectifs"
        >
          <h2
            id="effectifs"
            class="mb-1 text-lg font-bold"
          >
            {{ L.stats.effectifsTitre }}
          </h2>
          <p class="mb-3 text-[13px] text-ink-2">{{ L.stats.effectifsNote }} {{ L.stats.ordre }}</p>
          <div class="card overflow-x-auto">
            <table class="w-full min-w-[860px] text-left text-sm">
              <thead class="border-b border-line text-xs font-semibold tracking-wider text-ink-3 uppercase">
                <tr>
                  <th
                    class="px-4 py-3"
                    scope="col"
                  >
                    {{ L.stats.colGroupe }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colScrutins }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colMembres }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colPour }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colContre }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colAbstentions }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colNonVotants }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colSansVote }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colPersonnes }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line font-mono">
                <tr
                  v-for="g in lignes"
                  :key="g.groupe_id"
                >
                  <th
                    class="px-4 py-3 font-sans font-semibold"
                    scope="row"
                  >
                    <RouterLink :to="`/groupes/${g.groupe_id}`">{{ nomDe(g.groupe_id) }}</RouterLink>
                  </th>
                  <td class="px-4 py-3 text-right">{{ nombre(g.nb_scrutins) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.membres_scrutins) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.pour) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.contre) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.abstentions) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.non_votants) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.sans_vote_enregistre) }}</td>
                  <td class="px-4 py-3 text-right">{{ nombre(g.personnes_avec_vote) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p
            v-if="exclus > 0"
            class="mt-2 text-xs text-ink-3"
          >
            {{ L.stats.exclus(nombre(exclus)) }}
          </p>
        </section>

        <section
          class="mb-10"
          aria-labelledby="positions"
        >
          <h2
            id="positions"
            class="mb-1 text-lg font-bold"
          >
            {{ L.stats.positionsTitre }}
          </h2>
          <p class="mb-3 text-[13px] text-ink-2">{{ L.stats.positionsNote }}</p>
          <div class="card overflow-x-auto">
            <table class="w-full min-w-[760px] text-left text-sm">
              <thead class="border-b border-line text-xs font-semibold tracking-wider text-ink-3 uppercase">
                <tr>
                  <th
                    class="px-4 py-3"
                    scope="col"
                  >
                    {{ L.stats.colGroupe }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colPour }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colContre }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.positions.abstention }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colEgalite }}
                  </th>
                  <th
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ L.stats.colAucunVote }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line font-mono">
                <tr
                  v-for="g in lignes"
                  :key="g.groupe_id"
                >
                  <th
                    class="px-4 py-3 font-sans font-semibold"
                    scope="row"
                  >
                    {{ nomDe(g.groupe_id) }}
                  </th>
                  <td class="px-4 py-3 text-right">
                    {{ L.stats.sur(nombre(g.scrutins_par_position_majoritaire.pour), nombre(g.nb_scrutins)) }}
                  </td>
                  <td class="px-4 py-3 text-right">
                    {{ L.stats.sur(nombre(g.scrutins_par_position_majoritaire.contre), nombre(g.nb_scrutins)) }}
                  </td>
                  <td class="px-4 py-3 text-right">
                    {{ L.stats.sur(nombre(g.scrutins_par_position_majoritaire.abstention), nombre(g.nb_scrutins)) }}
                  </td>
                  <td class="px-4 py-3 text-right">
                    {{ L.stats.sur(nombre(g.scrutins_par_position_majoritaire.egalite), nombre(g.nb_scrutins)) }}
                  </td>
                  <td class="px-4 py-3 text-right">
                    {{ L.stats.sur(nombre(g.scrutins_par_position_majoritaire.aucun_vote_exprime), nombre(g.nb_scrutins)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="part">
          <h2
            id="part"
            class="mb-1 text-lg font-bold"
          >
            {{ L.stats.partTitre }}
          </h2>
          <p class="mb-3 text-[13px] text-ink-2">{{ L.stats.partNote }}</p>
          <div class="card overflow-x-auto">
            <table class="w-full min-w-[860px] text-left text-sm">
              <thead class="border-b border-line text-xs font-semibold text-ink-3">
                <tr>
                  <th
                    class="px-4 py-3 tracking-wider uppercase"
                    scope="col"
                  >
                    {{ L.stats.colGroupe }}
                  </th>
                  <th
                    v-for="(tranche, i) in stats.donnees.value?.libelles_tranches"
                    :key="i"
                    class="px-4 py-3 text-right"
                    scope="col"
                  >
                    {{ tranche }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line font-mono">
                <tr
                  v-for="g in lignes"
                  :key="g.groupe_id"
                >
                  <th
                    class="px-4 py-3 font-sans font-semibold"
                    scope="row"
                  >
                    {{ nomDe(g.groupe_id) }}
                  </th>
                  <td
                    v-for="(n, i) in g.repartition_part_majoritaire"
                    :key="i"
                    class="px-4 py-3 text-right"
                  >
                    {{ L.stats.sur(nombre(n), nombre(g.nb_scrutins)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>
