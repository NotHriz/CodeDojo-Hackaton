// AUTH LOGIC: wraps Supabase so views never touch it directly. Errors are thrown as plain Error messages.
import { reactive } from 'vue'
import { supabase, supabaseConfigured } from './supabase.js'
import { resolveLoginEmail } from './api.js'

export const auth = reactive({ user: null }) // auth.user is null when signed out

// Resolves once the saved session has been read (router waits for this).
export const authReady = supabaseConfigured
  ? supabase.auth.getSession().then(({ data }) => { auth.user = data.session?.user ?? null })
  : Promise.resolve()
supabase.auth.onAuthStateChange((_e, s) => { auth.user = s?.user ?? null })

const need = () => { if (!supabaseConfigured) throw new Error('Sign-in is not configured. Set the Supabase keys in frontend/.env.') }
const check = ({ error }) => { if (error) throw new Error(error.message) }

// LOG IN: username is converted to an email by the backend (PROPOSED endpoint); an email is used directly.
export async function logIn(identifier, password, remember) {
  need(); localStorage.setItem('remember', remember ? '1' : '0')
  const email = identifier.includes('@') ? identifier : await resolveLoginEmail(identifier)
  check(await supabase.auth.signInWithPassword({ email, password }))
}

// SIGN UP step 1: email the 6-digit code. Needs Supabase email template to contain {{ .Token }}.
export async function sendCode(email) { need(); check(await supabase.auth.signInWithOtp({ email, options: { shouldCreateUser: true } })) }

// SIGN UP step 2: verify the code (this signs the user in), then save password + username.
export async function signUp({ username, password, email, code }) {
  need(); check(await supabase.auth.verifyOtp({ email, token: code, type: 'email' }))
  check(await supabase.auth.updateUser({ password, data: { username } }))
}

// FORGOT: Supabase emails a link that opens /reset.
export async function forgot(email) { need(); check(await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/reset` })) }
export async function resetPassword(password) { need(); check(await supabase.auth.updateUser({ password })) }

// PROFILE EDIT: proves the old password first by signing in again, then applies the change.
export async function updateProfile({ current, username, password }) {
  need(); check(await supabase.auth.signInWithPassword({ email: auth.user.email, password: current }))
  const patch = {}
  if (password) patch.password = password
  if (username) patch.data = { username }
  check(await supabase.auth.updateUser(patch))
}

export const logOut = () => supabase.auth.signOut()
