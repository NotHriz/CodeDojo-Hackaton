<script setup>
// PROFILE: shows account info. Changing username or password requires the current password (checked by signing in again).
import { reactive, ref } from 'vue'
import { auth, updateProfile } from '../services/auth.js'

const form = reactive({ username: '', password: '', confirm: '', current: '' })
const error = ref('')
const done = ref('')
const busy = ref(false)

async function save() {
  error.value = ''; done.value = ''
  if (!form.username && !form.password) { error.value = 'Enter a new username or a new password.'; return }
  if (form.password !== form.confirm) { error.value = 'Passwords do not match.'; return }
  busy.value = true
  try { await updateProfile(form); done.value = 'Profile updated.'; Object.assign(form, { username: '', password: '', confirm: '', current: '' }) }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <section class="mx-auto max-w-md space-y-5">
    <h1 class="text-2xl font-bold">Your profile</h1>
    <!-- ACCOUNT INFO (read from the Supabase user) -->
    <dl class="card space-y-2">
      <div><dt class="font-bold">Username</dt><dd>{{ auth.user.user_metadata?.username ?? 'Not set' }}</dd></div>
      <div><dt class="font-bold">Email</dt><dd>{{ auth.user.email }}</dd></div>
    </dl>
    <!-- EDIT FORM: leave a field empty to keep it unchanged -->
    <form class="card space-y-4" @submit.prevent="save">
      <h2 class="text-xl font-bold">Change username or password</h2>
      <div><label for="u" class="font-bold">New username</label><input id="u" v-model="form.username" class="input" autocomplete="username" /></div>
      <div><label for="p" class="font-bold">New password</label><input id="p" v-model="form.password" type="password" minlength="8" class="input" autocomplete="new-password" /></div>
      <div><label for="c" class="font-bold">Confirm new password</label><input id="c" v-model="form.confirm" type="password" class="input" autocomplete="new-password" /></div>
      <div><label for="o" class="font-bold">Current password (required)</label><input id="o" v-model="form.current" type="password" required class="input" autocomplete="current-password" /></div>
      <p v-if="error" role="alert" class="font-bold text-no">✖ {{ error }}</p>
      <p v-if="done" role="status" class="font-bold text-yes">✔ {{ done }}</p>
      <button type="submit" class="btn w-full" :disabled="busy">Save changes</button>
    </form>
  </section>
</template>
