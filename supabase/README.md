# Supabase schema and configuration

Owner: teammate 3/database.

The migrations implement campuses, buildings, entrances, facility observations, and ordered photo/evidence references. They follow the IDs, field limits, coordinate ranges, and three `yes`/`no`/`unknown` facility values in [the building contract](../contracts/places.md). No records are seeded. Absent facility information defaults to `unknown`; observation aggregation still needs agreement before live use.

## Migration runner

Use the Supabase CLI migration runner for a future shared deployment (`supabase db push` after linking the intended project and reviewing pending migrations). Timestamped SQL files in `migrations/` are applied in filename order. Never replay them manually against an existing shared schema or rewrite an applied migration. This increment does not initialize/link a Supabase project or apply anything remotely.

Each migration must run transactionally. Local checks use PostgreSQL's `psql --single-transaction` with `ON_ERROR_STOP=1`. To apply just the foundation migration to an empty disposable database, the equivalent command is:

```powershell
psql -X --set ON_ERROR_STOP=1 --single-transaction --file supabase/migrations/20261016000100_building_foundation.sql
```

The migration expects the existing Supabase `anon`, `authenticated`, and `service_role` roles. The local test harness supplies minimal stand-ins in an isolated cluster. Do not run `tests/roles.sql` on Supabase.

## Access and verification

All six tables enable RLS with no browser policies and revoke table access from public/browser roles. Only the backend service role receives CRUD access; public browsing remains through FastAPI. No frontend credentials, private reliability, or community tables are introduced.

With PostgreSQL 18 installed locally, run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
# Optional: -PostgresBin 'C:\path\to\postgresql\bin' -Port 55440
```

The harness creates a unique temporary cluster, listens only on loopback with local trust authentication, applies all migrations, and runs both SQL suites. Checks cover defaults, constraints, foreign keys, backend access, browser denial, RLS, nullable observation metadata, timestamp offsets, ordered evidence, and protected parent deletion. It stops the server in `finally` and retains temporary files for diagnosis. It never reads application credentials or connects to the shared database. Tests use fictional records rolled back at completion. Local trust authentication is exclusively for this disposable test cluster.

## Evidence mapping for the backend adapter

`20261016000200_place_evidence.sql` adds:

- `entrances`: UUID identity, `building_id`, required description, optional latitude/longitude supplied as a pair. Map both nulls to API `coordinates: null`; never substitute the building centre.
- `facility_observations`: UUID identity, `building_id`, facility/value, nullable `observed_at`, source and notes, and a distinct server-generated `recorded_at`. Missing observation dates stay null, regardless of ingestion time.
- `entrance_photos`: `entrance_id`, zero-based nonnegative `position`, and URL. Read by position into `photo_urls`.
- `observation_evidence`: `observation_id`, position, and URL. Read by position into `evidence_urls`.

No child references means an empty API array. UUIDs/positions/ingestion timestamps are persistence fields, not additions to the public DTO. URL constraints reject non-HTTP(S), empty hosts, and whitespace; the adapter must still validate complete URLs using the existing `HttpUrl` DTOs and return only public or appropriately scoped references. No file upload or Storage bucket is created.

Foreign keys use `ON DELETE RESTRICT` to avoid silently erasing recorded evidence when deleting a parent. Any deliberate deletion must handle dependent references explicitly. No trigger updates building facility values, selects the latest observation, or changes report state: recording evidence alone does not establish a current facility or community consensus.

## Pending handoff

Community persistence, observation aggregation, Storage/Auth policies, and seed import remain incomplete. The facility columns are current values, not evidence or certification; no aggregation rule is selected here. `backend/app/models.py` and `backend/app/database.py` remain placeholders. Coordinate SQLModel/PostgreSQL dependency additions with the backend owner before implementing their models/session API, then agree the adapter location and wire it through `create_app(place_repository=...)`. Existing endpoints and demo behavior are unchanged. The alternate, unmerged remote `feat/database-foundation` migration also creates campuses and entrances; do not combine it unchanged with these migrations accepted through PR #11.

The database owner also owns `backend/app/models.py`, `backend/app/database.py`, and `seed/`. The backend owner owns API schemas and service logic; agree fields and session interfaces before either side implements them.

- Version shared schema changes instead of making undocumented dashboard edits.
- Apply shared migrations through the database owner; never rewrite already applied migrations.
- Keep reliability records private and align public access with the backend/API contract.
- Document Auth redirect URLs and Storage/database access rules without storing credentials.
- Coordinate schema, backend, and seed changes before shared deployment.

See [collaboration rules](../COLLABORATION.md#shared-database-rules) and [onboarding](../onboarding.md).
