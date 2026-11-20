<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import ErrorPanel from '../components/ErrorPanel.vue'
import KpiCard from '../components/KpiCard.vue'
import SkeletonRows from '../components/SkeletonRows.vue'
import { useAsync } from '../composables/useAsync'
import { chargerQualite } from '../data'
import { dateLongue, nombre } from '../format'
import { L } from '../lexique'

const qualite = useAsync(chargerQualite)
const q = computed(() => qualite.donnees.value)
const mods = computed(() => q.value?.modifications ?? null)

function valeur(v: number | string | null): string {
  return v === null ? '—' : String(v)
}
</script>

<template>
  <div class="mx-auto max-w-[1120px] px-5 pt-10 pb-[72px] md:px-10">
    <div class="mb-6">
      <h1 class="mb-1.5 text-[28px] font-bold">{{ L.qualite.titre }}</h1>
      <p class="max-w-3xl text-[15px] text-ink-2">{{ L.qualite.chapeau }}</p>
    </div>

    <SkeletonRows
      v-if="qualite.chargement.value"
      :lignes="4"
    />
    <ErrorPanel
      v-else-if="qualite.erreur.value"
      @reessayer="qualite.recharger"
    />

    <template v-else-if="q">
      <div class="mb-8 grid gap-4 sm:grid-cols-2">
        <KpiCard
          :label="L.qualite.scrutins"
          :valeur="nombre(q.nombre_scrutins)"
          :sous="`${L.qualite.donneesDu} ${dateLongue(q.donnees_du.slice(0, 10))}`"
        />
        <div class="card px-6 py-5">
          <div class="mb-2.5 text-xs font-semibold tracking-wider text-ink-3 uppercase">{{ L.qualite.archive }}</div>
          <div class="font-mono text-[13px] break-all">{{ q.archive_sha256 }}</div>
        </div>
      </div>

      <section
        class="mb-8"
        aria-labelledby="ecarts"
      >
        <h2
          id="ecarts"
          class="mb-1 text-lg font-bold"
        >
          {{ L.qualite.statutTitre }}
        </h2>
        <p class="mb-4 text-[14px] text-ink-2">
          {{
            q.statut_reconciliation === 'ok'
              ? L.qualite.statutOk
              : L.qualite.statutEcarts(nombre(q.ecarts_connus.length))
          }}
        </p>
        <div
          v-if="q.ecarts_connus.length"
          class="card overflow-x-auto"
        >
          <table class="w-full min-w-[720px] text-left text-sm">
            <caption class="sr-only">{{ L.qualite.ecartsTitre }}</caption>
            <thead class="border-b border-line text-xs font-semibold tracking-wider text-ink-3 uppercase">
              <tr>
                <th
                  class="px-4 py-3"
                  scope="col"
                >
                  {{ L.qualite.colControle }}
                </th>
                <th
                  class="px-4 py-3"
                  scope="col"
                >
                  {{ L.qualite.colScrutin }}
                </th>
                <th
                  class="px-4 py-3 text-right"
                  scope="col"
                >
                  {{ L.qualite.colAttendu }}
                </th>
                <th
                  class="px-4 py-3 text-right"
                  scope="col"
                >
                  {{ L.qualite.colObtenu }}
                </th>
                <th
                  class="px-4 py-3"
                  scope="col"
                >
                  {{ L.qualite.colMotif }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-line">
              <tr
                v-for="(e, i) in q.ecarts_connus"
                :key="i"
              >
                <td class="px-4 py-3 align-top font-mono">
                  {{ e.controle }}<span v-if="e.detail"> · {{ e.detail }}</span>
                </td>
                <td class="px-4 py-3 align-top">
                  <RouterLink :to="`/scrutins/${e.scrutin_id}`">{{ e.scrutin_id }}</RouterLink>
                </td>
                <td class="px-4 py-3 text-right align-top font-mono">{{ valeur(e.attendu) }}</td>
                <td class="px-4 py-3 text-right align-top font-mono">{{ valeur(e.obtenu) }}</td>
                <td class="px-4 py-3 align-top text-ink-2">
                  {{ e.motif }}
                  <div class="mt-1 text-xs text-ink-3">{{ L.qualite.valideLe(e.valide_le) }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section
        class="mb-8"
        aria-labelledby="classification"
      >
        <h2
          id="classification"
          class="mb-1 text-lg font-bold"
        >
          {{ L.qualite.classificationTitre }}
        </h2>
        <p class="mb-2 text-[13px] text-ink-2">{{ L.qualite.classificationNote }}</p>
        <ul class="space-y-1 text-[14px]">
          <li>{{ L.qualite.aVerifier(nombre(q.classification.a_verifier), nombre(q.nombre_scrutins)) }}</li>
          <li>{{ L.qualite.indetermine(nombre(q.classification.indetermine)) }}</li>
        </ul>
      </section>

      <section
        class="mb-8"
        aria-labelledby="noms"
      >
        <h2
          id="noms"
          class="mb-1 text-lg font-bold"
        >
          {{ L.qualite.nomsTitre }}
        </h2>
        <ul class="mb-2 space-y-1 text-[14px]">
          <li>{{ L.qualite.nomsGroupes(nombre(q.noms_non_resolus.groupes)) }}</li>
          <li>{{ L.qualite.nomsDeputes(nombre(q.noms_non_resolus.deputes)) }}</li>
        </ul>
        <p class="text-[13px] text-ink-2">{{ L.qualite.nomsNote }}</p>
      </section>

      <section
        class="mb-8"
        aria-labelledby="modifications"
      >
        <h2
          id="modifications"
          class="mb-2 text-lg font-bold"
        >
          {{ L.qualite.modificationsTitre }}
        </h2>
        <p
          v-if="!mods"
          class="text-[14px] text-ink-2"
        >
          {{ L.qualite.modificationsAucune }}
        </p>
        <template v-else>
          <ul class="mb-2 space-y-1 text-[14px]">
            <li>{{ L.qualite.nouveaux(nombre(mods.nouveaux)) }}</li>
            <li>{{ L.qualite.supprimes(nombre(mods.nombre_supprimes)) }}</li>
            <li>{{ L.qualite.chiffres(nombre(mods.nombre_modifies_chiffres)) }}</li>
            <li>{{ L.qualite.autres(nombre(mods.nombre_modifies_autres)) }}</li>
          </ul>
          <p class="text-xs text-ink-3">{{ L.qualite.listeLimitee }}</p>
        </template>
      </section>

      <RouterLink
        to="/methodologie"
        class="font-semibold"
      >
        {{ L.qualite.voirMethodo }} →
      </RouterLink>
    </template>
  </div>
</template>
