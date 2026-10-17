<script setup>
// LOGIN / SIGN UP / FORGOT PASSWORD / RESET: one form, four versions.
// The route's meta.mode (see router.js) picks the version. To change a page's text, fields or links, edit MODES below.
import { reactive, ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import HeroShell from '../components/HeroShell.vue'
import LogoBox from '../components/LogoBox.vue'
import { SITE_NAME } from '../config.js'
import { logIn, signUp, forgot, resetPassword } from '../services/auth.js'

const route = useRoute()
const router = useRouter()

// FIELD DEFINITIONS: label shown, input type, browser autofill hint.
const FIELDS = {
  identifier: { label: 'Username or email', type: 'text', auto: 'username' },
  username: { label: 'Username', type: 'text', auto: 'username' },
  email: { label: 'Email', type: 'email', auto: 'email' },
  password: { label: 'Password', type: 'password', auto: 'current-password' },
  confirm: { label: 'Confirm password', type: 'password', auto: 'new-password' }
}

// PAGE DEFINITIONS: heading, welcome sentence, button text, which fields appear (in order), links at the bottom.
const MODES = {
  login: { title: 'Welcome back', text: 'Log in to check access information before you visit.', button: 'Log in',
    fields: ['identifier', 'password'], remember: true, links: [['/signup', 'Sign up'], ['/forgot', 'Forgot password?']] },
  signup: { title: 'Join Findr', text: 'Create an account to add photos and vote on access information.', button: 'Sign up',
    fields: ['username', 'email', 'password', 'confirm'], links: [['/login', 'Back to log in'], ['/forgot', 'Forgot password?']] },
  forgot: { title: 'Reset your password', text: 'Please enter your email that used for the account for reset password.', button: 'Send verification',
    fields: ['email'], links: [['/login', 'Back to log in']] },
  reset: { title: 'Choose a new password', text: 'Enter a new password for your account.', button: 'Save password',
    fields: ['password', 'confirm'], links: [['/login', 'Back to log in']] }
}

const mode = computed(() => route.meta.mode)
const m = computed(() => MODES[mode.value])
const form = reactive({ identifier: '', username: '', email: '', password: '', confirm: '', remember: true, agree: false })
const error = ref('')   // red message
const done = ref('')    // green message
const busy = ref(false) // disables the button while waiting

// Runs a task, shows its error if it fails.
async function run(task) {
  error.value = ''; done.value = ''; busy.value = true
  try { await task() } catch (e) { error.value = e.message } finally { busy.value = false }
}

// FORM SUBMIT: what happens depends on the page.
const submit = () => run(async () => {
  if (m.value.fields.includes('confirm') && form.password !== form.confirm) throw new Error('Passwords do not match.')
  if (mode.value === 'login') { await logIn(form.identifier, form.password, form.remember); router.push(route.query.next || '/explore') }
  else if (mode.value === 'signup') {
    if (!form.agree) throw new Error('Please accept the Privacy Policy and Terms of Use to continue.')
    if (await signUp(form)) done.value = 'Account created. Check your email to confirm it, then log in.'
    else router.push('/explore')
  }
  else if (mode.value === 'forgot') { await forgot(form.email); done.value = 'Check your email' }
  else { await resetPassword(form.password); router.push('/explore') }
})
</script>

<template>
  <!-- Same blue-and-white layout as the Home page. Left = welcome text, right = the form on the white area. -->
  <HeroShell>
    <template #left>
      <h1 class="font-display text-5xl lowercase sm:text-6xl">{{ SITE_NAME }}</h1>
      <h2 class="mt-10 font-display text-2xl">{{ m.title }}</h2>
      <p class="mt-2 max-w-sm">{{ m.text }}</p>
    </template>

    <template #right>
      <!-- LOGO: set LOGO_SRC in src/config.js. Empty = blank blue square. -->
      <LogoBox size="h-24 w-24" />

      <form class="mt-5 space-y-4" @submit.prevent="submit">
        <!-- FIELDS: built from MODES. Native validation (required/pattern/minlength) runs before submit. -->
        <div v-for="n in m.fields" :key="n">
          <label :for="n" class="font-bold">{{ FIELDS[n].label }}</label>
          <div class="flex gap-2">
            <input :id="n" v-model="form[n]" class="input" required :type="FIELDS[n].type"
              :autocomplete="n === 'password' && mode !== 'login' ? 'new-password' : FIELDS[n].auto"
              :minlength="n === 'password' && mode !== 'login' ? 8 : undefined" />
          </div>
        </div>

        <label v-if="m.remember" class="flex min-h-11 items-center gap-3">
          <input v-model="form.remember" type="checkbox" class="size-6 accent-brand" /> Remember me
        </label>

        <template v-if="mode === 'signup'">
          <label class="flex items-start gap-3 text-sm">
            <input v-model="form.agree" type="checkbox" required class="mt-1 size-5 shrink-0 accent-brand" />
            <span>I agree to the Privacy Policy and Terms of Use.</span>
          </label>
          <div class="space-y-2 text-sm">
            <details class="rounded border-2 border-slate-300 bg-slate-50 p-3">
              <summary class="cursor-pointer font-bold">Privacy Policy</summary>
              <div class="mt-2 space-y-2">
                <p>Akses Campus collects your email and account identity to sign you in and associate contributions with your account. We use submitted reports, votes, observations, notes, and evidence links to provide the community accessibility service.</p>
                <p>Your private identity, vote weight, reliability information, and authentication tokens are not shown in public place pages. Do not submit sensitive personal information, faces, or private documents.</p>
                <p>Demo records may be fictional and are labelled in the application. You can ask the project team to correct or remove your account data during the hackathon pilot.</p>
              </div>
            </details>
            <details class="rounded border-2 border-slate-300 bg-slate-50 p-3">
              <summary class="cursor-pointer font-bold">Terms of Use</summary>
              <div class="mt-2 space-y-2">
                <p>Use Akses Campus respectfully and submit only information you have observed or can clearly identify as a demo contribution. Do not submit harmful, illegal, discriminatory, or misleading content.</p>
                <p>Community corroboration describes member agreement over submitted information; it is not a safety guarantee, formal accessibility certification, or promise that a facility will be available.</p>
                <p>We may restrict abusive submissions and remove content that creates a safety, privacy, or legal risk. This is a hackathon prototype and may be unavailable or incomplete.</p>
              </div>
            </details>
          </div>
        </template>

        <!-- MESSAGES: role=alert is read aloud immediately; role=status politely -->
        <p v-if="error" role="alert" class="font-bold text-no">✖ {{ error }}</p>
        <p v-if="done" role="status" class="font-bold text-yes">✔ {{ done }}</p>

        <button type="submit" class="btn w-full" :disabled="busy">{{ m.button }}</button>
      </form>

      <!-- NAVIGATION to the other account pages -->
      <nav aria-label="Other account options" class="mt-4 flex flex-wrap justify-between gap-x-4">
        <RouterLink v-for="[to, label] in m.links" :key="to" :to="to" class="py-2 font-bold text-brand underline">{{ label }}</RouterLink>
      </nav>
    </template>
  </HeroShell>
</template>
