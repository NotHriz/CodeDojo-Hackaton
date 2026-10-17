<script setup>
// HELP PAGE, laid out like nike.com/my/help: "Get help" title, search, Quick Assists (topic accordions), Contact us.
// Anyone can read it. Sending a ticket needs login and calls POST /api/tickets (backend snippet is in INTEGRATION.md).
import { reactive, ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { createTicket } from '../services/api.js'
import { auth } from '../services/auth.js'

// QUICK ASSISTS: edit freely. Each topic is one accordion; each question opens its answer.
const TOPICS = [
  { title: 'Using Findr', items: [
    ['How do I find a building?', 'Log in, open Explore, then search by name or click a pin on the map.'],
    ['How do I filter by access features?', 'Open "Filter by access features" and tick what you need. Only buildings recorded as Yes are shown. "Not checked yet" never counts as a match.'] ] },
  { title: 'Adding information', items: [
    ['How do I add a photo or an update?', 'Select a building, then use Add information at the bottom of its details. You must be logged in.'],
    ['What does Unverified mean?', 'Other members have not voted yet. When enough different people agree, it becomes Confirmed by community. This is agreement, not certification.'] ] },
  { title: 'Your account', items: [
    ['How do I change my username or password?', 'Open Profile. You must enter your current password for any change.'],
    ['I forgot my password.', 'On the log in page choose Forgot password. We email you a link to set a new one.'] ] },
  { title: 'Accessibility settings', items: [
    ['How do I make text bigger or use grey scale?', 'Use the Accessibility settings button in the header: text size slider, grey scale, colour-blind safe colours and screen reader mode.'] ] }
]
const CATEGORIES = ['Wrong accessibility information', 'Problem with my account', 'Something is not working', 'Other']

// SEARCH: keeps only questions that contain the typed words.
const q = ref('')
const shown = computed(() => {
  const s = q.value.trim().toLowerCase()
  return TOPICS.map(t => ({ ...t, items: t.items.filter(([a, b]) => !s || (a + b).toLowerCase().includes(s)) })).filter(t => t.items.length)
})

// TICKET FORM: the typed text is kept if sending fails, so nothing is lost.
const form = reactive({ category: CATEGORIES[0], subject: '', message: '' })
const error = ref('')
const sent = ref(false)
const busy = ref(false)
async function send() {
  error.value = ''; sent.value = false; busy.value = true
  try { await createTicket(form); sent.value = true; form.subject = ''; form.message = '' }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <div class="space-y-8">
    <!-- TITLE + SEARCH -->
    <header>
      <h1 class="font-display text-3xl font-bold uppercase">Get help</h1>
      <form role="search" class="mt-3 max-w-xl" @submit.prevent>
        <label for="hq" class="font-bold">What can we help you with?</label>
        <input id="hq" v-model="q" type="search" class="input" autocomplete="off" />
      </form>
    </header>

    <!-- QUICK ASSISTS -->
    <section aria-labelledby="qa-h">
      <h2 id="qa-h" class="text-xl font-bold">Quick assists</h2>
      <p>Answers to common questions are one click away.</p>
      <p v-if="!shown.length" role="status" class="mt-3">No answers match. Send us a ticket below.</p>
      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <details v-for="t in shown" :key="t.title" :open="q.trim() !== ''" class="card">
          <summary class="flex min-h-11 cursor-pointer items-center text-lg font-bold">{{ t.title }}</summary>
          <details v-for="[a, b] in t.items" :key="a" class="border-t border-slate-300 py-1">
            <summary class="flex min-h-11 cursor-pointer items-center">{{ a }}</summary>
            <p class="pb-2">{{ b }}</p>
          </details>
        </details>
      </div>
    </section>

    <!-- CONTACT US -->
    <section id="contact" aria-labelledby="ct-h" class="max-w-xl">
      <h2 id="ct-h" class="text-xl font-bold">Contact us</h2>
      <p v-if="!auth.user" class="card mt-3"><RouterLink to="/login?next=/help%23contact" class="font-bold text-brand underline">Log in</RouterLink> to send a ticket.</p>
      <form v-else class="card mt-3 space-y-4" @submit.prevent="send">
        <h3 class="text-lg font-bold">Send a ticket</h3>
        <div><label for="cat" class="font-bold">Topic</label>
          <select id="cat" v-model="form.category" class="input"><option v-for="c in CATEGORIES" :key="c">{{ c }}</option></select></div>
        <div><label for="sub" class="font-bold">Subject (3 to 120 characters)</label>
          <input id="sub" v-model="form.subject" required minlength="3" maxlength="120" class="input" /></div>
        <div><label for="msg" class="font-bold">Message (10 to 2000 characters)</label>
          <textarea id="msg" v-model="form.message" required minlength="10" maxlength="2000" rows="5" class="input"></textarea></div>
        <p v-if="error" role="alert" class="font-bold text-no">✖ {{ error }}</p>
        <p v-if="sent" role="status" class="font-bold text-yes">✔ Ticket sent. Thank you.</p>
        <button type="submit" class="btn w-full" :disabled="busy">Send ticket</button>
      </form>
    </section>
  </div>
</template>
