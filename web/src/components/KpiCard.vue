<script setup lang="ts">
defineProps<{ label: string; valeur: string; sous: string }>()
</script>

<template>
  <div class="card px-6 py-5">
    <div class="mb-2.5 text-xs font-semibold tracking-wider text-ink-3 uppercase">{{ label }}</div>
    <div class="font-mono text-[28px] font-semibold">{{ valeur }}</div>
    <div class="mt-1.5 text-xs text-ink-3">{{ sous }}</div>
  </div>
</template>
