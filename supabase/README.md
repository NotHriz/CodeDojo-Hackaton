# Supabase schema and configuration

Owner: teammate 3/database.

The migrations implement campuses, buildings, entrances, facility observations, barrier-report and clearing-observation creation/vote storage, ordered photo/evidence references, and report audit events. They follow [the building contract](../contracts/places.md) and [the community contract](../contracts/community.md). No records are seeded. Absent facility information defaults to `unknown`; observation aggregation and community transactions still need implementation before live use.

## Migration runner

Use the Supabase CLI migration runner for a future shared deployment (`supabase db push` after linking the intended project and reviewing pending migrations). Timestamped SQL files in `migrations/` are applied in filename order. Never replay them manually against an existing shared schema or rewrite an applied migration. This increment does not initialize/link a Supabase project or apply anything remotely.

Each migration must run transactionally. Local checks use PostgreSQL's `psql --single-transaction` with `ON_ERROR_STOP=1`. To apply just the foundation migration to an empty disposable database, the equivalent command is:

```powershell
psql -X --set ON_ERROR_STOP=1 --single-transaction --file supabase/migrations/20261016000100_building_foundation.sql
```

The migration expects the existing Supabase `anon`, `authenticated`, and `service_role` roles. The local test harness supplies minimal stand-ins in an isolated cluster. Do not run `tests/roles.sql` on Supabase.

## Access and verification

All fourteen tables enable RLS with no browser policies and revoke table access from public/browser roles. The backend service role receives CRUD on existing records, SELECT/INSERT on audit events, and SELECT/INSERT/UPDATE on contributor state; public browsing remains through FastAPI. Reports/clearing observations contain private author/retry metadata and votes/history contain private identities/weights; these rows must not be exposed directly. No frontend credentials or learned reputation scores are introduced; contributor eligibility and voting weights remain private.

