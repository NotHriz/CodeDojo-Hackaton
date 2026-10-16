// ACCESSIBILITY SETTINGS: one shared object used by every page. Saved in the browser between visits.
import { reactive, watchEffect } from 'vue'

const KEY = 'a11y'
const DEFAULTS = { scale: 100, gray: false, cb: false, sr: false }
let saved = {}
try { saved = JSON.parse(localStorage.getItem(KEY) ?? '{}') } catch { /* ignore corrupt data */ }

export const a11y = reactive({ ...DEFAULTS, ...saved })
export const resetA11y = () => Object.assign(a11y, DEFAULTS)

// Applies the settings to the whole page (so every tab/route is affected).
watchEffect(() => {
  const root = document.documentElement
  root.style.fontSize = `${a11y.scale}%`           // text size: everything uses rem, so all text scales
  root.style.filter = a11y.gray ? 'grayscale(1)' : '' // grey scale for the whole page
  root.dataset.cb = a11y.cb ? 'on' : 'off'          // colour-blind palette (see style.css)
  root.dataset.sr = a11y.sr ? 'on' : 'off'          // screen-reader mode (map hidden, read-aloud shown)
  localStorage.setItem(KEY, JSON.stringify({ ...a11y }))
})
