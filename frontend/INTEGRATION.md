# Frontend integration notes

## Run it
```bash
# Terminal 1: backend with fictional demo buildings (see backend/README.md "local chatbot demo")
cd backend && DEMO_DATA_ENABLED=true uvicorn app.main:app --reload --port 8000
# Terminal 2: frontend
cd frontend && cp .env.example .env   # fill in the Supabase and Google Maps values
npm install && npm run dev            # http://localhost:5173
```
No mock data is built in. If the backend is down, the pages show an error and a "Try again" button.

## Connected browsing increment

With backend `DATABASE_URL` configured and migrations applied separately, the existing API calls now read stored buildings and evidence. No frontend database credential is needed. Details and active warnings load independently of barrier reports; report errors have their own retry button and never imply that a building has no reports. Unknown facilities still do not match required features.

The production build passes. `tests/browsing-smoke.cjs` accepts a Playwright module path, Chromium/Edge executable, local site URL and screenshot output path. It expects a disposable SQL fixture named `Fictional integration building` with the warning `Fictional preserved report`, while community persistence is disconnected. It checks details/warnings despite reports 503, retry, refresh persistence and unknown-facility filtering. Playwright is an external verification tool, not an added application dependency.

Community persistence, chat UI, clearance/history UI, real campus observations and shared deployment remain pending. Additional facilities, username login, tickets and permanent-observation voting are deferred proposals rather than requirements for this integration slice.

## Changes to the repo
| Action | Path |
| --- | --- |
| Delete | `frontend/src/**/.gitkeep` (already removed in this version) |
| Replace | `frontend/.env.example` (same names, comments added, `VITE_API_BASE_URL` empty in dev) |
| Add | everything else in `frontend/` plus `package-lock.json` after `npm install` |
| Edit | nothing outside `frontend/`. Backend, `contracts/` and `supabase/` are untouched |

## What the backend/database owners must add
Frontend calls these. Items marked **missing** return an error in the UI until they exist.

| Need | Status | Proposed |
| --- | --- | --- |
| `GET /api/places`, `/api/places/{id}`, `/api/reports`, report votes, `POST /api/reports` | exists | used as documented in `contracts/` |
| Facilities `lift`, `braille`, `flashing_fire_alarm`, `tactile_paving` | **missing** (only 3 facilities exist) | add to `schemas.py` facility names |
| Submit facility info | **missing** | `POST /api/places/{id}/observations` `{facility, value, notes, observed_at, evidence_urls}` + `Idempotency-Key` |
| Vote on facility info | **missing** | `POST /api/observations/{id}/votes` `{stance}`; observations need an `id` |
| Photo upload | **missing** | `POST /api/uploads` multipart `file` -> `{url}` (Supabase Storage, check type/size) |
| Username login | **missing** | `POST /api/auth/resolve-username` `{username}` -> `{email}` (rate-limit it, it can reveal emails) |
| Unique usernames | **missing** | enforce in the database, usernames are only stored in Supabase user metadata now |
| Support tickets | **missing** | `POST /api/tickets` `{category, subject, message}` (signed in) |
| Supabase email template | setting | include `{{ .Token }}` so the sign-up email carries the 6-digit code |

## Git (follows COLLABORATION.md)
```bash
git switch main
git pull --ff-only origin main
git switch -c feat/frontend-ui

# copy this frontend/ folder over the repo's frontend/ folder, then:
cd frontend && npm install && npm run build && cd ..

git status                      # only frontend/ should be listed
git add frontend
git commit -m "feat(frontend): add search, map, accessibility settings, auth, profile and help pages"
git push -u origin feat/frontend-ui
```
Open a small Pull Request into `main` and tag the backend owner for the table above. If the push is rejected: `git pull --rebase origin main`, fix conflicts, `git add <file>`, `git rebase --continue`, push again.
