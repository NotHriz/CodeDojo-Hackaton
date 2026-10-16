# Backend work completed while the team was away

These changes are backend/API and integration documentation only. Frontend, Supabase schema/migrations, seed data, `backend/app/models.py`, and `backend/app/database.py` have not been edited.

## Review order

1. PR #3, `feat/backend-auth`: Supabase asymmetric access-token verification and `/api/auth/me`.
2. PR #4, `feat/backend-chat`: bounded DeepSeek search/details tools, source cards, request limits, explicit failures. Initially based on the auth branch.
3. `feat/backend-community`: authenticated reports/votes, idempotency contracts, separate clearing observations, configurable trust rules. Initially based on the chat branch; see the GitHub PR for its number.

Merge each prerequisite first, retarget the next PR to `main`, then delete the predecessor branch. Nothing has been auto-merged. Source branches form a stack so each PR shows only its feature.

## Verification

- 110 backend tests pass; dependency check passes.
- Tests use real generated EC/RSA signatures and mocked external providers/test persistence.
- No paid DeepSeek calls, real Supabase access, deployment, or frontend integration occurred.
- One existing Starlette test-client HTTPX deprecation warning remains.

## Database teammate

Start with [building adapter](contracts/places.md), then [community adapter](contracts/community.md). You still own models, database sessions, Supabase schema/policies, and seed/imports. Agree field mappings and implement real transactions/unique keys before connecting writes.

The backend composition root accepts `place_repository` and `community_repository`. All disconnected database features deliberately return 503. No runtime fake campus data was introduced. Building warning fields must be populated from actual unresolved reports.

## Frontend teammate

Review [places](contracts/places.md), [auth](contracts/auth.md), [chat](contracts/chat.md), and [community](contracts/community.md). Login through Supabase Auth, pass its bearer token for contributions, and reuse an idempotency UUID on submission retries. Render filters/source cards/warnings from structured fields. Treat 401/403/409/422/429/502/503 as explicit UI states; never substitute silent mocks for errors.

## Backend owner decisions/setup still needed

- Configure a real Supabase project with ES256/RS256 signing keys and token issuer origin; test real Auth flows.
- Connect the building and community adapters supplied by the database teammate.
- Review an experimental trust policy before explicitly activating it. There is no active numerical policy default. Reputation learning, expiry/reopening, and collusion resistance are not claimed complete.
- Configure the backend-only DeepSeek key and perform a small, deliberate real-provider quality test after records are available.
- Review process-local request budgets; they reset on restart and are not production abuse protection or spending caps.
- Deploy on Render, configure Netlify origins/Auth redirects, and rehearse the actual UI/backend/database demo.

See [backend/README.md](backend/README.md) for local startup and test commands. This is a reviewable backend implementation, not a completed live product.
