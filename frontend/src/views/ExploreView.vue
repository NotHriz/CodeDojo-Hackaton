<script setup>
// EXPLORE PAGE: search by name, tick access needs, click a map marker or a list item. Both select the same building.
import { ref, computed, onMounted, watch } from 'vue'
import { listPlaces } from '../services/api.js'
import { FACILITIES } from '../services/facilities.js'
import { a11y } from '../composables/useA11y.js'
import MapView from '../components/MapView.vue'
import PlaceDetails from '../components/PlaceDetails.vue'
import ChatPanel from '../components/ChatPanel.vue'

const places = ref([])
const state = ref('loading') // 'loading' | 'ready' | 'error'
const errorMsg = ref('')
const q = ref('')            // search text
const need = ref([])         // ticked facility keys
const category = ref('')
const chatMatches = ref(null)
const chatTotal = ref(null)
const refreshError = ref('')
let refreshVersion = 0
const selectedId = ref(null) // chosen building ID (shared by map and list)

// LOAD all buildings once (small pilot dataset). Errors are shown, never hidden behind fake data.
async function load() {
  state.value = 'loading'
  try { places.value = (await listPlaces()).items; state.value = 'ready' }
  catch (e) { errorMsg.value = e.message; state.value = 'error' }
}
onMounted(load)

// SEARCH + FILTER: name must contain the text AND every ticked feature must be "yes". "Unknown" never matches.
const categories = computed(() => [...new Set(places.value.map(p => p.category))].sort())
const results = computed(() => {
  const pool = chatMatches.value === null ? places.value : chatMatches.value
  return pool.filter(p => p.name.toLowerCase().includes(q.value.trim().toLowerCase())
    && (!category.value || p.category.toLowerCase() === category.value.toLowerCase())
    && need.value.every(k => p.facilities[k] === 'yes'))
})
watch([q, need, category], () => { chatMatches.value = null }, { deep: true, flush: 'sync' })
function applyChatResults(reply) {
  q.value = reply.applied_filters.q || ''
  category.value = reply.applied_filters.category || ''
  need.value = ['step_free_entrance', 'accessible_toilet', 'designated_parking'].filter(key => reply.applied_filters[key])
  chatMatches.value = reply.places
  chatTotal.value = reply.total_matches
}
async function refreshPlaces() {
  const version = ++refreshVersion
  refreshError.value = ''
  try {
    const response = await listPlaces()
    if (version !== refreshVersion) return
    places.value = response.items
    if (chatMatches.value !== null) {
      const previousIds = new Set(chatMatches.value.map(p => p.id))
      chatMatches.value = places.value.filter(p => previousIds.has(p.id))
    }
  } catch (e) { if (version === refreshVersion) refreshError.value = `Could not refresh map/list warnings: ${e.message}` }
}

// Announced to screen readers when results change.
const summary = computed(() => state.value === 'loading' ? 'Loading buildings...'
  : state.value === 'error' ? 'Buildings could not be loaded.' : `${results.value.length} building(s) found`)
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-2">
    <div class="space-y-5">
      <ChatPanel :selected-place-id="selectedId" @results="applyChatResults" @select="selectedId = $event" />
      <p v-if="refreshError" role="alert" class="text-no">{{ refreshError }}</p>
      <button v-if="refreshError" type="button" class="btn-alt" @click="refreshPlaces">Refresh building warnings</button>
      <!-- SEARCH -->
      <form role="search" @submit.prevent>
        <label for="q" class="text-xl font-bold">Search for a building</label>
        <input id="q" v-model="q" type="search" autocomplete="off" placeholder="For example: Library" class="input" />
      </form>

      <!-- FILTERS: add a facility in services/facilities.js and it appears here -->
      <details class="card">
        <summary class="flex min-h-11 cursor-pointer items-center font-bold">Filter by access features ({{ need.length }} selected)</summary>
        <fieldset class="mt-3">
          <legend class="sr-only">Show only buildings with</legend>
          <label v-for="f in FACILITIES" :key="f.key" class="flex min-h-11 items-center gap-3">
            <input v-model="need" type="checkbox" :value="f.key" class="size-6 accent-brand" /> {{ f.label }}
          </label>
        </fieldset>
        <label for="category" class="block font-bold mt-2">Building category</label>
        <select id="category" v-model="category" class="input">
          <option value="">All categories</option>
          <option v-for="item in categories" :key="item" :value="item">{{ item }}</option>
          <option v-if="category && !categories.includes(category)" :value="category">{{ category }}</option>
        </select>
        <button type="button" class="btn-alt mt-3" @click="need = []; category = ''; q = ''; chatMatches = null">Clear filters</button>
      </details>

      <!-- RESULTS LIST: works without the map -->
      <section aria-labelledby="res-h">
        <h2 id="res-h" class="text-xl font-bold">Buildings</h2>
        <p role="status" class="mt-1">{{ summary }}</p>
        <div v-if="chatMatches !== null" class="my-2">
          <p>Assistant result page: {{ results.length }} shown. {{ chatTotal === null ? 'Search count needs refreshing.' : `${chatTotal} total matches at search time.` }}</p>
          <button type="button" class="btn-alt" @click="chatMatches = null">Search all buildings with these filters</button>
        </div>
        <div v-if="state === 'error'" class="mt-3">
          <p role="alert" class="font-bold text-no">✖ {{ errorMsg }}</p>
          <button type="button" class="btn mt-2" @click="load">Try again</button>
        </div>
        <ul v-else-if="results.length" class="mt-3 space-y-3">
          <li v-for="p in results" :key="p.id">
            <button type="button" :aria-current="p.id === selectedId ? 'true' : undefined" @click="selectedId = p.id"
              class="min-h-14 w-full rounded-lg border-2 border-ink bg-white p-3 text-left aria-[current=true]:border-4 aria-[current=true]:border-brand">
              <span class="block font-bold">{{ p.name }}</span>
              <span v-if="p.active_warnings.length" class="block font-bold text-no">⚠ {{ p.active_warnings.length }} active barrier report(s)</span>
            </button>
          </li>
        </ul>
        <p v-else-if="state === 'ready'" class="mt-3">No buildings match. Try another name or clear some filters.</p>
      </section>

      <PlaceDetails v-if="selectedId" :id="selectedId" @changed="refreshPlaces" />
    </div>

    <!-- MAP: hidden in screen reader mode -->
    <MapView v-if="!a11y.sr" :places="results" :selected-id="selectedId" class="h-80 lg:sticky lg:top-4 lg:h-[34rem]" @select="selectedId = $event" />
  </div>
</template>
