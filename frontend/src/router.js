// ROUTES: one line per page. meta.auth = true means "must be signed in".
// Login/Signup/Forgot/Reset share one component; meta.mode picks which version shows.
import { createRouter, createWebHistory } from 'vue-router'
import { auth, authReady } from './services/auth.js'
import ExploreView from './views/ExploreView.vue'
import AuthView from './views/AuthView.vue'
import ProfileView from './views/ProfileView.vue'
import HelpView from './views/HelpView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ExploreView },
    { path: '/login', component: AuthView, meta: { mode: 'login' } },
    { path: '/signup', component: AuthView, meta: { mode: 'signup' } },
    { path: '/forgot', component: AuthView, meta: { mode: 'forgot' } },
    { path: '/reset', component: AuthView, meta: { mode: 'reset' } },
    { path: '/profile', component: ProfileView, meta: { auth: true } },
    { path: '/help', component: HelpView, meta: { auth: true } }
  ]
})

// GUARD: signed-out visitors to a protected page are sent to login, then returned.
router.beforeEach(async to => {
  await authReady
  if (to.meta.auth && !auth.user) return { path: '/login', query: { next: to.fullPath } }
})

export default router
