# Shared Supabase deployment follow-up, 17 October 2026

Applied the eleven planned migrations and one forward permission correction (20261017000500) under the explicit deployment instruction. All 12 are recorded; the shared schema/RLS/grant audit matches. Service-role API reads return 200 across fresh app instances; browser direct reads are denied. Shared data remains empty because no reviewed campus dataset exists. Local demo is disabled and policy iium-gombak-pilot-v1 remains selected.

182 backend plus 4 audit tests pass locally, including cloud-default-grant regression. Applied correction and deployment docs are published for PR review on chore/deploy-supabase-schema. A restricted runtime credential, reviewed import, hosting/Auth/provider setup and full deployed rehearsal remain pending. Current local postgres credentials are administrative; temporary SET ROLE smoke tests do not replace them. No test fixtures or paid AI calls ran against shared services. See DATABASE_HANDOFF.md and supabase/DEPLOYMENT_PLAN.md for the applied record.

Earlier handoffs below are historical and superseded by this status.

# Frontend integration follow-up, 17 October 2026

PR #30 review fix: successful building-level submissions/votes now use the non-destructive community refresh. A browser regression first reproduced clearing-draft loss after another barrier submission, then passed with the fix. It verifies draft text, observation timestamp, open history, retry UUID/body and map warning refresh across that separate submission. Production build and four helper tests pass. These remain intercepted UI checks; real external-service rehearsal is still pending.

On feat/frontend-community-flows (prepared for PR review), the full-stack task adds public chat/source cards and structured map/list filters, authenticated clearing submissions/votes, and public paginated history. API paths/DTOs are unchanged. Mutation refresh preserves drafts/focus; clearing retry identity and timestamp are stable. Four helper tests, production build and contract-driven Edge browser checks pass. Browser replies are intercepted fixtures, not a live Auth/provider/database rehearsal. No shared writes or paid AI calls occurred. PRs #28/#29 are merged; shared schema/runtime verification and deployed rehearsal remain pending. See frontend/INTEGRATION.md for test commands and deferred endpoints.

Earlier handoffs below are historical; this section supersedes missing frontend-flow statements.

# Versioned policy activation follow-up

The team agreed experimental `iium-gombak-pilot-v1` (3 supporters, support weight 3, exact 67% support share, maximum individual weight 2; everyone starts at 1). The selector and snapshot tests are implemented on `feat/versioned-trust-policy`, prepared for PR review. Local ignored settings select it; restart an existing backend to reload. Committed configuration defaults to disabled. No promotion algorithm, agreement rewards, disagreement penalties or shared database writes were introduced. Shared deployment/runtime verification remains pending. See the [policy contract](contracts/community.md#trust-calculation).

The transactional repository from PR #28 is merged; its policy version binding is already implemented. The older implementation/deployment notes below are historical.

# Current backend implementation status

The transactional PostgreSQL CommunityRepository is implemented on `feat/transactional-community`, prepared for PR review and not merged or deployed. Configured building/community adapters share the lazy database engine. All 164 backend tests pass with disposable PostgreSQL, including concurrency and atomic rollback; no shared writes or paid AI requests occurred. See [backend setup](backend/README.md#transactional-community-persistence) and [database status](DATABASE_HANDOFF.md#transactional-community-follow-up).

Voting still requires an explicit reviewed policy and version; there are no active thresholds. Shared target confirmation, eleven-migration deployment, runtime permissions, real Auth/provider checks and frontend integration remain pending. The legacy PostgreSQL SQL runner was also attempted on PostgreSQL 17.11: it stops in the existing foundation test because a protected DELETE produces SQLSTATE 23503 while that test expects 23001. No migration was changed to work around this; the new backend transaction suite passes against the actual target's PostgreSQL major version.

The earlier handoff below is historical; its pending-adapter and test-count statements are superseded by this section.

# Backend integration handoff

Backend/API and integration documentation are implemented. Frontend, Supabase migrations, seed data, `backend/app/models.py`, and `backend/app/database.py` remain with their owners.

## Current verification

- Earlier authentication, chat, community, explicit local demo, and CI PRs have merged. There is no remaining stacked merge queue.
- 148 backend tests pass locally; dependency checks pass. One existing Starlette test-client HTTPX deprecation warning remains.
- Tests use generated EC/RSA signatures, mocked providers, and test repositories. The current browsing slice also passes disposable PostgreSQL API and Vue browser checks with fictional fixtures. No paid DeepSeek calls, shared Supabase access or deployment occurred.
- Review regressions cover mixed search/detail calls, maximum-length answer/history round trips, malformed provider JSON, and report/clearance history transitions.
- The community test adapter now preserves resolved reports after original-report votes and recomputes status when clearing support changes. This does not demonstrate SQL concurrency or transactional correctness.

## Database teammate

Start with the [building adapter](contracts/places.md), then the [community adapter](contracts/community.md). You own models, sessions, Supabase schema/policies, and seed/imports. Agree field mappings and implement real transactions/unique keys before connecting writes.

The composition root accepts explicit `place_repository` and `community_repository` injections. Without a place injection, `DATABASE_URL` now creates the live PostgreSQL place adapter; migrated tables/views and checked campus data must already exist. Community persistence remains disconnected and returns 503. The explicit development demo supplies fictional buildings only and cannot exercise community persistence. Building warnings must be joined from actual unresolved reports.

Before enabling votes, jointly agree thresholds and how policy/version snapshots are persisted with votes and history. The current `TrustPolicy` has no version field and no active numerical default; this review does not invent either. Reputation learning, expiry/reopening, and collusion resistance remain incomplete.

## Frontend teammate

Review [places](contracts/places.md), [auth](contracts/auth.md), [chat](contracts/chat.md), and [community](contracts/community.md). Login through Supabase Auth, pass bearer tokens for contributions, and reuse an idempotency UUID on retries. Render map/list matches from `places` and evidence cards from `sources`; an extra cited detail record can be excluded by the current filters. Retain up to six history messages within the role-specific chat limits.

Treat 401/403/409/422/429/502/503 as explicit UI states. Never substitute silent mocks for failures.

## Pre-demo integration checks

`GET /api/health` checks process liveness only. Before declaring the product ready:

1. The building adapter is connected and verified locally with disposable fixtures; verify checked real campus list/details, unknown facilities, and warnings after deployment. Declare fictional demo mode if using it.
2. Test real Supabase sign-in and `/api/auth/me`, plus unsigned and forbidden contribution requests.
3. With the community adapter and agreed policy, submit a report, retry its idempotency key, and verify one persisted report/history event. Test distinct voters, original-report votes after resolution, and reversed clearing votes using real transactions.
4. Confirm unresolved reports appear in building warnings and chatbot sources. Verify a corroborated clearance removes the active warning while preserving history.
5. Run a small deliberate DeepSeek test: matching searches, unknown data, conflicting reports, ambiguous names, and no matches. Source-card validation does not guarantee correct model prose. Verify timeout/provider failure UI states.
6. Verify client addresses behind the deployed proxy and review process-local budgets. Shared networks can share buckets; restarts reset limits. These are not distributed abuse protection or spending caps.
7. Configure Render/Netlify origins and Auth redirects, then rehearse the deployed keyboard-accessible map/list/report/chat flow.

See [backend/README.md](backend/README.md) for startup and tests. External integration remains incomplete until these checks pass.
