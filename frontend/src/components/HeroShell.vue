<script setup>
// HERO LAYOUT used by Home, About and Log in: text on the blue card (left), content on a white curved area (right),
// with decorative YELLOW STRIPES. Slots: #left and #right. On phones the right side becomes a white card.
</script>

<template>
  <div>
    <!-- YELLOW STRIPES (decoration only). Change size with h-/w- classes; colour is in style.css (.stripes). -->
    <div class="stripes pointer-events-none absolute bottom-0 left-0 h-12 w-64" aria-hidden="true"></div>
    <div class="stripes pointer-events-none absolute bottom-0 right-0 h-4 w-40" aria-hidden="true"></div>

    <div class="relative z-10 grid lg:min-h-[34rem] lg:grid-cols-2">
      <!-- LEFT: blue area. pb-20 keeps text clear of the stripes. -->
      <div class="px-6 pb-20 pt-4 sm:px-10 lg:py-12 lg:pb-24"><slot name="left" /></div>

      <!-- RIGHT: white curved area. The SVG draws the curve (edit the path "d" to reshape it). -->
      <div class="relative lg:flex lg:items-center lg:justify-center lg:px-8">
        <svg class="absolute inset-0 hidden h-full w-full lg:block" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path d="M30 0H100V100H12L2 40C0 22 12 10 30 0Z" fill="#fff" />
        </svg>
        <div class="relative z-10 mx-4 mb-16 rounded-2xl bg-white p-6 text-ink lg:mx-0 lg:mb-0 lg:ml-20 lg:w-full lg:max-w-md lg:bg-transparent lg:p-0">
          <slot name="right" />
        </div>
      </div>
    </div>
  </div>
</template>
