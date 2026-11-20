<script setup lang="ts">
import { computed } from 'vue'
import { L } from '../lexique'
import { STYLES_VOTE, type TypeBadge } from './voteStyles'

const props = withDefaults(defineProps<{ type: TypeBadge; label?: string; compact?: boolean }>(), {
  label: undefined,
  compact: false,
})

const texte = computed(() => props.label ?? L.positions[props.type])
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full font-bold whitespace-nowrap"
    :class="[STYLES_VOTE[type].badge, compact ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-[13px]']"
  >
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="3"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <polyline
        v-if="type === 'pour'"
        points="20 6 9 17 4 12"
      />
      <template v-else-if="type === 'contre'">
        <line
          x1="18"
          y1="6"
          x2="6"
          y2="18"
        />
        <line
          x1="6"
          y1="6"
          x2="18"
          y2="18"
        />
      </template>
      <line
        v-else-if="type === 'abstention'"
        x1="5"
        y1="12"
        x2="19"
        y2="12"
      />
      <line
        v-else-if="type === 'non_votant'"
        x1="5"
        y1="5"
        x2="19"
        y2="19"
        stroke-dasharray="3,3"
      />
      <circle
        v-else
        cx="12"
        cy="12"
        r="3"
      />
    </svg>
    {{ texte }}
  </span>
</template>
