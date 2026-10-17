# Community reports and votes — backend handoff v0.1

Backend routes, input validation, identity checks, limits, and deterministic trust functions are implemented. The transactional PostgreSQL adapter is implemented and configured alongside the building adapter when DATABASE_URL is supplied; shared deployment/runtime verification remains pending. The team agreed experimental policy `iium-gombak-pilot-v1`; activation is explicit and disabled by default. This proposal does not prescribe SQL tables or claim production anti-fraud protection.

## HTTP contract

Public reads:

- `GET /api/reports?place_id=<opaque building ID>&limit=20&offset=0`: newest-first list, `items`, `total`, `limit`, `offset`; limit 1–100, offset nonnegative. Only IIUM Gombak records for the requested building are returned.
- `GET /api/reports/{report_id}`: one public report or 404. Report/clearing-observation IDs are UUIDs.
- `GET /api/reports/{report_id}/history?limit=20&offset=0`: public oldest-first audit timeline, scoped to an existing in-campus report. Events contain IDs, occurrence time, action, previous/new status, and public counts; author IDs and private weights are excluded.

All writes require a valid Supabase bearer access token. New reports and clearing observations also require an **`Idempotency-Key` UUID header**, generated once per intended submission and reused on retry. Votes are upserts by signed-in user and target, not additive anonymous clicks.

| Endpoint | Body | Result |
| --- | --- | --- |
| `POST /api/reports` | `place_id`, `barrier_type`, `description`, `observed_at`, optional `evidence_urls` | 201 public unverified report |
| `POST /api/reports/{id}/votes` | `stance`: `corroborate` or `dispute` | Updated public report |
| `POST /api/reports/{id}/clearance-observations` | `description`, `observed_at`, optional `evidence_urls` | 201 unverified clearing observation |
| `POST /api/reports/{id}/clearance-observations/{observation_id}/votes` | `stance` | Updated parent report with clearing observations |

Descriptions are trimmed, nonblank, at most 2000 characters. Barrier type is an extensible nonblank string up to 64 characters; agree collection labels with the frontend. At most three HTTP(S) evidence references are allowed. They are stored as references, not fetched by the API; photo upload/storage policy is still a separate handoff. Public evidence must not expose service credentials or private images.

Observation times must have timezones and cannot exceed server time by more than five minutes. Clearing observations cannot predate the original barrier observation. Submission time comes from the backend. Client-supplied user ID, weight, score, status, and unknown fields are rejected.

Public report fields: `id`, `place_id`, `campus_id`, `barrier_type`, `description`, `observed_at`, `submitted_at`, `evidence_urls`, `status`, `community` (`supporters`, `disputes`), and `clearance_observations`. Clearing observations have `id`, description/evidence/times, status, and community counts. Author IDs, internal weights/scores, and restrictions are excluded from public DTOs.

Statuses: `unverified`, `community_corroborated`, `disputed`, `resolved`. Community corroboration represents agreement, not verified truth or accessibility certification.

## Trust calculation

The team agreed `iium-gombak-pilot-v1` on 17 October 2026. Select it with backend-only `COMMUNITY_POLICY_VERSION=iium-gombak-pilot-v1`; the committed default `disabled` keeps voting unavailable. Unknown/blank version settings fail startup. Normal startup binds the same immutable version and thresholds to the API and PostgreSQL adapter. Explicitly injected policies retain precedence, but cannot reuse this published version with different thresholds.

| Rule | Pilot value |
| --- | --- |
| Distinct supporting voters | At least 3 |
| Supporting weight | At least 3 |
| Supporting share of all vote weight | At least 67% (`0.67`, not two-thirds) |
| Individual weight cap | 2 |
| New account weight | 1 |

Everyone starts at weight 1. No higher-weight assignment mechanism is agreed or introduced; do not promote accounts manually until its process is agreed. No automatic rewards for agreement or penalties for disagreement exist. Both report and clearing votes use these rules. With all weights 1: 3 support/0 dispute and 3/1 corroborate; 3/2 disputes; 2/0 remains unverified. Two-thirds (approximately 66.67%) fails the exact 67% cutoff.

The repository snapshots the version and all four thresholds in accepted vote rows and history within the mutation transaction. Targets with incompatible existing report or clearing snapshots return 409 and require a separately reviewed policy migration. Never edit a published version, rewrite old snapshots, or silently reaggregate incompatible votes. Introduce a new version when rules change. A version matching these thresholds is an implementation identifier, not evidence of accuracy or safety. Use the label **community corroborated**.

Local ignored configuration selects this policy; restart any already-running backend to load it. Shared deployment/runtime verification remains pending. `TrustPolicy` remains the four-number calculation DTO; the separate immutable binding owns its version. Injected integration can still use `create_app(trust_policy=reviewed_policy, trust_policy_version=reviewed_version)`.

`aggregate_votes` requires unique voter IDs and no author vote. New members have neutral weight one; supplied internal weights are bounded to [1, configured maximum]. A report is community corroborated only when all quorum/weight/ratio conditions hold. Otherwise, any opposition marks it disputed; without opposition it stays unverified. A strong enough quorum can outweigh limited opposition, but a single trusted member cannot establish consensus.

