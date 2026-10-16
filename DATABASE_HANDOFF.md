# Database integration handoff

Owner: User 3 / database. Last updated: 16 October 2026 (Asia/Kuala_Lumpur).

This is the database owner's maintained status and integration checklist. Update it in every database task/PR that changes schema, models/sessions, adapters, seeds, policies, verification, or deployment readiness. Record what actually changed and ran; keep pending work separate from merged and deployed functionality. Detailed field mappings remain in [supabase/README.md](supabase/README.md); API contracts remain owned by the backend owner.

## Current status

Five PostgreSQL migrations are merged through [PR #15](https://github.com/NotHriz/CodeDojo-Hackaton/pull/15). They provide eleven backend-only tables. These are versioned schema definitions, not a connected application database. No shared Supabase project was linked or migrated by this work, and no real campus records were imported.

[PR #16: clearing-vote storage](https://github.com/NotHriz/CodeDojo-Hackaton/pull/16) is open at this handoff's update. Its sixth migration, twelfth table, and sixth test suite are pending review and are not part of this documentation PR's main-branch baseline. Update this status after merge; do not treat it as deployed.

`backend/app/models.py` and `backend/app/database.py` remain placeholders. No real place/community repository is connected. Database credentials alone do not create an adapter. No trust policy or observation aggregation rule is activated, and no SQL trigger derives report status.

## Migration inventory

Apply accepted migrations in filename order through the agreed Supabase migration workflow. Never rewrite an applied migration or replay the sequence against existing tables manually.

| Migration | Storage / integrity | Review status |
| --- | --- | --- |
| `20261016000100_building_foundation.sql` | Campuses/buildings, coordinates, three facility values defaulting to unknown | Merged, PR #11 |
| `20261016000200_place_evidence.sql` | Entrances, dated observations, ordered photo/evidence references | Merged, PR #12 |
| `20261016000300_barrier_reports.sql` | Reports, scoped retry keys/digests, ordered evidence (maximum three references) | Merged, PR #13 |
| `20261016000400_report_votes.sql` | Unique member/report votes, self-vote prevention, explicit bounded weight/policy snapshots | Merged, PR #14 |
| `20261016000500_clearance_observations.sql` | Clearing claims/evidence, scoped retry keys, chronology bound to actual parent time | Merged, PR #15 |
| `20261016000600_clearance_votes.sql` | Unique member/clearing votes, actual parent/author membership, private snapshots | Pending, PR #16 |

All implemented tables enable RLS and revoke browser-role access, including inherited grants. Backend service-role CRUD grants do not replace authenticated API identity/eligibility checks. Private author IDs, retry keys/digests, voter identities, weights and policy metadata must never enter public DTOs. No Storage bucket, upload API, public database policy, or private contributor reliability store exists yet.

The alternate remote `feat/database-foundation` branch uses another places schema and also creates campuses/entrances. Do not combine that migration unchanged with this accepted sequence. Its shared-project application status has not been verified.

## Backend integration order

1. Agree SQLModel/PostgreSQL dependencies and their pinned manifests with the backend owner. User 3 owns models/session implementation; dependency manifests, service logic, composition wiring and API contracts require the backend owner's scoped handoff. Connections must not open at module import time.
2. Implement models/session management and agree the adapter location/lifecycle. Own and close sessions per operation/request; return fully validated DTOs rather than expired/lazy ORM objects. Database failures must propagate, not become empty successful results or demo data.
3. Implement the read-only [PlaceRepository](contracts/places.md). Map building identity to `place_id` where required, join campus identity, preserve unknown facilities and null observation dates, and order evidence by position. Agree how current facility summaries are maintained; do not invent a latest-observation rule. Join actual unresolved reports into active warnings and exclude resolved reports.
4. Add the remaining audit-history and contributor-restriction persistence before enabling community writes. Agree explicit trust thresholds and policy-version assignment with the backend owner: `TrustPolicy` currently has no version field, while vote storage requires a private version/snapshot. Stored versions in tests are illustrative, not activated settings.
5. Implement the [CommunityRepository](contracts/community.md) transaction requirements and verify real concurrency. Inject the real adapters and reviewed policy through `create_app(...)` only after their integration checks pass. Public response shapes remain backend-owned.

## Community transaction requirements

- Lock the relevant report/clearing observation and recheck verified actor identity, contributor restrictions, campus and target membership inside the mutation transaction. Self-vote constraints are storage protection, not complete authorization.
- For creates, compute a SHA-256 digest from normalized user payload excluding server submission time. Report uniqueness is `(author_id, building_id, idempotency_key)`; clearing uniqueness is `(author_id, report_id, idempotency_key)`. Identical retries must return the original record/time; changed content must raise `IdempotencyConflict`. The database checks digest format only; the adapter must implement comparison/retry behavior.
- Read a clearing claim's internal `report_observed_at` from its locked parent. Its composite foreign key binds the copied time to the actual report; the claim cannot predate it. Observation times must be finite, timezone-aware at the API boundary, and at most five minutes after submission.
- Upsert each vote by member/target and refresh its complete weight/policy snapshot and `updated_at`. Weights come from private contributor state, never user-editable metadata. Current vote rows do not preserve past snapshots: audit storage remains necessary.
- Use backend trust functions to recalculate clearing and parent statuses, including after a changed clearing vote. Preserve original report evidence/times. Commit votes/claims, derived statuses, and audit history atomically. A new clearing claim alone cannot resolve a report.
- In pending PR #16, the clearing author cannot vote on their own claim; the original barrier reporter may vote on another member's claim. The composite target reference rejects a vote under the wrong report.

## Verification and limits

The most recent database execution tested commit `b211524` on `feat/database-clearance-votes`: all six PostgreSQL 18 SQL suites passed in a disposable loopback-only cluster. All six migrations applied transactionally; test records were rolled back and the server stopped. The first five suites/migrations are in the merged baseline; the sixth is in pending PR #16.

Run from the repository root on Windows with PostgreSQL 18 installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
```

Optional runner arguments are `-PostgresBin 'C:\path\to\postgresql\bin'` and `-Port 55440`. Minimal role fixtures exist only for the disposable cluster; never run `supabase/tests/roles.sql` against Supabase. Temporary cluster files are retained for diagnosis.

Coverage includes defaults, constraints, coordinate bounds, evidence ordering/limits, foreign keys and protected deletion, scoped retry uniqueness, clearing chronology, self-vote rejection, policy/weight bounds, vote replacement, RLS and browser-role denial. This is not proof of a complete retry adapter, simultaneous transaction correctness, real Supabase Auth/Storage configuration, deployed persistence across restarts, or the fairness of seeded consensus. No paid AI calls or shared database writes occurred. Backend/frontend suites were not rerun for this documentation task.

## Remaining acceptance checks

- Persist audit events with historical snapshots and contributor eligibility/restriction state; agree recovery, freshness/reopening and trust-version rules before implementing unagreed behavior.
- Connect real read/write adapters and verify competing/retried submissions produce one record/event, changed payload conflicts, and vote/status/history changes commit or roll back together.
- Test public-field privacy and active warnings through places, reports and chat; confirm clearing support changes recalculate parent status without erasing earlier evidence.
- Build a repeatable seed/import process using actual collected observations. Keep any fictional fixtures explicit and separate. Never turn fixtures into an outage fallback.
- Configure and verify Supabase access/Storage policies, migration history, shared deployment and persistence across backend restarts. No shared reset or deployment is authorized by this handoff.

See [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md) for backend readiness and [COLLABORATION.md](COLLABORATION.md) for ownership and PR coordination.
