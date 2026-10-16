# Supabase schema and configuration

Owner: teammate 3/database.

The migrations implement campuses, buildings, entrances, facility observations, barrier-report creation and vote storage, and ordered photo/evidence references. They follow [the building contract](../contracts/places.md) and [the community contract](../contracts/community.md). No records are seeded. Absent facility information defaults to `unknown`; observation aggregation and community transactions still need implementation before live use.

## Migration runner

Use the Supabase CLI migration runner for a future shared deployment (`supabase db push` after linking the intended project and reviewing pending migrations). Timestamped SQL files in `migrations/` are applied in filename order. Never replay them manually against an existing shared schema or rewrite an applied migration. This increment does not initialize/link a Supabase project or apply anything remotely.

Each migration must run transactionally. Local checks use PostgreSQL's `psql --single-transaction` with `ON_ERROR_STOP=1`. To apply just the foundation migration to an empty disposable database, the equivalent command is:

```powershell
psql -X --set ON_ERROR_STOP=1 --single-transaction --file supabase/migrations/20261016000100_building_foundation.sql
```

The migration expects the existing Supabase `anon`, `authenticated`, and `service_role` roles. The local test harness supplies minimal stand-ins in an isolated cluster. Do not run `tests/roles.sql` on Supabase.

## Access and verification

All nine tables enable RLS with no browser policies and revoke table access from public/browser roles. Only the backend service role receives CRUD access; public browsing remains through FastAPI. Report rows contain private author/retry metadata and votes contain private identities/weights; neither may be exposed directly. No frontend credentials or private contributor reliability records are introduced.

