<script setup>
// APP SHELL: the dark page, the big blue card, the navigation pills and the footer. Shown on every page.
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { auth, logOut } from './services/auth.js'
import { SITE_NAME } from './config.js'
import A11yBar from './components/A11yBar.vue'

const router = useRouter()
async function signOut() { await logOut(); router.push('/login') }
// PILL STYLE for nav links. The current page gets a visible outline (aria-current is set by the router).
const pill = 'rounded-full border-2 border-transparent px-4 py-2 font-bold uppercase tracking-wide aria-[current=page]:border-white/70'
</script>

<template>
  <!-- SKIP LINK: first Tab stop -->
  <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[2000] focus:rounded focus:bg-white focus:px-4 focus:py-3 focus:font-bold focus:text-brand">Skip to main content</a>

  <div class="mx-auto max-w-7xl p-3 sm:p-6">
    <!-- BIG BLUE CARD (the rounded blue panel in the design). overflow-hidden clips the yellow stripes to its corners. -->
    <div class="relative overflow-hidden rounded-3xl bg-brand text-white shadow-2xl">

      <!-- HEADER: site name, nav pills, mail icon, login pill, accessibility panel -->
      <header class="relative z-10 flex flex-wrap items-center gap-3 px-4 py-4 sm:px-8">
        <RouterLink to="/" class="mr-2 font-display text-2xl font-bold">{{ SITE_NAME }}</RouterLink>
        <nav aria-label="Main" class="flex flex-1 flex-wrap items-center gap-1">
          <RouterLink to="/" :class="pill">Home</RouterLink>
          <RouterLink to="/about" :class="pill">About</RouterLink>
          <RouterLink to="/explore" :class="pill">Explore</RouterLink>
          <RouterLink to="/help" :class="pill">Help</RouterLink>
          <!-- Mail icon: shortcut to the Help page's contact form -->
          <RouterLink to="/help#contact" aria-label="Contact support" class="ml-1 grid size-11 place-items-center rounded-full bg-white text-xl text-brand"><span aria-hidden="true">✉</span></RouterLink>
        </nav>
        <template v-if="auth.user">
          <RouterLink to="/profile" :class="pill">Profile</RouterLink>
          <button type="button" :class="pill" @click="signOut">Log out</button>
        </template>
        <RouterLink v-else to="/login" :class="pill + ' bg-white !text-brand'"><span aria-hidden="true">👤</span> Log in</RouterLink>
        <A11yBar />
      </header>

      <!-- PAGE: Home/About/Login draw straight on the blue card; other pages sit on a light panel -->
      <main id="main">
        <div :class="$route.meta.hero ? '' : 'relative z-10 m-3 rounded-2xl bg-paper p-4 text-ink sm:m-5 sm:p-6'">
          <RouterView :key="$route.path" />
        </div>
      </main>
    </div>

    <footer class="px-2 py-6 text-white">
      <p class="max-w-prose">Access information is shared by the community and is a guide, not a guarantee. Conditions can change.</p>
    </footer>
  </div>
</template>
