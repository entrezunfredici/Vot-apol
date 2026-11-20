<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { URL_CODE_SOURCE } from '../config'
import { chargerMeta } from '../data'
import { dateHeure } from '../format'
import { L } from '../lexique'
import { useAsync } from '../composables/useAsync'

// Le pied de page n'est jamais bloquant : sans `meta.json`, la date n'est simplement pas affichée.
const { donnees: meta } = useAsync(() => chargerMeta().catch(() => null))
</script>

<template>
  <footer class="mt-auto border-t border-line bg-surface">
    <div class="mx-auto grid max-w-[1360px] gap-8 px-5 py-10 md:grid-cols-[2fr_1fr] md:px-10">
      <div class="max-w-xl text-sm text-ink-2">
        <p class="mb-2 font-bold text-ink">{{ L.pied.donnees }}</p>
        <p class="mb-2">{{ L.pied.donneesTexte }}</p>
        <p class="mb-2">{{ L.pied.neutralite }}</p>
        <p
          v-if="meta"
          class="font-mono text-xs text-ink-3"
        >
          {{ L.pied.derniereMaj(dateHeure(meta.donnees_du)) }}
        </p>
      </div>
      <nav
        :aria-label="L.pied.liens"
        class="flex flex-col gap-2 text-sm"
      >
        <p class="font-bold">{{ L.pied.liens }}</p>
        <RouterLink to="/methodologie">{{ L.nav.methodologie }}</RouterLink>
        <RouterLink to="/qualite">{{ L.nav.qualite }}</RouterLink>
        <a
          :href="URL_CODE_SOURCE"
          rel="noopener"
        >{{ L.nav.codeSource }}</a>
      </nav>
    </div>
  </footer>
</template>
