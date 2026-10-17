<script setup>
// APP SHELL: full-screen blue page, header with nav pills, page area, footer. No outer margins or dark borders.
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { auth, logOut } from './services/auth.js'
import { SITE_NAME, LOGO_SRC } from './config.js'
import A11yBar from './components/A11yBar.vue'

const router = useRouter()
async function signOut() { await logOut(); router.push('/login') }
// NAV PILL: current page gets a visible outline (the router sets aria-current).
const pill = 'rounded-full border-2 border-transparent px-4 py-2 font-bold uppercase tracking-wide aria-[current=page]:border-white/70'
// RIGHT-SIDE PILL: white fill with blue text and border, so it is readable on the white area AND on blue pages.
const rpill = pill + ' bg-white !text-brand !border-brand'
</script>

<template>
  <!-- SKIP LINK: first Tab stop -->
  <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[2000] focus:rounded focus:bg-white focus:px-4 focus:py-3 focus:font-bold focus:text-brand">Skip to main content</a>

  <!-- WHOLE PAGE: min-h-screen + bg-brand = blue edge to edge, no dark frame -->
  <div class="flex min-h-screen flex-col bg-brand text-white">
    <div class="relative flex flex-1 flex-col">

      <!-- WHITE AREA (Home, About, Log in on laptops): drawn behind the header so Log in and Accessibility sit on white.
           Reshape with the path: first number of "M62 0" is where the curve meets the top (smaller = wider white). -->
      <svg v-if="$route.meta.hero" class="pointer-events-none absolute inset-0 hidden h-full w-full lg:block" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path d="M62 0H100V100H55L46 45C44 26 52 14 62 0Z" fill="#fff" />
      </svg>

      <!-- HEADER: logo + name, nav (left, on blue); Accessibility then Log in (right, on white) -->
      <!-- z-30 puts the header (and the Accessibility panel that opens from it) IN FRONT of the page content (z-10) -->
      <header class="relative z-30 flex flex-wrap items-center gap-3 px-4 py-4 sm:px-8">
        <RouterLink to="/" class="mr-2 flex items-center gap-2 font-display text-2xl font-bold">
          <img v-if="LOGO_SRC" :src="LOGO_SRC" alt="" class="size-10 rounded-lg bg-white" />{{ SITE_NAME }}
        </RouterLink>
        <nav aria-label="Main" class="flex flex-1 flex-wrap items-center gap-1 lg:max-w-[52%]">
          <RouterLink to="/" :class="pill">Home</RouterLink>
          <RouterLink to="/about" :class="pill">About</RouterLink>
          <!-- Explore only appears after log in -->
          <RouterLink v-if="auth.user" to="/explore" :class="pill">Explore</RouterLink>
          <RouterLink to="/help" :class="pill">Help</RouterLink>
        </nav>
        <div class="ml-auto flex flex-wrap items-center gap-2">
          <A11yBar />
          <template v-if="auth.user">
            <RouterLink to="/profile" :class="rpill">Profile</RouterLink>
            <button type="button" :class="rpill" @click="signOut">Log out</button>
          </template>
          <RouterLink v-else to="/login" :class="rpill"><span aria-hidden="true">👤</span> Log in</RouterLink>
        </div>
      </header>

      <!-- PAGE: Explore/Help/Profile fill the rest of the screen with a light panel; Home/About/Login draw on blue + white -->
      <main id="main" class="relative z-10 flex flex-1 flex-col">
        <div :class="$route.meta.hero ? 'flex flex-1 flex-col' : 'flex-1 bg-paper p-4 text-ink sm:p-6'">
          <RouterView :key="$route.path" />
        </div>
      </main>
    </div>

  </div>
</template>
