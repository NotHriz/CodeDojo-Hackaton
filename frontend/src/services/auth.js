// AUTH LOGIC: wraps Supabase so views never touch it directly. Errors are thrown as plain Error messages.
import { reactive } from 'vue'
import { supabase, supabaseConfigured } from './supabase.js'

export const auth = reactive({ user: null }) // auth.user is null when signed out

// DEMO USER (no database needed): username ali / password 12345678. Works only while running `npm run dev`,
// or in a build made with VITE_DEMO_LOGIN=true. It is NOT a real account: the backend gives it no token, so adding
// info or voting shows a real "sign in" error. Delete this block to remove the demo login completely.
const DEMO = { username: 'ali', email: 'ali@findr.test', password: '12345678' }
const demoEnabled = import.meta.env.DEV || import.meta.env.VITE_DEMO_LOGIN === 'true'
const demoUser = () => ({ id: 'demo-ali', email: DEMO.email, user_metadata: { username: DEMO.username }, is_demo: true })
const demoStored = () => sessionStorage.getItem('findr-demo') || localStorage.getItem('findr-demo')
let demoActive = demoEnabled && Boolean(demoStored())
if (demoActive) auth.user = demoUser()

// Resolves once the saved session has been read (router waits for this).
export const authReady = demoActive ? Promise.resolve() : supabaseConfigured
  ? supabase.auth.getSession().then(({ data }) => { auth.user = data.session?.user ?? null })
  : Promise.resolve()
supabase.auth.onAuthStateChange((_e, s) => { if (!demoActive) auth.user = s?.user ?? null })

const need = () => { if (!supabaseConfigured) throw new Error('Sign-in is not configured. Set the Supabase keys in frontend/.env.') }
const check = ({ error }) => { if (error) throw new Error(error.message) }

// LOG IN: an email is used directly. A username is turned into its email by the Supabase function login_email
// (create it once with setup/supabase-username-login.sql). Wrong username and wrong password give the same message.
async function emailFor(identifier) {
  if (identifier.includes('@')) return identifier
  const { data, error } = await supabase.rpc('login_email', { p_username: identifier })
  if (error || !data) throw new Error('Username or password is incorrect.')
  return data
}
export async function logIn(identifier, password, remember) {
  const id = identifier.trim().toLowerCase()
  if (demoEnabled && (id === DEMO.username || id === DEMO.email) && password === DEMO.password) { // demo user, no database
    (remember ? localStorage : sessionStorage).setItem('findr-demo', '1')
    demoActive = true; auth.user = demoUser(); return
  }
  need(); localStorage.setItem('remember', remember ? '1' : '0')
  check(await supabase.auth.signInWithPassword({ email: await emailFor(identifier.trim()), password }))
}

// SIGN UP: creates the account with the username stored in its metadata.
// Returns true when Supabase wants the email confirmed first (Authentication > Providers > Email > "Confirm email").
export async function signUp({ username, email, password }) {
  need()
  const { data, error } = await supabase.auth.signUp({ email, password, options: { data: { username: username.trim() } } })
  if (error) throw new Error(error.message)
  return !data.session
}

// FORGOT: Supabase emails a link that opens /reset.
export async function forgot(email) { need(); check(await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/reset` })) }
export async function resetPassword(password) { need(); check(await supabase.auth.updateUser({ password })) }

// PROFILE EDIT: proves the old password first by signing in again, then applies the change.
export async function updateProfile({ current, username, password }) {
  if (auth.user.is_demo) throw new Error('The demo account cannot be edited. Use a real account.')
  need(); check(await supabase.auth.signInWithPassword({ email: auth.user.email, password: current }))
  const patch = {}
  if (password) patch.password = password
  if (username) patch.data = { username }
  check(await supabase.auth.updateUser(patch))
}

export async function logOut() {
  demoActive = false; sessionStorage.removeItem('findr-demo'); localStorage.removeItem('findr-demo'); auth.user = null
  if (supabaseConfigured) await supabase.auth.signOut()
}
