<script setup>
// BUILDING DETAILS: access features, photos, barrier reports with voting, and a form to add information.
// Everything added here is sent to the backend and shown as "unverified" until the community votes.
import { ref, reactive, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getPlace, listReports, castVote, submitObservation, submitReport, uploadPhoto } from '../services/api.js'
import { FACILITIES, STATUS } from '../services/facilities.js'
import { auth } from '../services/auth.js'
import { a11y } from '../composables/useA11y.js'

const props = defineProps({ id: String })
const place = ref(null)
const reports = ref([])
const state = ref('loading')
const error = ref('')
const done = ref('')
const busy = ref(false)
const root = ref(null)

// LOAD the building and its reports whenever a different building is chosen.
async function load() {
  state.value = 'loading'
  try {
    const [p, r] = await Promise.all([getPlace(props.id), listReports(props.id)])
    place.value = p; reports.value = r.items; state.value = 'ready'
    root.value?.focus() // moves keyboard/screen reader focus to the new details
  } catch (e) { error.value = e.message; state.value = 'error' }
}
watch(() => props.id, load, { immediate: true })

// WORDS for report statuses (shown instead of raw codes)
const REPORT = { unverified: 'Unverified', community_corroborated: 'Confirmed by community', disputed: 'Disputed', resolved: 'Resolved' }

// VOTING: kind is 'reports' (backend ready) or 'observations' (backend must add). Reloads to show new counts.
async function vote(kind, id, stance) {
  error.value = ''; done.value = ''
  try { await castVote(kind, id, stance); done.value = 'Your vote was saved.'; await load() }
  catch (e) { error.value = e.message }
}

// CONTRIBUTE FORM
const form = reactive({ kind: 'facility', facility: FACILITIES[0].key, value: 'yes', description: '', file: null })
let idem = crypto.randomUUID() // one key per intended submission, reused on retry so the backend never saves duplicates

async function submit() {
  error.value = ''; done.value = ''; busy.value = true
  try {
    const evidence_urls = form.file ? [(await uploadPhoto(form.file)).url] : []
    if (form.kind === 'facility')
      await submitObservation(props.id, { facility: form.facility, value: form.value, notes: form.description || null, observed_at: new Date().toISOString(), evidence_urls }, idem)
    else
      await submitReport({ place_id: props.id, barrier_type: 'temporary_barrier', description: form.description, observed_at: new Date().toISOString(), evidence_urls }, idem)
    idem = crypto.randomUUID(); form.description = ''; form.file = null
    done.value = 'Thank you. Your information was sent and is unverified until others vote.'
    await load()
  } catch (e) { error.value = e.message } finally { busy.value = false }
}

// READ ALOUD (screen reader mode): speaks a short summary with the browser's built-in voice.
function readAloud() {
  const t = FACILITIES.map(f => `${f.label}: ${STATUS[place.value.facilities[f.key] ?? 'unknown'].text}`).join('. ')
  speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(`${place.value.name}. ${t}`))
}
</script>

