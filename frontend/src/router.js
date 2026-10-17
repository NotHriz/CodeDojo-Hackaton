// ROUTES: one line per page.
//   meta.auth = true  -> must be logged in (otherwise redirected to /login, then returned)
//   meta.hero = true  -> uses the blue/white design with yellow stripes (see components/HeroShell.vue)
// Login/Signup/Forgot/Reset share one component; meta.mode picks which version shows.
import { createRouter, createWebHistory } from 'vue-router'
import { auth, authReady } from './services/auth.js'
import HomeView from './views/HomeView.vue'
import AboutView from './views/AboutView.vue'
import ExploreView from './views/ExploreView.vue'
import AuthView from './views/AuthView.vue'
import ProfileView from './views/ProfileView.vue'
import HelpView from './views/HelpView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView, meta: { hero: true } },
    { path: '/about', component: AboutView, meta: { hero: true } },
    { path: '/login', component: AuthView, meta: { hero: true, mode: 'login' } },
    { path: '/signup', component: AuthView, meta: { hero: true, mode: 'signup' } },
    { path: '/forgot', component: AuthView, meta: { hero: true, mode: 'forgot' } },
    { path: '/reset', component: AuthView, meta: { hero: true, mode: 'reset' } },
    { path: '/explore', component: ExploreView, meta: { auth: true } }, // login required
    { path: '/profile', component: ProfileView, meta: { auth: true } },
    { path: '/help', component: HelpView }                               // anyone can read; sending a ticket needs login
  ]
})

router.beforeEach(async to => {
  await authReady
  if (to.meta.auth && !auth.user) return { path: '/login', query: { next: to.fullPath } }
})

export default router
