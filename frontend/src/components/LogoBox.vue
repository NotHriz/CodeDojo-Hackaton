<script setup>
// LOGO SQUARE: the rounded blue gradient square from the design. The picture comes from LOGO_SRC in src/config.js.
// Empty LOGO_SRC = an empty square. size = Tailwind height/width classes.
import { LOGO_SRC } from '../config.js'
defineProps({ size: { type: String, default: 'h-56 w-56' } })
</script>

<template>
  <div :class="['mx-auto grid place-items-center overflow-hidden rounded-3xl bg-gradient-to-b from-[#3b7fc4] to-[#6fb1e2]', size]">
    <img v-if="LOGO_SRC" :src="LOGO_SRC" alt="Findr logo" class="h-3/4 w-3/4 object-contain" />
  </div>
</template>
