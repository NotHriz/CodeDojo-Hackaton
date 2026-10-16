# Backend

Owner: the user (backend). Teammate 3 owns `app/models.py` and `app/database.py`; agree their interfaces before backend services depend on them. See [file ownership and handoffs](../COLLABORATION.md).

The FastAPI foundation, building list/details API, and Supabase asymmetric-token verification are implemented. Database connections, contribution restrictions, voting, and AI are not implemented yet. `app/models.py` and `app/database.py` remain database-owned placeholders. Building endpoints return an explicit 503 until the database teammate supplies the repository adapter; tests alone use test records.

## Local development

Use Python 3.12. From the repository root in PowerShell:

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
Set-Location backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Copy the environment example only when creating a new local environment; do not overwrite an existing `.env`. No external credentials are required for liveness. Settings load from `backend/.env` regardless of the working directory; actual environment variables take precedence. Never commit the local file.

- Liveness: `GET http://localhost:8000/api/health`
- Interactive API docs: `http://localhost:8000/api/docs`
- OpenAPI: `http://localhost:8000/api/openapi.json`

Liveness returns `{"status":"ok","service":"akses-campus-api"}`. This proves only that the API process responds; it does not check Supabase or DeepSeek readiness. Unimplemented endpoints return 404, not mock data. Building endpoints are documented in `/api/docs` and [the handoff contract](../contracts/places.md).

## Tests

From the repository root:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
.venv/Scripts/python.exe -m pytest
```

Tests cover liveness, configuration, HTTP errors, sanitization, CORS, building filters, campus isolation, pagination, evidence/warnings, genuine misses, disconnected/broken repositories, and real signed-token verification. All 52 tests pass. `requirements.in` records direct runtime dependency ranges; `requirements.txt` pins the resolved runtime environment and `requirements-dev.txt` pins the test environment. Regenerate and verify pins deliberately when upgrading.

Authentication handoff: [contracts/auth.md](../contracts/auth.md). Set `SUPABASE_URL`, configure ES256/RS256 signing keys in Supabase, and send bearer tokens to `/api/auth/me`. Only the verified user UUID is returned. Legacy HS256 tokens are unsupported; immediate token revocation and live contribution restrictions are not implemented.

## API foundation contract

Application errors use `{"error":{"code":"...","message":"..."}}`. Current codes are `not_found` (404), `method_not_allowed` (405), `validation_error` (422), `service_unavailable` (503), `internal_error` (500), and `request_failed` for other HTTP errors. Validation failures omit submitted values; unexpected errors omit internal exception details. CORS preflight rejection is middleware-owned and can be plain text; clients must handle non-JSON infrastructure responses too.

`ALLOWED_ORIGINS` is a comma-separated list of exact HTTP(S) origins without paths, trailing slashes, credentials, or wildcards. Empty disables cross-origin browser access. Bearer-token headers are permitted; cookie credentials are disabled. CORS is a browser policy, not authentication.

## Render configuration

When creating the backend service, set root directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and health path `/api/health`. Use Python 3.12, `APP_ENV=production`, and `ALLOWED_ORIGINS` matching the Netlify site origin. No deployment has been performed.

## Ownership and next slice

| Path | Responsibility |
| --- | --- |
| `app/main.py` | Application factory, error handling, middleware, and router registration |
| `app/config.py` | Environment settings and explicit origin validation |
| `app/models.py` | Persistence models agreed with the database teammate |
| `app/schemas.py` | Foundation response schemas; domain/AI contracts not yet implemented |
| `app/database.py` | Connection/session management; no import-time external connections |
| `app/routers/` | Places, reports, votes, clearance observations, identity, and chat endpoints |
| `app/services/` | Query logic, community aggregation, trust rules, and DeepSeek tool orchestration |

Keep credentials on Render/the backend. Supabase Auth tokens must be verified before accepting reports or votes. The backend owns derived report status and private reliability; clients and AI cannot set them directly.

Agree trust thresholds and shared schemas before implementing the services. Register no fake success responses for unimplemented features. Deployment target: Render; persistent data and photos belong in Supabase.

Implemented: `GET /api/places` with name/category/campus and required-facility filters, stable sorting, and pagination; `GET /api/places/{place_id}` with entrance/observation/evidence fields and active warnings. Required facilities match only `yes`; warnings never remove matches; no matches never relax filters.

Next handoff: teammate 3 provides a persistence adapter implementing `PlaceRepository` and teammate 1 reviews [response examples](../contracts/places.md). The backend owner then wires that adapter into `create_app`. No database-owned files or frontend files were changed for this feature. Schema review, actual data access, and end-to-end external integration remain pending.

See [project README](../README.md) and [onboarding](../onboarding.md) for scope and acceptance criteria.