`derive_report_status` resolves a report only when a later clearing observation is itself community corroborated. An unverified clearing claim cannot resolve anything. Changing conditions do not mark the original report false. These functions never update reputation or punish disagreement.

Restrictions are read through an internal `ContributorState`; unknown/new contributors default to neutral eligibility. Blocked contributors receive a visible 403. No silent report dropping, automatic consensus-based reputation learning, or Sybil/collusion-proof identity is implemented. Freshness/expiry, reopening after recurrence, reputation calibration, and recovery from restrictions still need product rules before a real rollout.

## Database teammate handoff — required atomic behavior

Implement `app.services.community.CommunityRepository` over your owned persistence/session layer. Inject through `create_app(community_repository=adapter, trust_policy=reviewed_policy)`; construct the persisted adapter with the same reviewed policy and version. Default configured wiring also accepts `trust_policy_version`. The protocol lists read/create/vote/clearance/history methods and internal record types. API inputs and public DTOs are backend-owned; SQL schema and migrations remain yours. History records use `report_created`, `vote_updated`, `clearance_submitted`, and `clearance_vote_updated` actions; return public `ReportEventResponse` objects without internal actor/weight data.

Every mutation must be a single transaction with the relevant report/observation locked or an equivalent concurrency-safe strategy:

1. Recheck contributor restrictions and target membership/campus inside the transaction, not only in the route's earlier read.
2. Reject self-votes and enforce a unique voter/target key. Repeated votes replace stance instead of incrementing counts.
3. Snapshot the bounded weight when accepting a vote; record policy version and subsequent changes in history. Do not take a weight from request JSON or user-editable metadata.
4. Recompute the affected observation/report using the backend trust functions. Preserve original report evidence/times and record derived-status history atomically with the vote.
5. For clearing votes, recalculate the observation and the parent report together. Only corroborated clearing observations resolve a report. Changing a clearing vote must recalculate rather than leave a stale resolved state.
6. For creates, use an actor + operation + target + idempotency-key uniqueness constraint and normalized payload digest. An identical retry returns the original record/time; different content with the same key raises `IdempotencyConflict`. Submission timestamps are excluded from the user-payload digest. Never perform a second insert because a retry received a new server timestamp.
7. Recheck clearing-event chronology and restrictions under the transaction. Raise `ContributionDenied` if eligibility changed. Do not return success when the transaction fails.

`ReportRecord` and `ClearanceRecord` contain internal author IDs used for eligibility. Their `.public` fields contain only response DTOs. `get_contributor` returns `ContributorState | None`; private score/weight storage must not be publicly readable. New-account neutrality does not require trusting a user-submitted score.

Building adapter integration: map actual unresolved report statuses into `PlaceDetail.active_warnings`; exclude resolved reports there. This is necessary for map/chat warnings to reflect community changes. There is no runtime fake repository or automatic cross-service in-memory persistence.

## Failures and limits

- 401 for missing/invalid sign-in; 403 for restricted accounts or self-votes.
- 404 for missing/out-of-campus targets; 409 for idempotency content conflicts.
- 422 for invalid fields, timestamps, UUIDs, or missing idempotency headers.
- 429 with `Retry-After` for contribution limits.
- 503 without a community adapter, without required building persistence for report creation, or without a reviewed voting policy.
- Sanitized 500 for unexpected persistence failures. Failed requests do not return a successful report/vote.

Contribution limits are five attempts per verified user per minute and 500 globally per UTC day, process-local, reset on restart. These are demo limits, not durable/distributed spam prevention. Idempotency correctness depends on real database constraints and transactions.

Tests use explicit in-memory adapters to exercise routes and backend policy functions. They do not prove real database concurrency, migration correctness, stored reliability, or real-community fairness. Those require database integration and intended-user review.

## Implemented transaction adapter

`app.services.postgres_community.PostgresCommunityRepository` implements the existing protocol without schema changes. Every mutation first inserts a missing neutral contributor row with ON CONFLICT DO NOTHING and locks the actual row, serializing even missing-row restriction races. Lock order is contributor, pilot building/report, then clearing target. Restriction administrators must follow that same contributor-first order and upsert restrictions rather than treating an absent row as an unlocked state.

Same-actor creates serialize under that row lock before comparing the scoped retry key and SHA-256 digest; normalized UTC observation time and validated request fields are included, server submission time is excluded. Existing SQL uniqueness constraints remain the final guard. Private weights are freshly loaded under lock; the earlier route weight is not authoritative. Vote upserts, clearing/parent statuses and accepted history snapshots share one transaction. Parent locking serializes report and clearing votes, preserving other corroborated clearances on reversal. Equal-time history retains persisted sequence order without exposing the sequence publicly.

Real disposable PostgreSQL tests cover competing identical/conflicting retries, concurrent distinct/repeated votes, clearing resolution/reversal, restriction races, and injected post-history failures for all four mutation types. These are local transaction checks, not real Auth/community validation or proof of shared deployment. Shared schema/permissions and deployment selection of the agreed policy/version remain activation requirements.
