# Supabase schema and configuration

Owner: teammate 3/database.

The first migration implements campuses and buildings only. It follows the IDs, field limits, coordinate ranges, and three `yes`/`no`/`unknown` facility values in [the building contract](../contracts/places.md). No records are seeded. Absent facility information defaults to `unknown`; these current values still need an evidence/observation persistence design before live use.

## Migration runner

Use the Supabase CLI migration runner for a future shared deployment (`supabase db push` after linking the intended project and reviewing pending migrations). Timestamped SQL files in `migrations/` are applied in filename order. Never replay them manually against an existing shared schema or rewrite an applied migration. This increment does not initialize/link a Supabase project or apply anything remotely.

Each migration must run transactionally. Local checks use PostgreSQL's `psql --single-transaction` with `ON_ERROR_STOP=1`. For an empty disposable database only, the equivalent command is:

```powershell
psql -X --set ON_ERROR_STOP=1 --single-transaction --file supabase/migrations/20261016000100_building_foundation.sql
```

The migration expects the existing Supabase `anon`, `authenticated`, and `service_role` roles. The local test harness supplies minimal stand-ins in an isolated cluster. Do not run `tests/roles.sql` on Supabase.

## Access and verification

Both tables enable RLS with no browser policies and revoke table access from public/browser roles. Only the backend service role receives CRUD access; public browsing remains through FastAPI. No frontend credentials, private reliability, or community tables are introduced.

With PostgreSQL 18 installed locally, run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
# Optional: -PostgresBin 'C:\path\to\postgresql\bin' -Port 55440
```

The harness creates a unique temporary cluster, listens only on loopback with local trust authentication, applies migrations, and checks defaults, constraints, foreign keys, backend access, browser denial, and RLS. It stops the server in `finally` and retains temporary files for diagnosis. It never reads application credentials or connects to the shared database. Tests use fictional records rolled back at completion. Local trust authentication is exclusively for this disposable test cluster.

## Pending handoff

Entrances, dated observations/evidence, community persistence, Storage/Auth policies, and seed import remain incomplete. The facility columns are current values, not evidence or certification; no aggregation rule is selected here. `backend/app/models.py` and `backend/app/database.py` remain placeholders. Coordinate SQLModel/PostgreSQL dependency additions with the backend owner before implementing their models/session API, then agree the adapter location and wire it through `create_app(place_repository=...)`. Existing endpoints and demo behavior are unchanged.

The database owner also owns `backend/app/models.py`, `backend/app/database.py`, and `seed/`. The backend owner owns API schemas and service logic; agree fields and session interfaces before either side implements them.

- Version shared schema changes instead of making undocumented dashboard edits.
- Apply shared migrations through the database owner; never rewrite already applied migrations.
- Keep reliability records private and align public access with the backend/API contract.
- Document Auth redirect URLs and Storage/database access rules without storing credentials.
- Coordinate schema, backend, and seed changes before shared deployment.

See [collaboration rules](../COLLABORATION.md#shared-database-rules) and [onboarding](../onboarding.md).
