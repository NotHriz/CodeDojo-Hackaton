<script setup>
// EXPLORE PAGE: search by name, tick access needs, click a map marker or a list item. Both select the same building.
import { ref, computed, onMounted } from 'vue'
import { listPlaces } from '../services/api.js'
import { FACILITIES } from '../services/facilities.js'
import { a11y } from '../composables/useA11y.js'
import MapView from '../components/MapView.vue'
import PlaceDetails from '../components/PlaceDetails.vue'

const places = ref([])
const state = ref('loading') // 'loading' | 'ready' | 'error'
const errorMsg = ref('')
const q = ref('')            // search text
const need = ref([])         // ticked facility keys
const selectedId = ref(null) // chosen building ID (shared by map and list)

// LOAD all buildings once (small pilot dataset). Errors are shown, never hidden behind fake data.
async function load() {
  state.value = 'loading'
  try { places.value = (await listPlaces()).items; state.value = 'ready' }
  catch (e) { errorMsg.value = e.message; state.value = 'error' }
}
onMounted(load)

// SEARCH + FILTER: name must contain the text AND every ticked feature must be "yes". "Unknown" never matches.
const results = computed(() => places.value.filter(p =>
  p.name.toLowerCase().includes(q.value.trim().toLowerCase()) && need.value.every(k => p.facilities[k] === 'yes')))

// Announced to screen readers when results change.
const summary = computed(() => state.value === 'loading' ? 'Loading buildings...'
  : state.value === 'error' ? 'Buildings could not be loaded.' : `${results.value.length} building(s) found`)
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-2">
    <div class="space-y-5">
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
        <button type="button" class="btn-alt mt-3" @click="need = []">Clear filters</button>
      </details>

      <!-- RESULTS LIST: works without the map -->
      <section aria-labelledby="res-h">
        <h2 id="res-h" class="text-xl font-bold">Buildings</h2>
        <p role="status" class="mt-1">{{ summary }}</p>
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

      <PlaceDetails v-if="selectedId" :id="selectedId" />
    </div>

    <!-- MAP: hidden in screen reader mode -->
    <MapView v-if="!a11y.sr" :places="results" :selected-id="selectedId" class="h-80 lg:sticky lg:top-4 lg:h-[34rem]" @select="selectedId = $event" />
  </div>
</template>
