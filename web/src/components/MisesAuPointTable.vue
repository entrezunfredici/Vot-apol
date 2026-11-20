<script setup lang="ts">
import type { DeputeListe, GroupeListe, MiseAuPoint } from '../data'
import { L } from '../lexique'
import VoteBadge from './VoteBadge.vue'

// Mises au point et dysfonctionnements : positions déclarées APRÈS le scrutin. Les chiffres officiels
// ne sont jamais modifiés ; un député introuvable dans le décompte est listé sans rattachement.
const props = defineProps<{
  titre: string
  intro: string
  lignes: MiseAuPoint[]
  deputes: Map<string, DeputeListe> | null
  groupes: Map<string, GroupeListe> | null
}>()

function nomDepute(id: string): string {
  const d = props.deputes?.get(id)
  return d?.nom ? [d.prenom, d.nom].filter(Boolean).join(' ') : `${id} (${L.scrutin.deputeNonResolu})`
}

function nomGroupe(m: MiseAuPoint): string {
  if (m.statut === 'introuvable' || !m.groupe_id) return L.scrutin.groupeNonDetermine
  const g = props.groupes?.get(m.groupe_id)
  return g?.sigle ?? g?.libelle ?? `${m.groupe_id} (${L.scrutin.libelleNonResolu})`
}
</script>

<template>
  <section class="card mb-6 overflow-hidden">
    <div class="px-6 pt-5 pb-1.5">
      <h2 class="mb-1.5 text-base font-bold">{{ titre }}</h2>
      <p class="mb-3 text-[13px] leading-relaxed text-ink-2">{{ intro }}</p>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full min-w-[560px] text-[13px]">
        <thead class="bg-surface-alt text-[11px] font-semibold tracking-wide text-ink-3 uppercase">
          <tr>
            <th
              scope="col"
              class="px-6 py-2 text-left font-semibold"
            >
              {{ L.scrutin.colDepute }}
            </th>
            <th
              scope="col"
              class="px-3 py-2 text-left font-semibold"
            >
              {{ L.scrutin.colGroupe }}
            </th>
            <th
              scope="col"
              class="px-6 py-2 text-left font-semibold"
            >
              {{ L.scrutin.colPosition }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(m, i) in lignes"
            :key="`${m.depute_id}-${i}`"
            class="border-t border-line"
          >
            <td class="px-6 py-2.5">{{ nomDepute(m.depute_id) }}</td>
            <td class="px-3 py-2.5 text-ink-2">{{ nomGroupe(m) }}</td>
            <td class="px-6 py-2.5">
              <span class="flex flex-wrap items-center gap-2.5">
                <VoteBadge
                  v-if="m.position_initiale"
                  :type="m.position_initiale"
                  compact
                />
                <span
                  v-else
                  class="tag"
                >{{ L.scrutin.nonRetrouvee }}</span>
                <span
                  aria-hidden="true"
                  class="text-ink-3"
                >→</span>
                <VoteBadge
                  :type="m.position_declaree"
                  compact
                />
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
