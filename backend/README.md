# Backend

Owner: the user (backend). Teammate 3 owns `app/models.py` and `app/database.py`; agree their interfaces before backend services depend on them. See [file ownership and handoffs](../COLLABORATION.md).

The FastAPI foundation is runnable: process liveness, environment settings, explicit CORS origins, API documentation, and sanitized JSON errors. Building search, database connections, authentication, voting, and AI are not implemented yet. `app/models.py` and `app/database.py` remain database-owned placeholders.

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

Liveness returns `{"status":"ok","service":"akses-campus-api"}`. This proves only that the API process responds; it does not check Supabase or DeepSeek readiness. Unimplemented endpoints return 404, not mock data.

## Tests

From the repository root:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
.venv/Scripts/python.exe -m pytest
```

Tests cover liveness without credentials, unavailable endpoints, HTTP/validation errors, sanitization, CORS allowlisting, and settings precedence. `requirements.in` records direct runtime dependency ranges; `requirements.txt` pins the resolved runtime environment and `requirements-dev.txt` pins the test environment. Regenerate and verify pins deliberately when upgrading.

## API foundation contract

Application errors use `{"error":{"code":"...","message":"..."}}`. Current codes are `not_found` (404), `method_not_allowed` (405), `validation_error` (422), `internal_error` (500), and `request_failed` for other HTTP errors. Validation failures omit submitted values; unexpected errors omit internal exception details. CORS preflight rejection is middleware-owned and can be plain text; clients must handle non-JSON infrastructure responses too.

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

Next feature: `GET /api/places` and `GET /api/places/{id}`. Agree building/entrance field shapes and the database-session interface with teammate 3, and response examples with teammate 1, before implementing that shared slice. This foundation does not change their files or prescribe their schema.

See [project README](../README.md) and [onboarding](../onboarding.md) for scope and acceptance criteria.
