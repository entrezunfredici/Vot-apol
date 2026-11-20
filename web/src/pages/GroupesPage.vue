<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { RouterLink } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import SkeletonRows from '../components/SkeletonRows.vue'
import { useAsync } from '../composables/useAsync'
import { chargerGroupes, chargerStatsGroupes, type StatsGroupe } from '../data'
import { nombre } from '../format'
import { L } from '../lexique'

const groupes = useAsync(chargerGroupes)

// Les agrégats enrichissent les cartes mais ne bloquent jamais la liste.
const stats = shallowRef<Map<string, StatsGroupe> | null>(null)
void chargerStatsGroupes().then((s) => (stats.value = s), () => undefined)

// Ordre du fichier : libellé puis identifiant (alphabétique, jamais selon un indicateur).
const liste = computed(() => [...(groupes.donnees.value?.values() ?? [])])

function nomDe(g: { sigle: string | null; libelle: string | null; id: string }): string {
  return g.sigle ?? g.libelle ?? g.id
}
</script>

<template>
  <div class="mx-auto max-w-[1360px] px-5 pt-10 pb-[72px] md:px-10">
    <div class="mb-6">
      <h1 class="mb-1.5 text-[28px] font-bold">{{ L.groupes.titre }}</h1>
      <p
        v-if="liste.length"
        class="text-[15px] text-ink-2"
      >
        {{ L.groupes.chapeau(nombre(liste.length)) }}
      </p>
      <p class="mt-1 text-[13px] text-ink-3">{{ L.groupes.ordre }} {{ L.groupes.definition }}</p>
    </div>

    <SkeletonRows
      v-if="groupes.chargement.value"
      :lignes="4"
    />
    <ErrorPanel
      v-else-if="groupes.erreur.value"
      @reessayer="groupes.recharger"
    />
    <EmptyPanel
      v-else-if="!liste.length"
      :titre="L.groupes.aucun"
    />

    <ul
      v-else
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <li
        v-for="g in liste"
        :key="g.id"
        class="card flex flex-col p-5"
      >
        <div class="mb-1 flex items-baseline justify-between gap-3">
          <h2 class="text-lg font-bold">{{ nomDe(g) }}</h2>
          <span class="font-mono text-xs text-ink-3">{{ g.id }}</span>
        </div>
        <p
          v-if="g.libelle && g.sigle"
          class="mb-3 text-sm text-ink-2"
        >
          {{ g.libelle }}
        </p>
        <p
          v-else-if="!g.libelle"
          class="mb-3 text-sm text-ink-3"
        >
          {{ L.scrutin.libelleNonResolu }}
        </p>
        <dl class="mt-auto space-y-1 text-[13px] text-ink-2">
          <div>
            <dt class="sr-only">{{ L.groupes.kpiScrutins }}</dt>
            <dd>{{ L.groupes.scrutinsIdentifie(nombre(g.nombre_scrutins)) }}</dd>
          </div>
          <div v-if="stats?.get(g.id)">
            <dt class="sr-only">{{ L.groupes.positionsTitre }}</dt>
            <dd>{{ L.groupes.personnes(nombre(stats.get(g.id)!.personnes_avec_vote)) }}</dd>
          </div>
        </dl>
        <RouterLink
          :to="`/groupes/${g.id}`"
          class="btn mt-4 justify-center"
          :aria-label="L.groupes.voirFiche(nomDe(g))"
        >
          {{ L.scrutin.voirGroupe }}
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
