<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import ErrorPanel from '../components/ErrorPanel.vue'
import KpiCard from '../components/KpiCard.vue'
import ScrutinRow from '../components/ScrutinRow.vue'
import SkeletonRows from '../components/SkeletonRows.vue'
import { useAsync } from '../composables/useAsync'
import { chargerDerniersScrutins, chargerMeta } from '../data'
import { dateEtHeure, nombre, periode } from '../format'
import { L } from '../lexique'

const router = useRouter()
const requete = ref('')

// Indicateurs : toujours lus dans meta.json, jamais codés en dur (CONVENTIONS, règles front).
const meta = useAsync(chargerMeta)
const derniers = useAsync(() => chargerDerniersScrutins(5))

function rechercher(): void {
  const q = requete.value.trim()
  void router.push({ path: '/scrutins', query: q ? { q } : {} })
}
</script>

<template>
  <section class="border-b border-line bg-surface px-5 pt-14 pb-12 text-center md:px-10 md:pt-[72px]">
    <div class="mx-auto max-w-[760px]">
      <span class="inline-flex rounded-full bg-accent-100 px-3 py-1 text-[13px] font-semibold text-accent-600">
        {{ L.accueil.badge }}
      </span>
      <h1 class="mt-5 mb-4 text-4xl leading-[1.14] font-extrabold tracking-tight md:text-5xl">
        {{ L.accueil.titre }}
      </h1>
      <p class="mb-8 text-lg leading-relaxed text-ink-2">{{ L.accueil.intro }}</p>
      <form
        role="search"
        class="mx-auto flex max-w-[580px] items-center gap-2 rounded-[14px] border border-line bg-surface py-1.5 pr-2 pl-4 shadow-sm"
        @submit.prevent="rechercher"
      >
        <label
          for="recherche-accueil"
          class="sr-only"
        >{{ L.scrutins.recherche }}</label>
        <input
          id="recherche-accueil"
          v-model="requete"
          type="search"
          :placeholder="L.accueil.recherchePlaceholder"
          class="min-w-0 flex-1 bg-transparent py-2.5 text-[15px] outline-none"
        >
        <button
          type="submit"
          class="btn btn-primary"
        >
          {{ L.accueil.rechercher }}
        </button>
      </form>
    </div>
  </section>

  <section class="mx-auto max-w-[1240px] px-5 pt-12 md:px-10">
    <ErrorPanel
      v-if="meta.erreur.value"
      @reessayer="meta.recharger"
    />
    <div
      v-else
      class="grid gap-5 [grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr))]"
    >
      <template v-if="meta.donnees.value">
        <KpiCard
          :label="L.accueil.kpiScrutins"
          :valeur="nombre(meta.donnees.value.nombre_scrutins)"
          :sous="L.accueil.kpiScrutinsSous"
        />
        <KpiCard
          :label="L.accueil.kpiGroupes"
          :valeur="nombre(meta.donnees.value.nombre_groupes)"
          :sous="L.accueil.kpiGroupesSous"
        />
        <KpiCard
          :label="L.accueil.kpiPeriode"
          :valeur="periode(meta.donnees.value.premiere_date, meta.donnees.value.derniere_date)"
          :sous="L.accueil.kpiPeriodeSous"
        />
        <KpiCard
          :label="L.accueil.kpiSynchro"
          :valeur="dateEtHeure(meta.donnees.value.donnees_du).date"
          :sous="L.accueil.kpiSynchroSous(dateEtHeure(meta.donnees.value.donnees_du).heure)"
        />
      </template>
      <template v-else>
        <div
          v-for="n in 4"
          :key="n"
          class="skeleton h-[112px]"
          aria-hidden="true"
        />
      </template>
    </div>
  </section>

  <section class="mx-auto max-w-[1240px] px-5 pt-14 pb-4 md:px-10">
    <div class="card border-accent-100 bg-accent-50 p-6">
      <h2 class="mb-2 text-base font-bold">{{ L.accueil.avertissementTitre }}</h2>
      <p class="mb-3 text-sm leading-relaxed text-ink-2">{{ L.accueil.avertissement }}</p>
      <RouterLink
        to="/methodologie"
        class="text-sm font-semibold"
      >{{ L.accueil.lireMethodologie }}</RouterLink>
    </div>
  </section>

  <section class="mx-auto max-w-[1240px] px-5 pt-12 pb-[72px] md:px-10">
    <div class="mb-3 flex items-center justify-between gap-4">
      <h2 class="text-2xl font-bold">{{ L.accueil.derniers }}</h2>
      <RouterLink
        to="/scrutins"
        class="text-sm font-semibold"
      >{{ L.accueil.voirTous }} →</RouterLink>
    </div>
    <SkeletonRows
      v-if="derniers.chargement.value"
      :lignes="5"
    />
    <ErrorPanel
      v-else-if="derniers.erreur.value"
      @reessayer="derniers.recharger"
    />
    <div
      v-else
      class="card px-6 py-2"
    >
      <ScrutinRow
        v-for="s in derniers.donnees.value ?? []"
        :key="s.id"
        :scrutin="s"
      />
    </div>
  </section>
</template>
