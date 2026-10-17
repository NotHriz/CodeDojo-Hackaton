# Frontend

Vue 3, Vite, JavaScript, Tailwind and Vue Router. The user now owns the full-stack implementation task; prior teammate ownership remains the default outside explicitly assigned work. This increment implements chat, clearing observations/votes and public report history using existing API contracts.

## Run and verify

From the repository root:

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
npm run build --prefix frontend
node --test frontend/tests/community-ui.test.js
```

Create local configuration from `.env.example` only if `.env` does not already exist. Vite proxies `/api` to FastAPI at localhost:8000. Production uses VITE_API_BASE_URL. All VITE values are browser-visible; never include database, privileged Supabase or AI secrets.

## Implemented flows

- Public Explore chat: bounded conversation context, selected building context, source cards, demo labels, unknown dates/facilities, interpreted editable filters and matching map/list results. Extra cited details are not added to matches. Manual browsing works independently of AI failures.
- Report cards: signed-in original-report votes, clearing submission with local observation time and optional public HTTP(S) evidence link, clearing votes, status/count updates and warning refresh.
- Public history: lazy loading, server order preserved including equal timestamps, pagination, keyboard-scrollable timeline and explicit retry states.
- Failed clearing submissions preserve the draft, UUID and observation timestamp on retry. Edited payloads start a new intended submission. No success message is produced for failed writes.
- UI errors remain explicit for authentication, restrictions, policy conflicts, validation, limits and service outages. No fabricated API/AI response is used in the application.

A source card is the record snapshot returned with an answer; open building details for current conditions. Chat/drafts are held in component memory, with no added localStorage persistence. Existing Supabase sign-in session behavior is unchanged.

## Verification scope

Four helper tests and the production build pass. `tests/community-flows-smoke.cjs` verifies the real Vue UI/API client in Edge with intercepted contract responses: chat outage/retry, matching results versus extra evidence, signed-out controls, clearing retry identity, 403 handling, status/warning refresh, equal-time history order/pagination/error, and mobile overflow. All browser responses are test-only; this is not a live Supabase/AI rehearsal. No application dependencies were added.

See [integration and browser test instructions](INTEGRATION.md). Shared deployment and real Auth/AI/schema validation remain pending. Existing proposed permanent-facility contributions/votes, uploads, username resolution and tickets are not implemented by this increment.
