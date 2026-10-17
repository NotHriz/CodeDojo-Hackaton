<script setup>
import { ref } from 'vue'
import { sendChat } from '../services/api.js'
import { chatHistory, formatTime, REPORT_STATUS } from '../services/community-ui.js'
import { FACILITIES, STATUS } from '../services/facilities.js'

const props = defineProps({ selectedPlaceId: String })
const emit = defineEmits(['results', 'select'])
const draft = ref('')
const turns = ref([])
const busy = ref(false)
const error = ref('')
async function send() {
  if (busy.value || !draft.value.trim()) return
  const question = draft.value.trim()
  busy.value = true; error.value = ''
  try {
    const reply = await sendChat({ message: question, history: chatHistory(turns.value), selected_place_id: props.selectedPlaceId || null })
    turns.value.push({ question, reply })
    draft.value = ''
    if (reply.applied_filters !== null) emit('results', reply)
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <section class="card space-y-4" aria-labelledby="chat-heading">
    <h2 id="chat-heading" class="text-xl font-bold">Ask about campus access</h2>
    <p>Ask for buildings or recorded facilities. Answers use community records and are not accessibility guarantees.</p>
    <p v-if="selectedPlaceId">Your selected building is included as context.</p>
    <ol class="max-h-[36rem] space-y-4 overflow-y-auto" aria-label="Conversation">
      <li v-for="(turn, index) in turns" :key="index" class="space-y-3 border-t border-slate-300 pt-3">
        <p class="whitespace-pre-wrap break-words"><strong>You:</strong> {{ turn.question }}</p>
        <p v-if="turn.reply.data_mode === 'demo'" class="font-bold text-no">Fictional local demo data</p>
        <p class="whitespace-pre-wrap break-words"><strong>Assistant:</strong> {{ turn.reply.answer }}</p>
        <p v-if="turn.reply.applied_filters">
          {{ turn.reply.places.length }} shown from
          {{ turn.reply.total_matches === null ? 'a search whose count needs refreshing' : `${turn.reply.total_matches} matching buildings` }}.
          The map and list use these matches. Evidence cards may include an excluded building for comparison.
        </p>
        <p v-if="turn.reply.sources.length" class="text-sm">These records were returned with this answer. Open a building for current conditions.</p>
        <ul aria-label="Answer sources" class="space-y-3">
          <li v-for="source in turn.reply.sources" :key="source.id" class="rounded border-2 border-slate-300 p-3">
            <button type="button" class="btn-alt" @click="emit('select', source.id)">Open {{ source.name }}</button>
            <p v-if="source.is_demo" class="font-bold">Sample data</p>
            <ul class="mt-2">
              <li v-for="facility in FACILITIES.slice(0, 3)" :key="facility.key">
                {{ facility.label }}: {{ STATUS[source.facilities[facility.key] || 'unknown'].text }}
              </li>
            </ul>
            <ul v-if="source.active_warnings.length" class="mt-2 text-no">
              <li v-for="warning in source.active_warnings" :key="warning.report_id">
                {{ REPORT_STATUS[warning.status] }}: {{ warning.description }}
              </li>
            </ul>
            <p v-if="!source.observations.length">No dated observations recorded.</p>
            <ul v-else class="mt-2 text-sm">
              <li v-for="(observation, i) in source.observations" :key="i">
                {{ observation.facility.replaceAll('_', ' ') }}: {{ observation.value }}.
                Source: {{ observation.source }}. Checked: {{ formatTime(observation.observed_at) }}
              </li>
            </ul>
          </li>
        </ul>
      </li>
    </ol>
    <p role="status" aria-live="polite">{{ busy ? 'Checking recorded campus information...' : turns.length ? 'Answer received. Sources and results are available.' : '' }}</p>
    <p v-if="error" role="alert" class="font-bold text-no">{{ error }}</p>
    <form class="space-y-2" @submit.prevent="send">
      <label for="chat-message" class="font-bold">Your question</label>
      <textarea id="chat-message" v-model="draft" class="input" rows="3" maxlength="1000" required :readonly="busy" placeholder="Find a study building with a step-free entrance and accessible toilet"></textarea>
      <div class="flex flex-wrap gap-2">
        <button type="submit" class="btn" :disabled="busy || !draft.trim()">{{ error ? 'Retry question' : 'Ask assistant' }}</button>
        <button type="button" class="btn-alt" :disabled="busy" @click="turns = []; error = ''">Clear conversation</button>
      </div>
    </form>
  </section>
</template>
