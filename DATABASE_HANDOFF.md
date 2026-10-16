# Database integration handoff

Owner: User 3 / database. Last updated: 17 October 2026 (Asia/Kuala_Lumpur).

This is the database owner's maintained status and integration checklist. Update it in every database task/PR that changes schema, models/sessions, adapters, seeds, policies, verification, or deployment readiness. Record what actually changed and ran; keep pending work separate from merged and deployed functionality. Detailed field mappings remain in [supabase/README.md](supabase/README.md); API contracts remain owned by the backend owner.

## Current status

| Deliverable | Implementation / merge status | Verification / deployment |
| --- | --- | --- |
| Fourteen tables, seven backend-only views, eleven migrations | Merged through PR #23 | All eleven SQL suites pass locally; shared history/schema unverified |
| Insert-only collection/import tooling | Merged PR #21 | Ten unit/CLI checks and disposable import/retry/conflict checks pass; no actual campus dataset found |
| Lazy SQLModel sessions and real building repository/API | PR #24 is MERGED (confirmed via GitHub, 17 October local date) | Persisted HTTP reads and app recreation pass locally; shared runtime not verified |
| Community read-view/private eligibility mappings and explicit transaction context | Prepared on `feat/database-delivery-readiness`; pending PR review | Service-role mappings, public DTO fields, commit, exception/constraint rollback and connection release pass |
| Read-only target audit and migration/import plan | Current task | Four audit privacy/unit checks and disposable audit checks pass, including rejected writes and detected grant drift |
| Runtime CommunityRepository | Backend-owner responsibility, not implemented | Atomic retry/concurrency/status/history integration remains pending |
| Shared Supabase deployment / real data import | No writes performed by this task | Configured connection times out; migration/data state unknown |

The latest task explicitly restricts writable scope to `supabase/**`, `seed/**`, `backend/app/models.py`, `backend/app/database.py` and this handoff. Earlier building-browsing cross-area authorization ended with that task. No frontend, backend services/routers, manifests, shared contracts or other root files were edited for this task. No new migration, trust threshold, reputation rule, field or Storage policy was introduced. The user authorized publishing this task as a PR; it is pending review and has not been merged. No shared database writes are authorized by the PR request.

The ignored CLI project link, Auth origin and database project identifiers match; demo data is off. The credential-safe target fingerprint is `efce16da98c9af3c`. The sandbox first denied outbound access; an authorized unrestricted read-only retry timed out, and the sanitized audit confirms `connection_timeout`. The read-only audit was rerun before PR publication after the user updated local configuration; the same target still timed out from this environment (exit 1). The four audit privacy/unit checks were rerun and passed. This proves neither successful login nor an empty/migrated schema. Shared version/history/schema, grants, policies, record counts and Storage configuration remain unverified. Credentials/local link files were not added to source control; `supabase/.gitignore` now excludes CLI caches and generated audit/import files.

See [the exact migration/import plan](supabase/DEPLOYMENT_PLAN.md). It lists the eleven accepted files in order and requires target/history reconciliation plus a reviewed dry run before shared-write approval. No shared-write approval has been requested because a concrete remote pending set cannot yet be verified. Do not reset the project or combine the alternate foundation schema.

## Migration inventory

Apply accepted migrations in filename order through the agreed Supabase migration workflow. Never rewrite an applied migration or replay the sequence against existing tables manually.

