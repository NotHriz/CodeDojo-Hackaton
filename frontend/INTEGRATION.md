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

## 3. Example login user (no database needed)
Username `ali`, password `12345678` (or email `ali@findr.test`). It works in `npm run dev` and is not a real account:
browsing and Explore work, but adding info or voting need a real Supabase user. To show it in a built site set `VITE_DEMO_LOGIN=true`.
Real accounts: run `setup/supabase-username-login.sql` in Supabase, then use Sign up.

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
