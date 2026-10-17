<script setup>
// LOGO SQUARE: white rounded square holding the logo (Findr.png has a white background, so the square is white).
// Picture comes from LOGO_SRC in src/config.js. size = Tailwind height/width classes.
import { LOGO_SRC } from '../config.js'
defineProps({ size: { type: String, default: 'h-56 w-56' } })
</script>

<template>
  <div :class="['mx-auto grid place-items-center overflow-hidden rounded-3xl bg-white shadow-lg ring-4 ring-brand/20', size]">
    <img v-if="LOGO_SRC" :src="LOGO_SRC" alt="Findr logo" class="h-full w-full object-contain" />
  </div>
</template>