| Migration | Storage / integrity | Review status |
| --- | --- | --- |
| `20261016000100_building_foundation.sql` | Campuses/buildings, coordinates, three facility values defaulting to unknown | Merged, PR #11 |
| `20261016000200_place_evidence.sql` | Entrances, dated observations, ordered photo/evidence references | Merged, PR #12 |
| `20261016000300_barrier_reports.sql` | Reports, scoped retry keys/digests, ordered evidence (maximum three references) | Merged, PR #13 |
| `20261016000400_report_votes.sql` | Unique member/report votes, self-vote prevention, explicit bounded weight/policy snapshots | Merged, PR #14 |
| `20261016000500_clearance_observations.sql` | Clearing claims/evidence, scoped retry keys, chronology bound to actual parent time | Merged, PR #15 |
| `20261016000600_clearance_votes.sql` | Unique member/clearing votes, actual parent/author membership, private snapshots | Merged, PR #16 |
| `20261016000700_report_history.sql` | Application append-only audit events, public status/count and private vote snapshots | Merged, PR #18 |
| `20261017000100_contributor_state.sql` | Private current eligibility, neutral/bounded weight, explicit restriction reason | Merged, PR #19 |
| `20261017000200_community_read_views.sql` | Active warnings and separate report/clearing member counts | Merged, PR #20 |
| `20261017000300_place_detail_records.sql` | Complete public place-detail record projection | Merged, PR #22 |
| `20261017000400_community_records.sql` | Public report/clearing/history DTO projections with private query access | Merged, PR #23 |

All implemented tables enable RLS and revoke browser-role access, including inherited grants. The backend service role has CRUD on existing application records, only SELECT/INSERT on audit events, and SELECT/INSERT/UPDATE on contributor state. Grants do not replace authenticated API identity/eligibility checks. Private author IDs, retry keys/digests, voter identities, weights and policy metadata must never enter public DTOs. No Storage bucket, upload API, public database policy, or learned reputation system exists yet.

The alternate remote `feat/database-foundation` branch uses another places schema and also creates campuses/entrances. Do not combine that migration unchanged with this accepted sequence. Its shared-project application status has not been verified.

## Backend integration order

1. Implemented under the user-authorized scoped handoff: SQLModel/Psycopg dependencies and pinned manifests. User 3 owns models/session implementation; dependency manifests, service logic, composition wiring and API contracts require the backend owner's scoped handoff. Connections must not open at module import time.
2. Merged through PR #24: SQLModel models, lazy PostgreSQL engine, operation-scoped sessions and validated place DTOs. Database failures propagate as sanitized HTTP errors.
3. Implemented: the read-only [PlaceRepository](contracts/places.md) uses the persisted place-detail view. Map building identity to `place_id` where required, join campus identity, preserve unknown facilities and null observation dates, and order evidence by position. Agree how current facility summaries are maintained; do not invent a latest-observation rule. Join actual unresolved reports into active warnings and exclude resolved reports.
4. Implement transactional contributor eligibility checks plus audit writes before enabling community writes. Agree explicit trust thresholds and policy-version assignment with the backend owner: `TrustPolicy` currently has no version field, while vote/history storage requires a private version/snapshot. Stored versions in tests are illustrative, not activated settings.
5. Implement the [CommunityRepository](contracts/community.md) transaction requirements and verify real concurrency. Inject the real adapters and reviewed policy through `create_app(...)` only after their integration checks pass. Public response shapes remain backend-owned.

## Community transaction requirements

- Lock the relevant report/clearing observation and recheck verified actor identity, contributor restrictions, campus and target membership inside the mutation transaction. Self-vote constraints are storage protection, not complete authorization.
- For creates, compute a SHA-256 digest from normalized user payload excluding server submission time. Report uniqueness is `(author_id, building_id, idempotency_key)`; clearing uniqueness is `(author_id, report_id, idempotency_key)`. Identical retries must return the original record/time; changed content must raise `IdempotencyConflict`. The database checks digest format only; the adapter must implement comparison/retry behavior.
- Read a clearing claim's internal `report_observed_at` from its locked parent. Its composite foreign key binds the copied time to the actual report; the claim cannot predate it. Observation times must be finite, timezone-aware at the API boundary, and at most five minutes after submission.
- Upsert each vote by member/target and refresh its complete weight/policy snapshot and `updated_at`. Weights come from private contributor state, never user-editable metadata. Append the accepted snapshot to history in the same transaction; current vote rows alone do not preserve past snapshots.
- Use backend trust functions to recalculate clearing and parent statuses, including after a changed clearing vote. Preserve original report evidence/times. Commit votes/claims, derived statuses, and audit history atomically. A new clearing claim alone cannot resolve a report.
- The clearing author cannot vote on their own claim; the original barrier reporter may vote on another member's claim. The composite target reference rejects a vote under the wrong report.

