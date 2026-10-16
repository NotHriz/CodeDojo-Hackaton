// SUPABASE CLIENT: handles sign-in sessions. Uses only the PUBLIC key.
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
export const supabaseConfigured = Boolean(url && key) // false -> auth screens show a clear error

// "Remember me": unticked = session lives in sessionStorage (ends when the tab closes).
const store = () => (localStorage.getItem('remember') === '0' ? sessionStorage : localStorage)

export const supabase = createClient(url || 'http://localhost', key || 'missing', {
  auth: { storage: { getItem: k => store().getItem(k), setItem: (k, v) => store().setItem(k, v), removeItem: k => store().removeItem(k) } }
})
