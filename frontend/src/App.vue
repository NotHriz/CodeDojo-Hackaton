<script setup>
// APP SHELL: header, navigation, page area and footer shown on every page.
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { auth, logOut } from './services/auth.js'
import A11yBar from './components/A11yBar.vue'

const router = useRouter()
async function signOut() { await logOut(); router.push('/login') }
</script>

<template>
  <!-- SKIP LINK: first Tab stop, jumps past the header -->
  <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[2000] focus:rounded focus:bg-white focus:px-4 focus:py-3 focus:font-bold focus:text-brand">Skip to main content</a>

  <!-- HEADER: site name, navigation (changes when signed in), accessibility panel -->
  <header class="bg-brand text-white">
    <div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
      <RouterLink to="/" class="text-2xl font-bold">Akses Campus</RouterLink>
      <nav aria-label="Main" class="flex flex-wrap items-center gap-x-5 gap-y-1">
        <RouterLink to="/" class="py-2 font-bold aria-[current=page]:underline">Explore</RouterLink>
        <RouterLink to="/help" class="py-2 font-bold aria-[current=page]:underline">Help</RouterLink>
        <template v-if="auth.user">
          <RouterLink to="/profile" class="py-2 font-bold aria-[current=page]:underline">Profile</RouterLink>
          <button type="button" class="py-2 font-bold underline" @click="signOut">Log out</button>
        </template>
        <RouterLink v-else to="/login" class="py-2 font-bold aria-[current=page]:underline">Log in</RouterLink>
      </nav>
      <A11yBar />
    </div>
  </header>

  <!-- PAGE: :key resets the page when switching between login/signup/forgot -->
  <main id="main" class="mx-auto max-w-7xl px-4 py-6">
    <RouterView :key="$route.path" />
  </main>

  <footer class="mx-auto max-w-7xl px-4 pb-8">
    <p class="max-w-prose">Access information is shared by the community and is a guide, not a guarantee. Conditions can change.</p>
  </footer>
</template>