With PostgreSQL 18 installed locally, run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
# Optional: -PostgresBin 'C:\path\to\postgresql\bin' -Port 55440
```

The harness creates a unique temporary cluster, listens only on loopback with local trust authentication, applies all migrations, and runs all eight SQL suites. Checks cover defaults, constraints, foreign keys, backend access, browser denial, RLS, nullable observation metadata, timestamp offsets, ordered evidence, protected parent deletion, scoped submission uniqueness, future-time limits, three-reference evidence limits, self-vote rejection, vote replacement, bounded policy snapshots, clearing chronology tied to the actual parent timestamp, and clearing-vote parent membership. It stops the server in `finally` and retains temporary files for diagnosis. It never reads application credentials or connects to the shared database. Tests use fictional records rolled back at completion. Local trust authentication is exclusively for this disposable test cluster.

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

The adapter must lock the report, check current eligibility/campus, upsert one member's vote, refresh its entire policy/weight snapshot and `updated_at`, aggregate using the backend trust functions, and write status/audit history in the same transaction. `updated_at` defaults on insert only; the upsert must explicitly refresh it. Historical snapshots and policy changes must be appended to the audit-event store in the same transaction; this table records only the current accepted vote. No SQL trigger calculates consensus or changes report status. Policy version assignment and adapter wiring still require backend agreement; the illustrative versions in SQL tests are not deployed policies.

## Clearing-observation creation handoff

`20261016000500_clearance_observations.sql` adds `clearance_observations` and ordered `clearance_evidence` (slots 0–2). Clearing observations have UUID IDs, required author/description/observation time, separate finite submission times, an `unverified` default, and private retry keys/digests following the report-creation rules. Uniqueness is `(author_id, report_id, idempotency_key)`; creating a clearance is a separate operation from creating a report, so keys can be reused across those operations.

`report_observed_at` is an internal copy of the barrier time. A composite foreign key binds it to the actual parent `(id, observed_at)` and prevents parent time changes while clearances refer to it. The child's observation cannot predate that timestamp or exceed its submission time by more than five minutes. This also prevents bypassing chronology using a false copied parent time. Equality with the parent timestamp is allowed by the contract's “cannot predate” rule; no stronger temporal rule is added here. The adapter must read the timestamp from the locked parent, never client input.

The future adapter must recheck verified identity, eligibility, campus and chronology in the create transaction; compare normalized digests on retry; and write the clearing observation/evidence/audit event together. Identity and retry metadata stay out of public responses. `ClearanceRecord.report_id` identifies the parent; map the existing response fields without adding `report_observed_at` or digest fields. Missing evidence remains an empty array. SQL checks enforce basic URL shape; backend `HttpUrl` and reference permissions still apply.

Creating a claim leaves the parent report unchanged, preserving its original evidence/observation time. Clearing-vote storage is described below; resolution still requires a corroborated clearing observation and the backend's explicit trust functions in an atomic transaction.

## Clearing-vote storage handoff

`20261016000600_clearance_votes.sql` adds private `clearance_votes`, keyed by `(clearance_id, voter_id)`. A composite foreign key binds the observation ID, parent report ID and clearing author together; this rejects votes placed under the wrong report or with a spoofed author. The referenced clearing observation cannot be reassigned to another report/author while votes refer to it. A check rejects self-voting by the clearing author. The original barrier reporter may vote on another member's clearing observation; there is no additional ban on the barrier author.

The required stance, weight, complete policy snapshot and `updated_at` follow the report-vote rules, with no active defaults. Identity, weight and policy values remain backend-owned and private. One member may vote independently on multiple clearing observations; replacing a vote must update only the selected observation's row and refresh its complete snapshot and timestamp.

The adapter must lock the parent report and relevant observation, recheck eligibility/campus and parent membership, upsert the vote, recalculate both observation and parent status using the backend functions, and append audit history in one transaction. This includes recalculating a previously resolved report if a clearing vote changes. The schema supplies integrity/storage only: no consensus trigger, automatic resolution, reputation update or policy activation is added. Audit storage is described below; transactional adapter wiring remains pending.

## Report-history storage handoff

`20261016000700_report_history.sql` adds `report_events` with the four contract actions, finite occurrence time, report status before/after, public supporter/dispute counts, and private actor/clearing/vote metadata. Vote actions require a complete bounded policy/weight snapshot; creation actions cannot carry one. Clearing events must reference an observation belonging to that report. Unique partial indexes prevent duplicate report/clearing creation events.

Map only `id`, `report_id`, `occurred_at`, `action`, `previous_status`, `new_status`, and the public counts into `ReportEventResponse`. Keep actor IDs, clearing state/counts, stance, weights, policy metadata and internal sequence private. Read oldest-first by `occurred_at, sequence`; the generated identity sequence breaks equal-time ties but is not a global commit order and may have gaps.

The service role can SELECT/INSERT events and use the identity sequence, but cannot UPDATE/DELETE/TRUNCATE history. Table owners can still administer it; this is application append-only access, not tamper-proof storage. No trigger automatically writes events or proves their counts/statuses match the aggregate. The adapter must lock targets and append history atomically with each mutation, preserving old snapshots on later changes and returning original records/events on identical retries. Event-only writes must not be treated as successful application mutations.

The seventh SQL suite checks all four action shapes, historical snapshots, equal-time ordering, duplicate creation events, wrong-parent references, invalid snapshots, application append-only access, privacy/RLS, and rollback of an event in a failing SQL subtransaction. This does not test the pending real adapter or simultaneous transactions.

## Contributor-state storage handoff

`20261017000100_contributor_state.sql` adds private `contributor_state` keyed by `user_id` (verified Supabase UUID). New rows default to eligible with neutral weight 1. Stored weights are bounded to [1, 2]; a configured policy may impose a lower cap through the existing backend `eligible_weight` function. Missing rows retain the existing backend neutral default and are not automatically seeded.

`can_contribute=false` requires a non-space `restriction_reason`. Restoring eligibility requires clearing that reason explicitly. Map only eligibility/weight into the internal `ContributorState`; never expose this table or its reasons/timestamps as a public profile. No public restriction-explanation interface is defined by this migration. API identity verification is still required; this is not an Auth user table or credential store.

The backend service role may SELECT/INSERT/UPDATE state, but cannot DELETE/TRUNCATE it. Explicitly restore eligibility instead of deleting restrictions into the missing-row default. State updates must refresh `updated_at`; no timestamp trigger or automatic expiry is installed. Restriction administration, change history and recovery rules remain pending. No automatic score learning, consensus-based punishment, or rewriting of previously accepted votes occurs.

Before enabling community writes, the adapter must recheck eligibility inside each mutation transaction under a coordinated lock, including races involving a previously missing contributor row. This schema is storage only; it does not authorize an operation or complete concurrent restriction enforcement. The eighth SQL suite checks neutral defaults, bounds, explicit disable/restore, denied application deletion and browser read/write denial.

## Pending handoff

Audit/contributor-state transaction wiring, restriction administration/history, complete community transactions, observation aggregation, Storage/Auth policies, and seed import remain incomplete. The facility columns are current values, not evidence or certification; no aggregation rule is selected here. `backend/app/models.py` and `backend/app/database.py` remain placeholders. Coordinate SQLModel/PostgreSQL dependency additions with the backend owner before implementing their models/session API, then agree the adapter location and wire it through `create_app(place_repository=...)`. Existing endpoints and demo behavior are unchanged. The alternate, unmerged remote `feat/database-foundation` migration also creates campuses and entrances; do not combine it unchanged with these migrations accepted through PR #11.

The database owner also owns `backend/app/models.py`, `backend/app/database.py`, and `seed/`. The backend owner owns API schemas and service logic; agree fields and session interfaces before either side implements them.

- Version shared schema changes instead of making undocumented dashboard edits.
- Apply shared migrations through the database owner; never rewrite already applied migrations.
- Keep reliability records private and align public access with the backend/API contract.
- Document Auth redirect URLs and Storage/database access rules without storing credentials.
- Coordinate schema, backend, and seed changes before shared deployment.

See [collaboration rules](../COLLABORATION.md#shared-database-rules) and [onboarding](../onboarding.md).