With PostgreSQL 18 installed locally, run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
# Optional: -PostgresBin 'C:\path\to\postgresql\bin' -Port 55440
```

The harness creates a unique temporary cluster, listens only on loopback with local trust authentication, applies all migrations, and runs all four SQL suites. Checks cover defaults, constraints, foreign keys, backend access, browser denial, RLS, nullable observation metadata, timestamp offsets, ordered evidence, protected parent deletion, scoped report submission uniqueness, future-time limits, the three-reference report evidence limit, self-vote rejection, vote replacement, and bounded policy snapshots. It stops the server in `finally` and retains temporary files for diagnosis. It never reads application credentials or connects to the shared database. Tests use fictional records rolled back at completion. Local trust authentication is exclusively for this disposable test cluster.

## Evidence mapping for the backend adapter

`20261016000200_place_evidence.sql` adds:

- `entrances`: UUID identity, `building_id`, required description, optional latitude/longitude supplied as a pair. Map both nulls to API `coordinates: null`; never substitute the building centre.
- `facility_observations`: UUID identity, `building_id`, facility/value, nullable `observed_at`, source and notes, and a distinct server-generated `recorded_at`. Missing observation dates stay null, regardless of ingestion time.
- `entrance_photos`: `entrance_id`, zero-based nonnegative `position`, and URL. Read by position into `photo_urls`.
- `observation_evidence`: `observation_id`, position, and URL. Read by position into `evidence_urls`.

No child references means an empty API array. UUIDs/positions/ingestion timestamps are persistence fields, not additions to the public DTO. URL constraints reject non-HTTP(S), empty hosts, and whitespace; the adapter must still validate complete URLs using the existing `HttpUrl` DTOs and return only public or appropriately scoped references. No file upload or Storage bucket is created.

Foreign keys use `ON DELETE RESTRICT` to avoid silently erasing recorded evidence when deleting a parent. Any deliberate deletion must handle dependent references explicitly. No trigger updates building facility values, selects the latest observation, or changes report state: recording evidence alone does not establish a current facility or community consensus.

## Barrier-report creation handoff

`20261016000300_barrier_reports.sql` adds `barrier_reports` and `barrier_report_evidence`. Report identity is a UUID; `building_id` maps to API `place_id`, and campus identity comes from the referenced building. Observation and submission timestamps are distinct and finite; the database allows observation time at most five minutes after submission. New rows default to `unverified`. All four backend status names are supported for future backend-derived transitions; no policy or transition trigger is activated here.

Private fields are `author_id`, `idempotency_key`, and `payload_digest`. Author identity must come from verified Supabase authentication, never request JSON. There is no user/profile table or Auth deletion cascade in this slice; identity verification and transactional restriction checks remain adapter responsibilities. The digest must be 64 lowercase hexadecimal characters representing a backend-computed SHA-256 digest of normalized user payload, excluding server submission time. This migration checks its format, not its correctness.

Uniqueness is `(author_id, building_id, idempotency_key)`: the operation is implicitly create-report and the target is the building. Different actors/targets may reuse a key. This is a concurrency-safe database uniqueness primitive, not a completed retry implementation. The adapter must atomically compare digests on conflict, return the original unchanged record for identical content, raise `IdempotencyConflict` for changed content, and insert report/evidence/history in one transaction after checking eligibility/campus. Audit-event persistence and these transactions remain pending, so do not wire the community API yet.

Read evidence by `position` into `evidence_urls`. Slots 0–2 permit at most three references per report. Full URL validation and public/scoped-reference checks still belong to the backend DTO/adapter. For future place warnings, map only unresolved report statuses; do not leak author identity, retry keys, or payload digests. The migration does not change current place responses.

## Report-vote storage handoff

`20261016000400_report_votes.sql` adds private `report_votes`, keyed by `(report_id, voter_id)`. `stance` uses `corroborate`/`dispute`. A composite foreign key binds `report_author_id` to the actual report author, and a check rejects that author as voter; a caller cannot evade self-vote protection by supplying a different author. The referenced report identity/author cannot change while votes refer to it. Existing migrations are unchanged.

Each row requires the accepted `weight`, opaque nonblank `policy_version`, and all four `policy_*` values copied from an explicitly reviewed backend `TrustPolicy`. Limits match the backend model: supporters 2–20, minimum weight greater than zero and at most 40, support ratio greater than 0.5 and at most 1, maximum vote weight 1–2. A vote's weight must be between 1 and its own policy maximum. These are validation bounds, not selected thresholds: no weight/policy defaults or active trust policy are added. Identities and weights must come from verified identity/private contributor state, not client metadata.

The adapter must lock the report, check current eligibility/campus, upsert one member's vote, refresh its entire policy/weight snapshot and `updated_at`, aggregate using the backend trust functions, and write status/audit history in the same transaction. `updated_at` defaults on insert only; the upsert must explicitly refresh it. Historical snapshots and policy changes require the pending audit-event store; this table records only the current accepted vote. No SQL trigger calculates consensus or changes report status. Policy version assignment and adapter wiring still require backend agreement; the illustrative versions in SQL tests are not deployed policies.

## Pending handoff

Clearing observations/votes, audit history, contributor restrictions, complete community transactions, observation aggregation, Storage/Auth policies, and seed import remain incomplete. The facility columns are current values, not evidence or certification; no aggregation rule is selected here. `backend/app/models.py` and `backend/app/database.py` remain placeholders. Coordinate SQLModel/PostgreSQL dependency additions with the backend owner before implementing their models/session API, then agree the adapter location and wire it through `create_app(place_repository=...)`. Existing endpoints and demo behavior are unchanged. The alternate, unmerged remote `feat/database-foundation` migration also creates campuses and entrances; do not combine it unchanged with these migrations accepted through PR #11.

The database owner also owns `backend/app/models.py`, `backend/app/database.py`, and `seed/`. The backend owner owns API schemas and service logic; agree fields and session interfaces before either side implements them.

- Version shared schema changes instead of making undocumented dashboard edits.
- Apply shared migrations through the database owner; never rewrite already applied migrations.
- Keep reliability records private and align public access with the backend/API contract.
- Document Auth redirect URLs and Storage/database access rules without storing credentials.
- Coordinate schema, backend, and seed changes before shared deployment.

See [collaboration rules](../COLLABORATION.md#shared-database-rules) and [onboarding](../onboarding.md).
