<script setup>
// HERO LAYOUT used by Home, About and Log in: text on the blue (left), content on the white area (right), YELLOW STRIPES.
// Slots: #left and #right. The white curve itself is drawn in App.vue so it can also sit behind the header buttons.
// On phones the right side becomes a white card.
</script>

<template>
  <div class="relative flex-1">
    <!-- YELLOW STRIPES (decoration only). Length: w-full on phones, lg:w-[48%] on laptops, which stops before the white curve.
         Raise 48% to lengthen (above about 50% it touches the white). Thickness: h-12. Colour: .stripes in style.css. -->
    <div class="stripes pointer-events-none absolute bottom-0 left-0 z-0 h-12 w-full lg:w-[48%]" aria-hidden="true"></div>

    <div class="relative z-10 grid lg:min-h-[34rem] lg:grid-cols-2">
      <!-- LEFT: blue area. pb-20 keeps text clear of the stripes. -->
      <div class="px-6 pb-20 pt-4 sm:px-10 lg:py-12 lg:pb-24"><slot name="left" /></div>

      <!-- RIGHT: sits on the white area. lg:ml-24 keeps content clear of the curve (reduce it to move content left). -->
      <div class="lg:flex lg:items-center lg:justify-center lg:px-8">
        <div class="mx-4 mb-16 rounded-2xl bg-white p-6 text-ink lg:mx-0 lg:mb-0 lg:ml-24 lg:w-full lg:max-w-md lg:bg-transparent lg:p-0">
          <slot name="right" />
        </div>
      </div>
    </div>
  </div>
</template>
