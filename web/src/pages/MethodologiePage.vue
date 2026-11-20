<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { URL_CODE_SOURCE } from '../config'
import { L } from '../lexique'

const M = L.methodo
</script>

<template>
  <div class="mx-auto max-w-[860px] px-5 pt-10 pb-[72px] md:px-10">
    <h1 class="mb-1.5 text-[28px] font-bold">{{ M.titre }}</h1>
    <p class="mb-6 text-[15px] text-ink-2">{{ M.chapeau }}</p>

    <nav
      :aria-label="M.sommaire"
      class="card mb-8 px-5 py-4"
    >
      <p class="mb-2 text-xs font-semibold tracking-wider text-ink-3 uppercase">{{ M.sommaire }}</p>
      <ul class="flex flex-wrap gap-x-5 gap-y-1 text-[14px]">
        <li
          v-for="s in M.sections"
          :key="s.id"
        >
          <a :href="`#${s.id}`">{{ s.titre }}</a>
        </li>
        <li><a href="#cas">{{ M.casTitre }}</a></li>
      </ul>
    </nav>

    <section
      v-for="s in M.sections"
      :id="s.id"
      :key="s.id"
      class="mb-8 scroll-mt-24"
    >
      <h2 class="mb-3 text-xl font-bold">{{ s.titre }}</h2>
      <template v-if="'paragraphes' in s">
        <p
          v-for="(p, i) in s.paragraphes"
          :key="i"
          class="mb-3 text-[15px] leading-relaxed text-ink-2"
        >
          {{ p }}
        </p>
      </template>
      <ul
        v-else
        class="list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2"
      >
        <li
          v-for="(item, i) in s.liste"
          :key="i"
        >
          {{ item }}
        </li>
      </ul>
    </section>

    <section
      id="cas"
      class="mb-8 scroll-mt-24"
    >
      <h2 class="mb-1 text-xl font-bold">{{ M.casTitre }}</h2>
      <p class="mb-3 text-[13px] text-ink-2">{{ M.casNote }}</p>
      <div class="card overflow-x-auto">
        <table class="w-full min-w-[520px] text-left text-sm">
          <thead class="border-b border-line text-xs font-semibold tracking-wider text-ink-3 uppercase">
            <tr>
              <th
                v-for="c in M.casColonnes"
                :key="c"
                class="px-4 py-3"
                scope="col"
              >
                {{ c }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            <tr
              v-for="(ligne, i) in M.cas"
              :key="i"
            >
              <td
                v-for="(v, j) in ligne"
                :key="j"
                class="px-4 py-3"
                :class="j < 3 ? 'font-mono' : 'text-ink-2'"
              >
                {{ v }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card p-6">
      <h2 class="mb-2 text-lg font-bold">{{ M.correctionTitre }}</h2>
      <p class="mb-4 text-[14px] text-ink-2">{{ M.correction }}</p>
      <div class="flex flex-wrap gap-3">
        <a
          :href="`${URL_CODE_SOURCE}/issues`"
          class="btn btn-primary"
          rel="noopener"
        >{{ M.correctionLien }}</a>
        <RouterLink
          to="/qualite"
          class="btn"
        >
          {{ M.qualiteLien }}
        </RouterLink>
      </div>
    </section>
  </div>
</template>