<template>
  <section ref="root" tabindex="-1" aria-labelledby="pd-h" class="card space-y-5">
    <p v-if="state === 'loading'" role="status">Loading details...</p>
    <p v-else-if="state === 'error'" role="alert" class="font-bold text-no">✖ {{ error }}</p>

    <template v-else>
      <!-- HEADER -->
      <div>
        <h2 id="pd-h" class="text-2xl font-bold">{{ place.name }}</h2>
        <p v-if="place.is_demo" class="mt-1 inline-block rounded border-2 border-ink px-2 font-bold">Sample data</p>
        <p v-if="place.description" class="mt-2">{{ place.description }}</p>
        <button v-if="a11y.sr" type="button" class="btn-alt mt-2" @click="readAloud">Read aloud</button>
      </div>

      <!-- ACCESS FEATURES: all rows from services/facilities.js; missing data shows "Not checked yet" -->
      <div>
        <h3 class="text-xl font-bold">Access features</h3>
        <ul class="divide-y divide-slate-300">
          <li v-for="f in FACILITIES" :key="f.key" class="flex min-h-11 items-center justify-between gap-3 py-2">
            <span>{{ f.label }}</span>
            <strong :class="STATUS[place.facilities[f.key] ?? 'unknown'].cls">
              <span aria-hidden="true">{{ STATUS[place.facilities[f.key] ?? 'unknown'].icon }}</span>
              {{ STATUS[place.facilities[f.key] ?? 'unknown'].text }}
            </strong>
          </li>
        </ul>
      </div>

      <!-- EVIDENCE: who said it, when, photos, and votes -->
      <div v-if="place.observations.length">
        <h3 class="text-xl font-bold">Evidence</h3>
        <ul class="space-y-3">
          <li v-for="(o, i) in place.observations" :key="o.id ?? i" class="rounded border-2 border-slate-300 p-3">
            <p class="font-bold">{{ FACILITIES.find(f => f.key === o.facility)?.label ?? o.facility }}: {{ STATUS[o.value].text }}</p>
            <p>Source: {{ o.source }}. Checked: {{ o.observed_at ? new Date(o.observed_at).toLocaleDateString() : 'date unknown' }}</p>
            <p v-if="o.notes">{{ o.notes }}</p>
            <img v-for="u in o.evidence_urls" :key="u" :src="u" :alt="`Photo for ${o.facility.replaceAll('_', ' ')} at ${place.name}`" class="mt-2 max-h-48 rounded" />
            <div v-if="o.id && auth.user" class="mt-2 flex flex-wrap gap-2">
              <button type="button" class="btn-alt" @click="vote('observations', o.id, 'corroborate')">This is correct</button>
              <button type="button" class="btn-alt" @click="vote('observations', o.id, 'dispute')">This is wrong</button>
            </div>
          </li>
        </ul>
      </div>

      <!-- BARRIER REPORTS with community votes -->
      <div>
        <h3 class="text-xl font-bold">Barrier reports</h3>
        <p v-if="!reports.length">No active reports.</p>
        <ul class="space-y-3">
          <li v-for="r in reports" :key="r.id" class="rounded border-2 border-slate-300 p-3">
            <p class="font-bold">⚠ {{ REPORT[r.status] }}</p>
            <p>{{ r.description }}</p>
            <img v-for="u in r.evidence_urls" :key="u" :src="u" :alt="`Photo of reported barrier at ${place.name}`" class="mt-2 max-h-48 rounded" />
            <p class="mt-1">{{ r.community.supporters }} agree, {{ r.community.disputes }} disagree</p>
            <div v-if="auth.user && r.status !== 'resolved'" class="mt-2 flex flex-wrap gap-2">
              <button type="button" class="btn-alt" @click="vote('reports', r.id, 'corroborate')">I agree</button>
              <button type="button" class="btn-alt" @click="vote('reports', r.id, 'dispute')">I disagree</button>
            </div>
          </li>
        </ul>
      </div>

      <p v-if="error" role="alert" class="font-bold text-no">✖ {{ error }}</p>
      <p v-if="done" role="status" class="font-bold text-yes">✔ {{ done }}</p>

      <!-- ADD INFORMATION: needs sign-in (the backend checks this too) -->
      <form v-if="auth.user" class="space-y-3 border-t-2 border-slate-300 pt-4" @submit.prevent="submit">
        <h3 class="text-xl font-bold">Add information</h3>
        <fieldset>
          <legend class="font-bold">What are you adding?</legend>
          <label class="flex min-h-11 items-center gap-3"><input v-model="form.kind" type="radio" value="facility" class="size-6 accent-brand" /> An access feature</label>
          <label class="flex min-h-11 items-center gap-3"><input v-model="form.kind" type="radio" value="barrier" class="size-6 accent-brand" /> A temporary barrier</label>
        </fieldset>
        <template v-if="form.kind === 'facility'">
          <div><label for="fac" class="font-bold">Feature</label>
            <select id="fac" v-model="form.facility" class="input"><option v-for="f in FACILITIES" :key="f.key" :value="f.key">{{ f.label }}</option></select></div>
          <div><label for="val" class="font-bold">Is it available?</label>
            <select id="val" v-model="form.value" class="input"><option value="yes">Yes</option><option value="no">No</option></select></div>
        </template>
        <div><label for="desc" class="font-bold">{{ form.kind === 'barrier' ? 'Describe the barrier' : 'Notes (optional)' }}</label>
          <textarea id="desc" v-model="form.description" class="input" rows="3" maxlength="2000" :required="form.kind === 'barrier'"></textarea></div>
        <div><label for="photo" class="font-bold">Photo (optional)</label>
          <input id="photo" type="file" accept="image/*" class="input py-2" @change="form.file = $event.target.files[0] ?? null" /></div>
        <p>Do not include faces or personal information in photos.</p>
        <button type="submit" class="btn" :disabled="busy">Send information</button>
      </form>
      <p v-else><RouterLink to="/login" class="font-bold text-brand underline">Log in</RouterLink> to add information or vote.</p>
    </template>
  </section>
</template>
