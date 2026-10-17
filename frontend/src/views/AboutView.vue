<script setup>
// ABOUT PAGE (public). Edit STEPS and the paragraph below.
import HeroShell from '../components/HeroShell.vue'
import LogoBox from '../components/LogoBox.vue'
import { SITE_NAME } from '../config.js'

const STEPS = [
  ['Search', 'Find a building by name, or click a pin on the map.'],
  ['Check', 'See which access features are recorded, who recorded them and when.'],
  ['Add and vote', 'Add photos or updates. Other members vote, so information stays honest.']
]
</script>

<template>
  <HeroShell>
    <template #left>
      <h1 class="font-display text-5xl lowercase sm:text-7xl">about</h1>
      <h2 class="mt-10 font-display text-2xl">Why {{ SITE_NAME }} exists</h2>
      <p class="mt-2 max-w-sm">{{ SITE_NAME }} is a campus accessibility finder for IIUM Gombak. It covers physical, vision, hearing and cognitive needs. Information comes from the community and is never certified. Unknown stays marked as unknown.</p>
    </template>
    <template #right>
      <LogoBox size="h-24 w-24" />
      <h2 class="mt-4 text-center font-display text-xl font-bold">How it works</h2>
      <ol class="mt-3 space-y-3">
        <li v-for="([t, d], i) in STEPS" :key="t" class="flex gap-3">
          <span class="grid size-9 shrink-0 place-items-center rounded-full bg-brand font-bold text-white" aria-hidden="true">{{ i + 1 }}</span>
          <span><strong>{{ t }}.</strong> {{ d }}</span>
        </li>
      </ol>
    </template>
  </HeroShell>
</template>