## Audit storage handoff

`report_events` captures the four contract actions, report status before/after, public supporter/dispute counts, and occurrence time. Private actor, clearing status/counts, accepted stance/weight and full policy snapshot are stored alongside them. Map only existing `ReportEventResponse` fields; do not expose the remaining columns or internal identity sequence.

Creation events are unique per report/clearing observation. Clearing events reference an observation belonging to that report; vote events require complete bounded snapshots, while creation events carry no vote metadata. Sort oldest-first by `occurred_at, sequence` for deterministic equal-time ordering. Identity sequence gaps are normal; the sequence is not a global transaction commit order.

Application credentials cannot UPDATE, DELETE or TRUNCATE events; owners can still administer history, so this is not tamper-proof storage. No trigger creates events or verifies that their counts/statuses equal aggregate truth. The adapter must append events and update corresponding report/vote/clearing data atomically under locks, including exactly-once creation-event handling on retries. Stored history does not implement repository concurrency or authorization.

## Contributor-state handoff

`contributor_state` is private current state keyed by verified Supabase user UUID. New stored rows default to `can_contribute=true`, `vote_weight=1`, and no reason. Missing rows still map to `ContributorState | None` and the backend's existing neutral default. No profiles/accounts are created and no browser writes or user-metadata score inputs are permitted.

Map only `can_contribute` and `vote_weight` into the existing internal `ContributorState`. Stored weights are bounded to [1, 2]; the backend must still cap accepted snapshots to the explicitly reviewed policy maximum. A disabled row needs a non-space restriction reason; restoration must explicitly set eligibility true and clear that reason. The reason and update timestamp remain private, with no new public DTO fields. Future user-facing restriction explanations need a separate backend-owned interface review.

Application credentials may SELECT/INSERT/UPDATE state but cannot DELETE/TRUNCATE it; accidentally removing a blocked row must not reactivate missing-row neutrality. The adapter must explicitly refresh `updated_at`, verify identity, and recheck/lock contributor state inside report/vote/clearing transactions. Missing-row creation/restriction races also need a coordinated locking strategy before enabling writes; SQL schema tests do not prove that adapter behavior.

This slice stores current state only. It adds no restriction administration endpoint, restriction-change history, automatic reputation learning/penalties, expiry, or recovery policy. How trusted operators change state and record its history remains to be agreed. Existing report/clearing evidence and accepted vote snapshots are not rewritten when state changes.

## Community read-view handoff

The ninth migration adds `building_active_warnings`, `report_community_counts` and `clearance_community_counts`. Only the service role receives SELECT. All three views use invoker security, retaining underlying table permissions/RLS rather than borrowing the view owner's privileges. They require PostgreSQL 15+; validation used PostgreSQL 18. Verify the actual shared-project version before deployment.

The warning view exposes building/campus identity plus the existing warning fields for unverified, community-corroborated and disputed reports; resolved reports are excluded. Adapters must scope by requested building/campus and serialize the UUID report ID to the existing public string field. These queries do not drop a building that matches facility filters or overwrite its facility summaries.

Counts include zero-vote reports/clearing observations, count each unique voter row once regardless of weight, and keep report votes separate from clearing votes. A stance replacement or stored status change is reflected on the next query without a materialized refresh. No trust policy, weighted quorum, aggregate status or new API shape is computed. Status consistency still requires the pending mutation adapter to commit vote/status/history changes together.

View columns exclude author/voter IDs, weights, policy metadata, restriction state and retry secrets. This is backend query preparation, not direct browser access or completed API wiring. The ninth suite verifies approved columns, campus/warning scoping, zero/unweighted counts, separate targets, changed votes/statuses, service-role read-only grants, and browser denial even if SELECT on one view is accidentally granted without underlying table access.

## Seed preparation handoff

