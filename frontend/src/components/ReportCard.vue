<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { castVote, submitClearance, voteClearance } from '../services/api.js'
import { auth } from '../services/auth.js'
import { formatTime, localDateTime, REPORT_STATUS, retrySubmission } from '../services/community-ui.js'
import ReportHistory from './ReportHistory.vue'

const props = defineProps({ report: Object })
const emit = defineEmits(['updated', 'changed'])
const busy = ref(false)
const error = ref('')
const done = ref('')
const description = ref('')
const observed = ref(localDateTime())
const evidence = ref('')
const refreshToken = ref(0)
const submission = retrySubmission()
let active = true
onBeforeUnmount(() => { active = false })

async function mutate(operation, success) {
  if (busy.value) return false
  busy.value = true; error.value = ''; done.value = ''
  try {
    const result = await operation()
    if (!active) return false
    if (result.clearance_observations) emit('updated', result)
    refreshToken.value++
    done.value = result.clearance_observations ? `${success} Report status: ${REPORT_STATUS[result.status]}.` : success
    emit('changed')
    return true
  } catch (e) { if (active) error.value = e.message; return false }
  finally { if (active) busy.value = false }
}
async function clearBarrier() {
  let body
  try {
    const date = new Date(observed.value)
    if (!Number.isFinite(date.getTime())) throw new Error('Choose when you observed the barrier clearing.')
    if (date.getTime() < new Date(props.report.observed_at).getTime()) throw new Error('The clearing observation must follow the reported barrier.')
    if (evidence.value.trim() && !['https:', 'http:'].includes(new URL(evidence.value.trim()).protocol)) throw new Error('Evidence must be an HTTP or HTTPS link.')
    body = { description: description.value.trim(), observed_at: date.toISOString(), evidence_urls: evidence.value.trim() ? [evidence.value.trim()] : [] }
  } catch (e) { error.value = e.message; return }
  const pending = submission.prepare(body)
  if (await mutate(() => submitClearance(props.report.id, pending.body, pending.key), 'Clearing observation saved as unverified. Other members must corroborate it.')) {
    submission.reset(); description.value = ''; evidence.value = ''; observed.value = localDateTime()
  }
}
</script>

<template>
  <article class="rounded border-2 border-slate-300 p-3 space-y-2" :aria-label="`Barrier report: ${report.description}`">
    <h4 class="font-bold">{{ REPORT_STATUS[report.status] }}</h4>
    <p>{{ report.description }}</p>
    <p>Observed: <time :datetime="report.observed_at">{{ formatTime(report.observed_at) }}</time></p>
    <img v-for="url in report.evidence_urls" :key="url" :src="url" alt="Evidence for this reported barrier" class="mt-2 max-h-48 rounded" />
    <p>{{ report.community.supporters }} supporting, {{ report.community.disputes }} disputing the original report</p>
    <div v-if="auth.user" class="flex flex-wrap gap-2">
      <button type="button" class="btn-alt" :disabled="busy" @click="mutate(() => castVote('reports', report.id, 'corroborate'), 'Report vote saved.')">Corroborate report</button>
      <button type="button" class="btn-alt" :disabled="busy" @click="mutate(() => castVote('reports', report.id, 'dispute'), 'Report vote saved.')">Dispute report</button>
    </div>

    <section v-if="report.clearance_observations.length" aria-label="Clearing observations" class="space-y-3 pt-2">
      <h5 class="font-bold">Clearing observations</h5>
      <article v-for="claim in report.clearance_observations" :key="claim.id" class="rounded border border-ink p-3">
        <p class="font-bold">{{ REPORT_STATUS[claim.status] }}</p>
        <p>{{ claim.description }}</p>
        <p>Observed: <time :datetime="claim.observed_at">{{ formatTime(claim.observed_at) }}</time></p>
        <p>{{ claim.community.supporters }} supporting, {{ claim.community.disputes }} disputing</p>
        <a v-for="url in claim.evidence_urls" :key="url" :href="url" target="_blank" rel="noopener noreferrer" class="block min-h-11 break-all font-bold text-brand underline">View clearing evidence</a>
        <div v-if="auth.user" class="flex flex-wrap gap-2">
          <button type="button" class="btn-alt" :disabled="busy" @click="mutate(() => voteClearance(report.id, claim.id, 'corroborate'), 'Clearing vote saved.')">Corroborate clearing</button>
          <button type="button" class="btn-alt" :disabled="busy" @click="mutate(() => voteClearance(report.id, claim.id, 'dispute'), 'Clearing vote saved.')">Dispute clearing</button>
        </div>
      </article>
    </section>

    <details v-if="auth.user" class="pt-2">
      <summary class="min-h-11 cursor-pointer font-bold">Report that this barrier has cleared</summary>
      <form class="space-y-3" @submit.prevent="clearBarrier">
        <p>A clearing claim starts unverified. Community corroboration is not a safety guarantee.</p>
        <div><label :for="`clear-description-${report.id}`" class="font-bold">What has changed?</label>
          <textarea :id="`clear-description-${report.id}`" v-model="description" class="input" rows="3" maxlength="2000" required :readonly="busy"></textarea></div>
        <div><label :for="`clear-time-${report.id}`" class="font-bold">When did you observe it? (your local time)</label>
          <input :id="`clear-time-${report.id}`" v-model="observed" type="datetime-local" step="0.001" class="input" required :readonly="busy" /></div>
        <div><label :for="`clear-evidence-${report.id}`" class="font-bold">Evidence link (optional, public HTTP/HTTPS)</label>
          <input :id="`clear-evidence-${report.id}`" v-model="evidence" type="url" class="input" :readonly="busy" /></div>
        <button type="submit" class="btn" :disabled="busy || !description.trim()">Submit clearing observation</button>
      </form>
    </details>
    <p v-else><RouterLink to="/login" class="font-bold text-brand underline">Log in</RouterLink> to report a clearing or vote.</p>
    <p v-if="busy" role="status">Saving contribution...</p>
    <p v-if="error" role="alert" class="font-bold text-no">{{ error }}</p>
    <p v-if="done" role="status" class="font-bold text-yes">{{ done }}</p>
    <ReportHistory :report-id="report.id" :refresh-token="refreshToken" />
  </article>
</template>
