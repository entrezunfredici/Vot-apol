<script setup lang="ts">
import { L } from '../lexique'

withDefaults(defineProps<{ lignes?: number }>(), { lignes: 5 })
</script>

<template>
  <div
    class="card divide-y divide-line px-6"
    role="status"
    aria-live="polite"
  >
    <span class="sr-only">{{ L.etat.chargement }}</span>
    <div
      v-for="n in lignes"
      :key="n"
      class="py-5"
      aria-hidden="true"
    >
      <div class="skeleton mb-3 h-3 w-40" />
      <div class="skeleton h-4 w-full max-w-xl" />
    </div>
  </div>
</template>