The merged `seed/import_places.py` validates collection JSON against backend field constraints and generates an explicit insert-only SQL transaction. The default CLI validates only; `--sql` prints a plan without connecting to a database. No new dependency, backend manifest change, SQLModel replacement, API shape, or schema migration is introduced.

See [seed/README.md](seed/README.md) for input format, stable identity requirements and commands. The self-contained batch lists campuses/buildings plus optional entrances/observations and ordered references. Unknown/private/demo fields, duplicate IDs/JSON keys, invalid references/values, non-timezone dates, nonfinite JSON and NUL are rejected. Unknown facilities and missing entrance coordinates/dates stay unknown/null; no actual campus observations are invented.

Generated imports accept identical records, insert missing records, and roll back the full batch on conflicting values for an existing identity. They do not UPDATE/DELETE existing rows, remove omitted references, or target community/private tables. Corrections and any real/shared execution need a separately reviewed task. Source authenticity and permission to publish evidence remain human collection responsibilities; this tool validates structure, not accessibility truth.

The combined disposable runner tests repeat imports, literal quotes/backslashes/dollar delimiters/Unicode, null/unknown defaults, retained community reports, and whole-batch rollback including evidence conflicts. Tests contain fictional fixtures only. Import preparation is not a runtime demo/outage fallback and does not connect the live repositories.

## Complete place-record handoff

The merged `place_detail_records` invoker view exposes only `id`, `campus_id` and `record`. Query by campus/building identity; validate `record` with the existing backend `PlaceDetail`. JSON includes facilities, entrances, observations, ordered evidence and unresolved warnings without private identities/weights, ingestion times, retry keys, or internal entrance/observation IDs. No field is added to the shared API contract.

Each child collection is independently aggregated to prevent join multiplication. Entrances sort by internal UUID; observations by ingestion time then UUID; each reference list by its explicit position; warnings by observed time descending then report UUID. These are deterministic display orderings, not a facility aggregation policy. Empty collections remain arrays; missing entrance coordinates, source/notes and observation dates remain null. Building summaries stay as recorded even if observations differ. Resolved warnings are excluded without dropping the building.

Persisted records project `is_demo=false`; fictional fixtures exist only inside disposable verification and are never a runtime demo adapter. The existing explicit development demo remains separate and unchanged. SQL stores reference URLs; backend DTO validation and public/scoped reference permissions still apply. Access is service-role SELECT only, with invoker permissions/RLS retained through underlying tables/views (PostgreSQL 15+).

The projection-only verification script remains test-only, but the real `PostgresPlaceRepository` and composition wiring are now merged in PR #24. `verify_runtime_places.py` verifies configured PostgreSQL -> repository -> HTTP reads under service-role permissions, including warnings, unknown values, pagination, application recreation and sanitized database failures. It uses only disposable fictional records and does not prove shared deployment.

## Complete community-record handoff

The merged eleventh migration adds `clearance_public_records`, `report_public_records` and `report_history_records`. The names describe public DTO field selection only: access remains backend-service SELECT with invoker security and no browser grants. No new table, policy threshold, runtime repository, or API field is introduced.

Validate report `record` using `ReportResponse`, nested clearing records using `ClearanceResponse`, and history `record` using `ReportEventResponse`. Report evidence is ordered by position; clearing observations by submission time then UUID. Report reads retain resolved rows and live unweighted member counts; history uses its captured status/count snapshot, not recomputed current counts. Missing references/clearing lists stay empty arrays. Private author/voter IDs, weights, retry metadata, policy snapshots and internal clearing chronology copies stay outside JSON.

Adapters must query reports by building and campus, sorting newest-first by `submitted_at DESC, id DESC`. Scope history by report/campus and order oldest-first by `occurred_at, sequence`; query metadata including sequence stays outside public DTOs. A report with no events has an empty timeline; separately check target existence/membership to distinguish that from a missing/out-of-campus report. Enforce pagination/count semantics and validate public/scoped reference URLs in the backend. Stored status/count consistency still depends on atomic mutation transactions.

