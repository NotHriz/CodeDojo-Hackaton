# Findr frontend: integration notes

## Run
```bash
cd frontend && cp .env.example .env     # fill VITE_SUPABASE_* (Google keys are no longer used)
npm install && npm run dev              # http://localhost:5173
# backend with fictional buildings: DEMO_DATA_ENABLED=true uvicorn app.main:app --reload --port 8000
```

## Where to edit
| What | File |
| --- | --- |
| Site name, **logo path** (`LOGO_SRC`) | `src/config.js` (put the image in `frontend/public/`, e.g. `'/logo.png'`) |
| Colours (blue, navy, yellow stripes) | `src/style.css` |
| Blue/white curve + stripes layout | `src/components/HeroShell.vue` |
| Home / About text | `src/views/HomeView.vue`, `AboutView.vue` |
| Help questions and ticket topics | `src/views/HelpView.vue` |
| Which pages need login | `src/router.js` (`meta.auth`) |

## Pin-pointing the 7 areas on the map
Pins are drawn from each building's `coordinates` in the backend, so the 7 areas become pins when they exist in the data.
1. Run `npm run dev` and open Explore. In dev mode, **click the map** where an area is: a popup shows `latitude, longitude`.
2. Check the spot against Google Maps or openstreetmap.org (right-click -> copy coordinates).
3. Give the 7 names and coordinates (5 decimals is about 1 m) to the database teammate for `seed/`, with category and facilities.
   For local testing only, the backend's fictional list is `backend/app/services/demo_places.py`.
4. Reload: each building appears as a pin and in the list. Selecting either one selects the same building.
Change the opening view with `START` and the zoom in `src/components/MapView.vue`.

## Help tickets: why it failed and the fix
The frontend was calling `POST /api/tickets`, which the backend does not have, so every send had to fail. The frontend now shows
a clear message and reads FastAPI errors correctly, and the form limits match the schema below. To make it work, the backend owner adds:
```python
# backend/app/routers/tickets.py  (adapt names to your code, then app.include_router(tickets.router))
from typing import Protocol
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.routers.auth import CurrentUser

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

class TicketIn(BaseModel):
    model_config = {"extra": "forbid"}
    category: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=2000)

class TicketRepository(Protocol):          # the database teammate implements this
    def create_ticket(self, user_id: str, data: TicketIn) -> str: ...

@router.post("", status_code=201)
def create_ticket(body: TicketIn, user: CurrentUser, request: Request):
    repo = getattr(request.app.state, "ticket_repository", None)
    if repo is None:
        raise HTTPException(503, "Support tickets are not connected yet.")
    return {"id": repo.create_ticket(str(user.id), body)}
```
```sql
create table tickets (
  id uuid primary key default gen_random_uuid(), user_id uuid not null,
  category text not null, subject text not null, message text not null,
  status text not null default 'open', created_at timestamptz not null default now());
```
The other missing endpoints (facility info, observation votes, uploads, username lookup) are listed in `src/services/api.js` under PROPOSED.

## Git (follows COLLABORATION.md)
```bash
git switch main
git pull --ff-only origin main
git switch -c feat/frontend-redesign
# replace the repo's frontend/ folder with this one, then:
cd frontend && npm install && npm run build && cd ..
git status                 # only frontend/ should be listed
git add frontend
git commit -m "feat(frontend): Findr redesign, login-first access, Leaflet map, help center"
git push -u origin feat/frontend-redesign
```
If you already committed the previous version, the same steps work: the new branch just contains the changed files.
