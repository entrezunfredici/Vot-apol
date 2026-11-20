<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { LigneIndex } from '../data'
import { dateCourte, titreAffiche } from '../format'
import { L, libelleCategorie, libelleResultat } from '../lexique'
import VoteBadge from './VoteBadge.vue'

defineProps<{ scrutin: LigneIndex }>()
</script>

<template>
  <div class="flex items-center justify-between gap-6 border-b border-line px-1 py-5 last:border-b-0">
    <div class="min-w-0">
      <div class="mb-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-ink-3">
        <span class="font-mono">{{ L.scrutins.numero }} {{ scrutin.numero }}</span>
        <span aria-hidden="true">·</span>
        <time :datetime="scrutin.date">{{ dateCourte(scrutin.date) }}</time>
        <span class="tag">{{ libelleCategorie(scrutin.categorie.valeur) }}</span>
      </div>
      <RouterLink
        :to="`/scrutins/${scrutin.id}`"
        class="block text-[15px] leading-snug font-semibold text-ink"
      >
        {{ titreAffiche(scrutin.titre) }}
      </RouterLink>
    </div>
    <div class="flex shrink-0 items-center gap-4">
      <VoteBadge
        type="resultat"
        :label="libelleResultat(scrutin.resultat)"
      />
      <RouterLink
        :to="`/scrutins/${scrutin.id}`"
        class="hidden text-ink-2 sm:flex"
        :aria-label="L.scrutins.voirDetail(scrutin.numero)"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </RouterLink>
    </div>
  </div>
</template>
