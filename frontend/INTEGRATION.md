# Findr frontend: setup and backend connection

## 1. Fill frontend/.env (this is why log in and the backend did not connect)
```
VITE_API_BASE_URL=                       # leave empty in development
VITE_SUPABASE_URL=https://<project-ref>.supabase.co     # a web address, not a folder path
VITE_SUPABASE_PUBLISHABLE_KEY=<publishable or anon key>  # Supabase > Project Settings > API
```
## 2. Start both sides
```bash
# Terminal 1 (backend, fictional buildings for testing)
cd backend && DEMO_DATA_ENABLED=true uvicorn app.main:app --reload --port 8000
# Terminal 2
cd frontend && npm install && npm run dev        # http://localhost:5173
```
`/api/...` calls are forwarded to port 8000 by `vite.config.js`. Test: http://localhost:8000/api/places must return buildings.
Response shapes were checked against `backend/app/schemas.py` and `services/community.py` (places, details, reports, votes).

## Connected browsing increment

With backend `DATABASE_URL` configured and migrations applied separately, the existing API calls now read stored buildings and evidence. No frontend database credential is needed. Details and active warnings load independently of barrier reports; report errors have their own retry button and never imply that a building has no reports. Unknown facilities still do not match required features.

The production build passes. `tests/browsing-smoke.cjs` accepts a Playwright module path, Chromium/Edge executable, local site URL and screenshot output path. It expects a disposable SQL fixture named `Fictional integration building` with the warning `Fictional preserved report`, while community persistence is disconnected. It checks details/warnings despite reports 503, retry, refresh persistence and unknown-facility filtering. Playwright is an external verification tool, not an added application dependency.

Transactional community persistence and policy binding are merged (PRs #28 and #29). Chat, clearing and history UI are now implemented on feat/frontend-community-flows, prepared for PR review and not deployed. Real campus observations and shared deployment remain pending. Additional facilities, username login, tickets and permanent-observation voting are deferred proposals rather than requirements for this integration slice.

## Changes to the repo
| Action | Path |
| --- | --- |
| Delete | `frontend/src/**/.gitkeep` (already removed in this version) |
| Replace | `frontend/.env.example` (same names, comments added, `VITE_API_BASE_URL` empty in dev) |
| Add | everything else in `frontend/` plus `package-lock.json` after `npm install` |
| Edit | nothing outside `frontend/`. Backend, `contracts/` and `supabase/` are untouched |

## 4. Map
Leaflet + OpenStreetMap (`src/components/MapView.vue`). No API key and no map ID exist or are needed.
Click the map in dev mode to read coordinates for new pins. Pins appear when the backend returns buildings.

## 5. Still missing in the backend
Facility info and its votes, photo upload, support tickets (router + SQL are in the earlier notes), the 4 extra facilities
(lift, braille, flashing_fire_alarm, tactile_paving), and unique usernames. Those buttons show a real error until added.

## 6. Where to edit
Logo `src/config.js` + `public/Findr.png` | colours and stripes `src/style.css` | stripe length and layout `src/components/HeroShell.vue`
| white curve `src/App.vue` | nav and button order `src/App.vue` | text `src/views/*`.

## 7. Git
```bash
git switch main && git pull --ff-only origin main
git switch -c feat/frontend-polish
git status                      # frontend/.env must NOT be listed
git add frontend && git commit -m "feat(frontend): logo, full-screen layout, username login, no sign-up code"
git push -u origin feat/frontend-polish
```
Open a small Pull Request into `main` and tag the backend owner for the table above. If the push is rejected: `git pull --rebase origin main`, fix conflicts, `git add <file>`, `git rebase --continue`, push again.

## Chat, clearing and history integration (17 October 2026)

PR #30 review regression: submitting a separate barrier after a failed clearing attempt must preserve the existing card's description, observation timestamp, open history and complete retry identity. The browser smoke test reproduces the failure with the old full reload and passes after switching successful building-level submissions/votes to `refreshCommunity()`. It also checks that the additional warning reaches the list and that resolving one barrier retains the other warning.

The current full-stack task connects POST /api/chat, clearing submission/vote endpoints and GET report history through the existing API client. No new backend contracts or dependencies. Google Maps continues to render only matching `places`, not all cited `sources`; editable interpreted filters include category and the three implemented facilities. Source records retain unknowns, warning labels and available check dates. AI errors retain the question and do not replace it with a canned answer.

Clearing submission uses the signed-in session and a retry UUID with a stable observation timestamp/body. The form retains failed input; votes show explicit 403/409/429/503 errors. Successful contributions refresh report counts/status, source building warnings and map/list warning summaries without resetting other drafts or moving focus. History preserves API order and uses offset pagination. Public history and ordinary browsing remain available signed out; writes remain enforced by backend identity checks.

Build and four helper tests pass. Browser checks use only intercepted test fixtures and no real provider/DB access. To reproduce with external Playwright and Edge installed, start a separate Vite process with test-only environment values (do not change real local files):

```powershell
$env:VITE_SUPABASE_URL = 'http://127.0.0.1:54321'
$env:VITE_SUPABASE_PUBLISHABLE_KEY = 'test-public-key'
$env:VITE_GOOGLE_MAPS_API_KEY = ''
$env:VITE_GOOGLE_MAPS_MAP_ID = ''
$env:VITE_API_BASE_URL = ''
npm run dev --prefix frontend -- --host 127.0.0.1 --port 5176 --strictPort
```

In another shell, invoke the smoke script with your external Playwright module path, Edge executable, site origin and output screenshot:

```powershell
node frontend/tests/community-flows-smoke.cjs C:/path/to/playwright 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' http://127.0.0.1:5176 C:/path/to/output.png
```

The test intercepts all API/Auth replies, including outages, and cannot validate provider prose quality, real login configuration, database deployment or distributed concurrency. The earlier browsing smoke script uses a different fixture/error scenario and does not exercise these new flows. Rehearse real migrated Supabase, backend policy activation and provider setup separately before the pitch.
