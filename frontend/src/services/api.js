// BACKEND CLIENT: the ONLY file that calls FastAPI. Every call goes through request().
// Paths marked PROPOSED do not exist in the backend yet (see INTEGRATION.md). Until they do, they show a real error.
import { supabase } from './supabase.js'

const BASE = import.meta.env.VITE_API_BASE_URL ?? '' // '' = same origin (Vite proxy in dev)

export class ApiError extends Error {
  constructor(message, status, code) { super(message); this.status = status; this.code = code }
}

// Adds the Supabase token (backend verifies it), an optional Idempotency-Key, and turns errors into ApiError.
async function request(path, { method = 'GET', body, form, idem } = {}) {
  const { data } = await supabase.auth.getSession()
  const headers = {}
  if (data.session) headers.Authorization = `Bearer ${data.session.access_token}`
  if (idem) headers['Idempotency-Key'] = idem
  if (body) headers['Content-Type'] = 'application/json'
  let res
  try { res = await fetch(BASE + path, { method, headers, body: form ?? (body ? JSON.stringify(body) : undefined) }) }
  catch { throw new ApiError('Cannot reach the server. Check your connection and try again.', 0) }
  const json = await res.json().catch(() => null)
  if (!res.ok) { // understands our {error:{message}} shape AND FastAPI's default {detail}
    const d = json?.detail
    const msg = json?.error?.message
      ?? (res.status === 404 ? 'The server does not have this feature yet.' : null)
      ?? (typeof d === 'string' ? d : d?.[0]?.msg) ?? `Request failed (${res.status})`
    throw new ApiError(msg, res.status, json?.error?.code)
  }
  return json
}

// ---- Implemented in the backend ----
export const listPlaces = () => request('/api/places?limit=100')                     // GET building summaries
export const getPlace = id => request(`/api/places/${encodeURIComponent(id)}`)       // GET one building + observations
export const listReports = placeId => request(`/api/reports?place_id=${encodeURIComponent(placeId)}`)
export const submitReport = (body, idem) => request('/api/reports', { method: 'POST', body, idem }) // needs sign-in
export const sendChat = body => request('/api/chat', { method: 'POST', body })
export const submitClearance = (reportId, body, idem) => request(`/api/reports/${encodeURIComponent(reportId)}/clearance-observations`, { method: 'POST', body, idem })
export const voteClearance = (reportId, clearanceId, stance) => request(`/api/reports/${encodeURIComponent(reportId)}/clearance-observations/${encodeURIComponent(clearanceId)}/votes`, { method: 'POST', body: { stance } })
export const getReportHistory = (reportId, offset = 0) => request(`/api/reports/${encodeURIComponent(reportId)}/history?limit=20&offset=${offset}`)

// stance: 'corroborate' | 'dispute'. kind: 'reports' (exists) | 'observations' (PROPOSED)
export const castVote = (kind, id, stance) => request(`/api/${kind}/${id}/votes`, { method: 'POST', body: { stance } })

// ---- Facility observations ----
export const submitObservation = (placeId, body, idem) => request(`/api/places/${encodeURIComponent(placeId)}/observations`, { method: 'POST', body, idem })
export const uploadPhoto = async file => { const f = new FormData(); f.append('file', file); return request('/api/uploads', { method: 'POST', form: f }) } // returns { url }
export const createTicket = body => request('/api/tickets', { method: 'POST', body })                // { category, subject, message }
