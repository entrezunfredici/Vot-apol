<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { URL_CODE_SOURCE } from '../config'
import { L } from '../lexique'

const route = useRoute()
const router = useRouter()
const menuOuvert = ref(false)
const recherche = ref('')

const liens = [
  { to: '/', label: L.nav.accueil },
  { to: '/scrutins', label: L.nav.scrutins },
  { to: '/groupes', label: L.nav.groupes },
  { to: '/comparateur', label: L.nav.comparateur },
  { to: '/statistiques', label: L.nav.statistiques },
  { to: '/methodologie', label: L.nav.methodologie },
]

// Le menu se referme à chaque navigation.
watch(
  () => route.fullPath,
  () => (menuOuvert.value = false),
)

function lancerRecherche(): void {
  const q = recherche.value.trim()
  void router.push({ path: '/scrutins', query: q ? { q } : {} })
  recherche.value = ''
}

function actif(to: string): boolean {
  return to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-line bg-surface">
    <a
      href="#contenu"
      class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:rounded focus:bg-surface focus:p-2"
    >
      {{ L.nav.allerAuContenu }}
    </a>
    <div class="mx-auto flex max-w-[1360px] flex-wrap items-center gap-x-8 gap-y-2 px-5 py-3 md:h-[72px] md:flex-nowrap md:px-10 md:py-0">
      <RouterLink
        to="/"
        class="flex shrink-0 items-center gap-2.5 text-ink no-underline hover:no-underline"
      >
        <span
          class="flex h-8 w-8 items-center justify-center rounded-[9px] bg-accent font-mono text-sm font-extrabold text-white"
          aria-hidden="true"
        >V</span>
        <span class="text-[17px] font-extrabold tracking-tight">{{ L.marque }}</span>
      </RouterLink>

      <button
        type="button"
        class="btn ml-auto md:hidden"
        :aria-expanded="menuOuvert"
        aria-controls="navigation"
        :aria-label="menuOuvert ? L.nav.fermerMenu : L.nav.ouvrirMenu"
        @click="menuOuvert = !menuOuvert"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <template v-if="menuOuvert">
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
          <template v-else>
            <line
              x1="3"
              y1="6"
              x2="21"
              y2="6"
            />
            <line
              x1="3"
              y1="12"
              x2="21"
              y2="12"
            />
            <line
              x1="3"
              y1="18"
              x2="21"
              y2="18"
            />
          </template>
        </svg>
      </button>

      <div
        id="navigation"
        class="w-full flex-col gap-4 md:flex md:w-auto md:flex-1 md:flex-row md:items-center md:justify-between"
        :class="menuOuvert ? 'flex' : 'hidden'"
      >
        <nav
          :aria-label="L.nav.principale"
          class="flex flex-col gap-1 md:flex-row md:items-center md:gap-7"
        >
          <RouterLink
            v-for="lien in liens"
            :key="lien.to"
            :to="lien.to"
            class="border-b-2 py-2 text-sm font-semibold no-underline hover:no-underline"
            :class="actif(lien.to) ? 'border-accent text-accent' : 'border-transparent text-ink-2 hover:text-ink'"
            :aria-current="actif(lien.to) ? 'page' : undefined"
          >
            {{ lien.label }}
          </RouterLink>
        </nav>
        <div class="flex flex-wrap items-center gap-4">
          <form
            role="search"
            class="flex min-w-[260px] items-center gap-2 rounded-lg border border-line bg-bg px-3 py-1.5"
            @submit.prevent="lancerRecherche"
          >
            <label
              for="recherche-globale"
              class="sr-only"
            >{{ L.scrutins.recherche }}</label>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              class="shrink-0 text-ink-3"
              aria-hidden="true"
            >
              <circle
                cx="11"
                cy="11"
                r="7"
              />
              <line
                x1="21"
                y1="21"
                x2="16.65"
                y2="16.65"
              />
            </svg>
            <input
              id="recherche-globale"
              v-model="recherche"
              type="search"
              :placeholder="L.scrutins.recherchePlaceholder"
              class="w-full bg-transparent text-[13px] outline-none"
            >
          </form>
          <a
            :href="URL_CODE_SOURCE"
            class="inline-flex items-center gap-1.5 text-[13px] font-semibold text-ink-2"
            rel="noopener"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            {{ L.nav.codeSource }}
          </a>
        </div>
      </div>
    </div>
  </header>
</template>
