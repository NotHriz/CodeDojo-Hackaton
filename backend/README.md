# Backend

Owner: the user (backend). Teammate 3 owns `app/models.py` and `app/database.py`; agree their interfaces before backend services depend on them. See [file ownership and handoffs](../COLLABORATION.md).

The FastAPI foundation, building list/details API, Supabase token verification, bounded DeepSeek chat, signed-in report/clearing submissions, vote routes, and configurable trust functions are implemented. Configuring `DATABASE_URL` now connects building browsing through SQLModel/Psycopg to the migrated `public.place_detail_records` view. Community persistence and policy activation remain pending; disconnected features return explicit 503s.

Apply reviewed migrations separately before starting the API and import checked campus data through the database seed workflow. Startup never creates tables or inserts fixtures. Use a backend-only PostgreSQL connection with the service-role table/view permissions, not a Supabase HTTP URL or API key. Sessions close after each repository operation; shutdown disposes the pool. A configured database failure returns a sanitized error and never falls back to fictional records. Shared deployment and real campus imports have not been performed.

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

GitHub Actions runs the backend suite on every pull request, pushes to `main`, and manual dispatch. The `Python 3.12 backend tests` job installs both pinned runtime/test manifests, checks dependency compatibility, runs pytest on Ubuntu, and uploads a `backend-test-results` JUnit artifact for seven days. No Supabase or DeepSeek secrets are supplied, and tests use generated keys and mocked providers. This does not replace real database/provider integration testing or human review.

From the repository root:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
.venv/Scripts/python.exe -m pytest
```

To generate the same report locally from `backend`, run `.venv/Scripts/python.exe -m pytest -q --junitxml=test-results.xml`. The report is ignored by Git. Workflow definition: [backend.yml](../.github/workflows/backend.yml).

All 148 tests pass across foundation, building discovery, real JWT signatures, read-only chatbot tools/citations/failures, signed-in contributions, idempotency contracts, weighted quorums, restrictions, and independent clearing observations. `requirements.in` records direct runtime dependency ranges; `requirements.txt` pins the resolved runtime environment and `requirements-dev.txt` pins the test environment. Regenerate and verify pins deliberately when upgrading. Starlette currently emits a test-only HTTPX deprecation warning; it does not fail the suite.

Authentication handoff: [contracts/auth.md](../contracts/auth.md). Set `SUPABASE_URL`, configure ES256/RS256 signing keys in Supabase, and send bearer tokens to `/api/auth/me`. Only the verified user UUID is returned. Legacy HS256 tokens are unsupported; immediate token revocation and live contribution restrictions are not implemented.

Chat handoff: [contracts/chat.md](../contracts/chat.md). `POST /api/chat` uses DeepSeek only after `AI_API_KEY` and a building repository are available. No paid requests were made. Output contains structured places/sources/filters; failures return explicit errors. The in-memory demo limiter resets with the process and is not a spending hard cap.

## Local chatbot demo without Supabase

To test real DeepSeek responses without a configured database, explicitly enable fictional building data in your ignored `backend/.env`:

```dotenv
APP_ENV=development
DEMO_DATA_ENABLED=true
AI_API_KEY=your-deepseek-key
AI_MODEL=deepseek-flash
```

Restart Uvicorn after editing `.env`. Open `/api/docs`, confirm its **LOCAL DEMO** description, and try `GET /api/places`. It should return three fictional buildings with `data_mode: "demo"` and `is_demo: true`. Coordinates are examples, dates remain unknown, and none of these records describe verified IIUM facilities.

Then use **POST /api/chat -> Try it out**:

```json
{
  "message": "Find a study building with a step-free entrance and accessible toilet",
  "history": [],
  "selected_place_id": null
}
```

Two fictional study buildings match; one has an unverified fictional ramp warning. Responses include a local-demo prefix, `data_mode: "demo"`, and labelled source cards. Try a detail question with `selected_place_id: "demo-study-annex"` or a study search requiring designated parking to test warnings and zero matches.

The model response is real and consumes your DeepSeek credit. Provider failures remain explicit errors, never canned accessibility answers. Automated tests use mocked providers and spend no credit.

The committed example defaults to `DEMO_DATA_ENABLED=false`. Production refuses demo mode, explicit real adapters take precedence, and a failing real adapter never switches to demo records. Demo buildings cannot be combined with a community persistence adapter, so this does not simulate reports/voting or write fictional records into a real database. Turn the flag off when connecting actual campus data.

Community handoff: [contracts/community.md](../contracts/community.md). Report/vote mutations require authenticated identity. New reports/clearing observations require an `Idempotency-Key` UUID header. No trust policy is active by default: supply an explicitly reviewed `TrustPolicy` after the real community adapter is ready. Adapter methods must provide database-enforced uniqueness, restrictions, atomic status/history changes, and idempotency; in-memory tests do not prove real transaction behavior.

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
| `app/schemas.py` | Public health/error and building DTOs; chat and community DTOs live in their service modules |
| `app/database.py` | Connection/session management; no import-time external connections |
| `app/routers/` | Places, reports, votes, clearance observations, identity, and chat endpoints |
| `app/services/` | Query logic, community aggregation, trust rules, and DeepSeek tool orchestration |

Keep credentials on Render/the backend. Supabase Auth tokens must be verified before accepting reports or votes. The backend owns derived report status and private reliability; clients and AI cannot set them directly.

Agree trust thresholds and shared schemas before implementing the services. Register no fake success responses for unimplemented features. Deployment target: Render; persistent data and photos belong in Supabase.

Implemented: `GET /api/places` with name/category/campus and required-facility filters, stable sorting, and pagination; `GET /api/places/{place_id}` with entrance/observation/evidence fields and active warnings. Required facilities match only `yes`; warnings never remove matches; no matches never relax filters.

Connected browsing now uses `PostgresPlaceRepository` when `DATABASE_URL` is set. The disposable PostgreSQL runner verifies service-role HTTP list/details, persistence across app recreation and explicit database failures. The Vue browser smoke check verifies SQL-backed details and warnings even when reports return 503. Next: real community persistence and reviewed policy, checked campus data and shared deployment. See [DATABASE_HANDOFF.md](../DATABASE_HANDOFF.md).

See [project README](../README.md) and [onboarding](../onboarding.md) for scope and acceptance criteria.
