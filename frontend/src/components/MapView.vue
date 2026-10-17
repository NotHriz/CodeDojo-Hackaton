<script setup>
// LEAFLET MAP (OpenStreetMap tiles, no API key). One pin per building; clicking or pressing Enter on a pin selects it.
// Pins come from the backend's building coordinates. In dev mode, clicking empty map shows the coordinates to copy.
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import L from 'leaflet'
import icon from 'leaflet/dist/images/marker-icon.png'
import icon2x from 'leaflet/dist/images/marker-icon-2x.png'
import shadow from 'leaflet/dist/images/marker-shadow.png'

const props = defineProps({ places: Array, selectedId: String })
const emit = defineEmits(['select'])
const el = ref(null)
const START = [3.2514, 101.7348] // CHANGE: where the map opens (IIUM Gombak). 16 below is the zoom level.
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
let map, layer
L.Icon.Default.mergeOptions({ iconUrl: icon, iconRetinaUrl: icon2x, shadowUrl: shadow }) // fixes pin images under Vite

// PINS: redrawn whenever search/filter results change. title/alt = text name for screen readers.
function draw() {
  layer.clearLayers()
  props.places.forEach(p =>
    L.marker([p.coordinates.latitude, p.coordinates.longitude], { title: p.name, alt: p.name })
      .bindTooltip(p.name).on('click', () => emit('select', p.id)).addTo(layer))
  if (props.places.length) map.fitBounds(layer.getBounds().pad(0.3), { maxZoom: 17, animate: !reduce })
}

onMounted(() => {
  map = L.map(el.value).setView(START, 16)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map)
  layer = L.featureGroup().addTo(map)
  draw()
  // PIN-POINT HELPER (npm run dev only): click anywhere to see "latitude, longitude" for a new pin.
  if (import.meta.env.DEV) map.on('click', e =>
    L.popup().setLatLng(e.latlng).setContent(`${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`).openOn(map))
})
watch(() => props.places, () => map && draw())
watch(() => props.selectedId, id => { // list selection moves the map
  const p = props.places.find(x => x.id === id)
  if (p) map.setView([p.coordinates.latitude, p.coordinates.longitude], 18, { animate: !reduce })
})
onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div>
    <div ref="el" role="region" aria-label="Map of buildings. The building list has the same information." class="z-0 h-full min-h-64 rounded-lg border-2 border-ink"></div>
  </div>
</template>