SQL checks cover independent clearing/report counts, ordered evidence, empty/zero states, resolved reports, captured history counts, SELECT-only grants and invoker/browser denial. Disposable Python checks verify exact public/nested field sets and validate actual PostgreSQL records through the existing community DTOs. Their temporary fixture mutations roll back. This is not authenticated HTTP-route integration or a production CommunityRepository.

## Verification and limits

Current-task verification: all eleven PostgreSQL 18 SQL suites, ten seed unit/CLI tests, generated-import integration, place/community DTO projection checks and configured building HTTP checks passed. New owned mapping/session checks pass under service-role permissions, including commit across sessions, rollback after a Python exception and a real database constraint failure, private-field exclusion and connection release. The audit passes its four privacy/unit checks and disposable catalog/permission/DTO checks; a follow-up check confirms writes are rejected in its read-only transaction and accidental browser SELECT grants are detected. All local servers started for these checks were stopped.

The existing backend suite also passes: 148 tests, one existing Starlette HTTPX deprecation warning, and clean `pip check`. Frontend build/browser smoke were verified in the merged browsing task, not rerun for these database-only changes. One initial database run stalled while native PostgreSQL startup output was redirected; its isolated cluster was stopped and the direct rerun completed successfully. No SQL/schema/application test failure remains.

Local fixtures are explicitly fictional. These checks do not implement or prove backend mutation concurrency, real Supabase identity, shared restart persistence, paid AI behavior or intended-user accessibility truth. No shared migrations, data imports or Storage changes occurred.

