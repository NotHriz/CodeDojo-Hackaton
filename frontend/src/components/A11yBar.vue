<script setup>
// ACCESSIBILITY PANEL: opened from the header on every page. Controls the shared settings in useA11y.js.
import { ref } from 'vue'
import { a11y, resetA11y } from '../composables/useA11y.js'
const open = ref(false)
</script>

<template>
  <div class="relative" @keydown.esc="open = false">
    <!-- Toggle button. aria-expanded tells screen readers whether the panel is open. -->
    <button type="button" class="btn-alt bg-white" :aria-expanded="open" aria-controls="a11y-panel" @click="open = !open">
      Accessibility settings
    </button>
    <div v-show="open" id="a11y-panel" role="group" aria-label="Accessibility settings"
      class="card absolute right-0 z-[1100] mt-2 w-80 max-w-[85vw] space-y-3 text-ink">
      <!-- TEXT SIZE slider: 80% to 200%. Change min/max/step to alter the range. -->
      <div>
        <label for="scale" class="font-bold">Text size: {{ a11y.scale }}%</label>
        <input id="scale" v-model.number="a11y.scale" type="range" min="80" max="200" step="10" class="h-8 w-full" />
      </div>
      <label class="flex min-h-11 items-center gap-3"><input v-model="a11y.gray" type="checkbox" class="size-6 accent-brand" /> Grey scale</label>
      <label class="flex min-h-11 items-center gap-3"><input v-model="a11y.cb" type="checkbox" class="size-6 accent-brand" /> Colour-blind safe colours (blue and orange)</label>
      <label class="flex min-h-11 items-center gap-3"><input v-model="a11y.sr" type="checkbox" class="size-6 accent-brand" /> Screen reader mode (hides the map, adds read aloud)</label>
      <button type="button" class="btn-alt" @click="resetA11y">Reset all</button>
    </div>
  </div>
</template>
