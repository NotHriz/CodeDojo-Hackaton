<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { getReportHistory } from '../services/api.js'
import { formatTime, HISTORY_ACTION, REPORT_STATUS } from '../services/community-ui.js'

const props = defineProps({ reportId: String, refreshToken: Number })
const open = ref(false)
const items = ref([])
const total = ref(0)
const loaded = ref(false)
const busy = ref(false)
const error = ref('')
let generation = 0
async function load(reset = false) {
  if (busy.value) return
  const current = generation
  busy.value = true; error.value = ''
  const offset = reset ? 0 : items.value.length
  try {
    const page = await getReportHistory(props.reportId, offset)
    if (current !== generation) return
    items.value = reset ? page.items : [...items.value, ...page.items]
    total.value = page.total; loaded.value = true
  } catch (e) { if (current === generation) error.value = e.message }
  finally { if (current === generation) busy.value = false }
}
function toggle(event) {
  open.value = event.target.open
  if (open.value && !loaded.value) load(true)
}
watch(() => props.refreshToken, () => {
  generation++; busy.value = false; loaded.value = false
  items.value = []; total.value = 0; error.value = ''
  if (open.value) load(true)
})
onBeforeUnmount(() => { generation++ })
</script>

<template>
  <details class="mt-3 border-t border-slate-300 pt-2" @toggle="toggle">
    <summary class="min-h-11 cursor-pointer font-bold">Report history</summary>
    <p v-if="busy" role="status">Loading history...</p>
    <div v-if="error" class="my-2">
      <p role="alert" class="text-no">{{ error }}</p>
      <button type="button" class="btn-alt" :disabled="busy" @click="load(!loaded)">Retry history</button>
    </div>
    <p v-if="loaded && !items.length">No history recorded.</p>
    <!-- Keep API order, including equal timestamps; never sort by event UUID. -->
    <ol v-if="items.length" tabindex="0" class="max-h-96 space-y-2 overflow-y-auto" aria-label="Report timeline">
      <li v-for="event in items" :key="event.id" class="border-l-4 border-brand pl-3">
        <p class="font-bold">{{ HISTORY_ACTION[event.action] || event.action }}</p>
        <p><time :datetime="event.occurred_at">{{ formatTime(event.occurred_at) }}</time></p>
        <p>{{ event.previous_status ? `${REPORT_STATUS[event.previous_status]} → ` : '' }}{{ REPORT_STATUS[event.new_status] }}</p>
        <p>{{ event.community.supporters }} supporting, {{ event.community.disputes }} disputing</p>
      </li>
    </ol>
    <button v-if="loaded && items.length < total" type="button" class="btn-alt mt-3" :disabled="busy" @click="load()">Load more history</button>
  </details>
</template>