Run from the repository root on Windows with PostgreSQL 18 installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
```

Optional runner arguments are `-PostgresBin 'C:\path\to\postgresql\bin'` and `-Port 55440`. Minimal role fixtures exist only for the disposable cluster; never run `supabase/tests/roles.sql` against Supabase. Temporary cluster files are retained for diagnosis.

Coverage includes defaults, constraints, coordinate bounds, evidence ordering/limits, foreign keys and protected deletion, scoped retry uniqueness, clearing chronology, self-vote rejection, policy/weight bounds, vote replacement, RLS and browser-role denial. Audit checks cover all four actions, equal-time ordering, independent snapshots, application append-only access, unique creation events, wrong-parent rejection, and event rollback after a failed mutation in the same SQL subtransaction. Contributor checks cover neutral defaults, required restriction reasons, explicit restoration, bounded/nonfinite weights, application deletion denial, RLS and private-field read/write denial. Place-record checks additionally cover independent child aggregation, evidence ordering, empty/null fields, resolved-warning exclusion, DTO privacy, campus defense, unknown-filter exclusion and pagination through actual backend search logic. This is not proof of a complete retry adapter, simultaneous transaction correctness, real Supabase Auth/Storage configuration, deployed persistence across restarts, or the fairness of seeded consensus. No paid AI calls or shared database writes occurred. The current browsing integration additionally passes backend/frontend verification described above; public API interfaces are unchanged.

## Remaining acceptance checks

- Implement eligibility checks/event writes and the accepted read views through the real adapter. Agree restriction administration/history, recovery, freshness/reopening and trust-version rules before implementing unagreed behavior.
- Connect real read/write adapters and verify competing/retried submissions produce one record/event, changed payload conflicts, and vote/status/history changes commit or roll back together.
- Test public-field privacy and active warnings through places, reports and chat; confirm clearing support changes recalculate parent status without erasing earlier evidence.
- Obtain actual collected observations for the merged seed preparation tooling. Review and apply generated SQL as a separate database-owner task. Keep fictional tests separate; never turn them into an outage fallback.
- Restore shared connectivity and verify actual migration history, grants, schema and persisted runtime reads. Storage is deferred until an upload requirement and its policy are agreed. No shared reset or deployment is authorized by this handoff.

See [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md) for backend readiness and [COLLABORATION.md](COLLABORATION.md) for ownership and PR coordination.

## Exact backend-owner implementation handoff

The database-owned interface is now:

- `Database.session()`: operation-scoped SQLModel session; no implicit success commit, closed on exit. Read failures propagate.
- `Database.transaction()`: one owned SQLModel session/transaction, commit on successful context exit, rollback on any exception and always release the connection. Keep **all** mutation work inside this context; returning a DTO must not bypass commit failure handling.
- `Campus`, `Building`, `PlaceDetailRecord`: existing mapped public-schema identities and complete place projection.
- `ReportPublicRecord`, `ClearancePublicRecord`, `ReportHistoryRecord`: mapped read-only community views. Validate `.record` using the existing response DTOs; never INSERT/UPDATE these views or call `SQLModel.metadata.create_all`. Filter report/campus/target and use history `occurred_at, sequence` ordering. These mappings are exercised against actual PostgreSQL in the new suite, not unused copies of every schema table.
- `ContributorStateRecord`: private eligibility/weight/reason/update-time storage only. Map only eligibility/weight into the existing internal ContributorState; never serialize this ORM row publicly. Refresh update time explicitly during accepted changes.

The backend owner must implement the existing `CommunityRepository` protocol in its services scope and wire it through `create_app`. Reports/clearances need private author lookups from their base tables to construct ReportRecord/ClearanceRecord; author IDs deliberately do not appear in the public JSON views. Existing SQL constraints/parameterized SQL can be used inside the owned session without adding speculative ORM mappings for every table.

For each mutation: recheck pilot membership/chronology/self-vote rules and contributor eligibility **inside** the transaction; coordinate locks for missing contributor rows as well as existing rows. Serialize parent-report mutations and lock the clearing target when applicable. Agree a consistent lock order with restriction administration. PostgreSQL uniqueness is a final guard, not a complete concurrent retry algorithm.

Normalize user payloads into SHA-256 excluding server submission time; scoped keys are `(author_id, building_id, idempotency_key)` for reports and `(author_id, report_id, idempotency_key)` for clearing claims. Identical concurrent retries must return the original record/time with exactly one creation event, while changed payloads raise IdempotencyConflict. Handle conflict races in a way that does not leave the transaction aborted.

Votes upsert by target/voter and snapshot freshly checked bounded weight plus all policy fields. Recompute clearance and parent status with the existing backend functions, preserving a resolved report when another corroborated clearance remains and reopening its prior derived state when clearing support is reversed. Commit votes, statuses and append-only history together. Public counts are distinct voters, never weight sums. Test concurrent distinct votes, repeated same-user votes, retry conflicts, restriction races and injected failures before enabling writes.

**Policy interface is still a backend/team decision:** TrustPolicy has four numerical fields and no version; SQL vote/event rows require an explicit private version plus snapshots. The backend owner must define the reviewed version binding and policy-change behavior before activation. Neither this task nor the database chooses production thresholds or silently changes accepted snapshots.

There is also an existing history integration gap: the HTTP history route currently sorts equal-time events by UUID, whereas the persisted timeline is ordered by occurrence time and sequence. The backend owner must preserve the repository's persisted order or otherwise reconcile ordering without exposing sequence as a new public field. No router or contract was changed here.

## Frontend and external handoff

Frontend owner: consume the existing contracts, retain independent details/report error states, display unresolved warnings and unknown facilities, and add chat evidence cards, clearance submissions/votes and report history when backend persistence is ready. Keep privileged database/AI keys out of VITE variables. No frontend edit is part of this task.

External dependencies: restore configured Supabase connectivity; confirm shared migration history/permissions; collect and human-review real campus observations using `seed/collection-template.json`; obtain approval for the exact migration/import SQL; configure Auth signing keys/redirects and hosting with their owners. No actual import SQL can be prepared without observations. The empty template validates and generates zero data inserts. Photo upload/Storage remains deferred, rather than silently provisioning a public bucket.

Person 3's locally verifiable code/schema/session/seed-plan deliverables are complete for this scope. Shared verification/application remains externally blocked, and the complete application still requires backend transactional implementation and frontend integration. SQL tests alone do not establish a working application.
