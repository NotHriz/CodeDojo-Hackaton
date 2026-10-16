<script setup>
// GOOGLE MAP: one marker per building. Clicking (or pressing Enter on) a marker selects that building.
// Needs VITE_GOOGLE_MAPS_API_KEY and VITE_GOOGLE_MAPS_MAP_ID. Without them the list still works.
import { ref, onMounted, watch } from 'vue'

const props = defineProps({ places: Array, selectedId: String })
const emit = defineEmits(['select'])
const el = ref(null)
const error = ref('')
const KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
const MAP_ID = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID
const START = { lat: 3.2514, lng: 101.7348 } // CHANGE: where the map opens (IIUM Gombak). Zoom is set below.
let map, markers = []

// Loads Google's script once.
function loadGoogle() {
  return new Promise((resolve, reject) => {
    if (window.google?.maps) return resolve()
    window.__gmReady = resolve
    const s = document.createElement('script')
    s.src = `https://maps.googleapis.com/maps/api/js?key=${KEY}&v=weekly&libraries=marker&callback=__gmReady`
    s.onerror = reject
    document.head.append(s)
  })
}

// Redraws markers whenever the search/filter results change.
function draw() {
  markers.forEach(m => (m.map = null))
  markers = props.places.map(p => {
    const m = new google.maps.marker.AdvancedMarkerElement({
      map, title: p.name, gmpClickable: true, // title = text label for screen readers
      position: { lat: p.coordinates.latitude, lng: p.coordinates.longitude }
    })
    m.addListener('click', () => emit('select', p.id))
    return m
  })
}

onMounted(async () => {
  if (!KEY || !MAP_ID) { error.value = 'The map is not configured yet. Use the building list.'; return }
  try { await loadGoogle(); map = new google.maps.Map(el.value, { center: START, zoom: 16, mapId: MAP_ID }); draw() }
  catch { error.value = 'The map could not load. Use the building list.' }
})
watch(() => props.places, () => map && draw())
// Moving the map when a building is chosen from the list keeps both selections in sync.
watch(() => props.selectedId, id => {
  const p = props.places.find(x => x.id === id)
  if (p && map) { map.panTo({ lat: p.coordinates.latitude, lng: p.coordinates.longitude }); map.setZoom(18) }
})
</script>

<template>
  <p v-if="error" class="card">{{ error }}</p>
  <div v-show="!error" ref="el" role="region" aria-label="Map of buildings. The building list has the same information."
    class="rounded-lg border-2 border-ink"></div>
</template>
