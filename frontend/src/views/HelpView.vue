<script setup>
// HELP CENTER: sends a support ticket to the backend (POST /api/tickets, PROPOSED). Edit CATEGORIES to change the dropdown.
import { reactive, ref } from 'vue'
import { createTicket } from '../services/api.js'

const CATEGORIES = ['Wrong accessibility information', 'Problem with my account', 'Something is not working', 'Other']
const form = reactive({ category: CATEGORIES[0], subject: '', message: '' })
const error = ref('')
const sent = ref(false)
const busy = ref(false)

async function send() {
  error.value = ''; busy.value = true
  try { await createTicket(form); sent.value = true; form.subject = ''; form.message = '' }
  catch (e) { error.value = e.message } // the typed text is kept so nothing is lost on failure
  finally { busy.value = false }
}
</script>

<template>
  <section class="mx-auto max-w-md space-y-4">
    <h1 class="text-2xl font-bold">Help center</h1>
    <p>Tell us what went wrong. A team member will read your ticket.</p>
    <p v-if="sent" role="status" class="card font-bold text-yes">✔ Ticket sent. Thank you.</p>
    <form class="card space-y-4" @submit.prevent="send">
      <div><label for="cat" class="font-bold">Topic</label>
        <select id="cat" v-model="form.category" class="input"><option v-for="c in CATEGORIES" :key="c">{{ c }}</option></select></div>
      <div><label for="sub" class="font-bold">Subject</label><input id="sub" v-model="form.subject" required maxlength="120" class="input" /></div>
      <div><label for="msg" class="font-bold">Message</label><textarea id="msg" v-model="form.message" required maxlength="2000" rows="5" class="input"></textarea></div>
      <p v-if="error" role="alert" class="font-bold text-no">✖ {{ error }}</p>
      <button type="submit" class="btn w-full" :disabled="busy">Send ticket</button>
    </form>
  </section>
</template>
