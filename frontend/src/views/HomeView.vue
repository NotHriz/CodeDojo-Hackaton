<script setup>
// HOME PAGE (public). Edit the words here; the layout comes from HeroShell.
import { RouterLink } from 'vue-router'
import HeroShell from '../components/HeroShell.vue'
import LogoBox from '../components/LogoBox.vue'
import { auth } from '../services/auth.js'
import { SITE_NAME } from '../config.js'

// The three small tiles under the text. Change icon/label freely.
const TILES = [['📍', 'Search the map'], ['✔', 'Check access'], ['👥', 'Vote together']]
</script>

<template>
  <HeroShell>
    <template #left>
      <h1 class="font-display text-5xl lowercase sm:text-7xl">{{ SITE_NAME }}</h1>
      <h2 class="mt-10 font-display text-2xl">Welcome to our site</h2>
      <p class="mt-2 max-w-sm">{{ SITE_NAME }} helps people with disabilities check step-free entrances, lifts, toilets, braille and more at IIUM Gombak before they visit.</p>
      <div class="mt-5 flex flex-wrap gap-3">
        <RouterLink to="/about" class="pill-btn">Read more <span aria-hidden="true">→</span></RouterLink>
        <RouterLink :to="auth.user ? '/explore' : '/login'" class="pill-btn bg-white !text-brand">{{ auth.user ? 'Explore' : 'Log in' }}</RouterLink>
      </div>
      <ul class="mt-8 flex flex-wrap gap-4">
        <li v-for="[icon, label] in TILES" :key="label" class="grid size-28 place-items-center rounded-2xl border border-white/50 p-2 text-center">
          <span class="text-3xl" aria-hidden="true">{{ icon }}</span><span class="text-sm">{{ label }}</span>
        </li>
      </ul>
    </template>
    <!-- RIGHT: the logo square. Logo file is set in src/config.js -->
    <template #right><LogoBox /></template>
  </HeroShell>
</template>
