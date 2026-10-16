# Akses Campus

A campus accessibility finder with an AI assistant helping wheelchair users find facilities and check recent barrier reports before visiting.

Built as a planned three-person, 24-hour hackathon project under the Persons with Disabilities track. IIUM is the proposed pilot campus.

> Where can I study nearby with a step-free entrance and an accessible toilet, and how recently was that information checked?

## Status

**Planning and documentation only.** There is no runnable application, database schema, dependency manifest, seed dataset, or deployment yet. The stack and structure below describe the implementation baseline.

Teammates and future agents should read [onboarding.md](onboarding.md) for scope, judging criteria, related work, acceptance criteria, responsibilities, and engineering guidance.

## Planned MVP

- Explore approximately 10–15 campus locations using a Google map or accessible list.
- Filter for step-free entrances, accessible toilets, and designated parking.
- View facility observations, evidence, source, and last checked date.
- Ask the AI assistant to find matching places or explain a location's recorded accessibility; show source cards and update the map/list from structured results.
- Submit temporary barrier reports, clearly labelled as unverified.
- Let an authenticated reviewer confirm, reject, or resolve reports with status history.

Facilities use **yes / no / unknown** values. Permanent observations and temporary barriers remain separate records.

**Demo flow:** Ask for a study space with a step-free entrance and accessible toilet -> see matching map markers and evidence cards -> inspect a barrier warning -> submit a report -> reviewer confirms and later resolves it.

Route planning, volunteer dispatch, city-wide coverage, and AI accessibility certification are outside the MVP. The chatbot is a planned MVP feature, built on the working place/search API. Conversational report drafting is a stretch feature.

## AI assistant

The assistant is grounded in campus records and exposes two initial tools: `search_places` and `get_place_details`. It can interpret search requirements, return matching locations, and explain known facilities and active warnings. The frontend displays editable interpreted filters, matching markers, and source cards with observation dates and report status.

The planned flow is `Vue chat panel -> POST /api/chat -> backend-validated tool call -> database query -> answer + cards + map/list updates`. Tool schemas and endpoint schemas are design contracts to finalize during implementation; no chatbot is implemented yet.

- The backend allows only explicitly defined tools and validates arguments. The model cannot run arbitrary SQL, confirm reports, or grant reviewer privileges.
- Answers must distinguish unknown facilities and unverified reports; missing evidence must not become a confident accessibility claim.
- Place descriptions and submitted reports are untrusted content, never instructions for the model.
- Keep ordinary filters usable when the AI is unavailable. Use timeouts, bounded tool calls, and request limits to manage latency and cost.
- Optional `prepare_barrier_report` produces an editable draft only. Explicit user submission goes through the normal validated report endpoint.
- AI provider/model selection remains open. Credentials stay on the backend; provider usage is billed separately from Google Maps.

## Technology stack

| Area | Baseline |
| --- | --- |
| Frontend | Vue 3, Vite, JavaScript, Vue Router |
| Styling | Tailwind CSS with the Vite plugin |
| Map | Google Maps JavaScript API, Advanced Markers |
| Backend | Python, FastAPI, Pydantic |
| Database access | SQLModel |
| Database | PostgreSQL |
| Images | Object storage; provider undecided |
| AI assistant | Backend tool-calling service for campus search and place questions; provider/model undecided |

Use one repository and one backend, organized by feature. Google provides the base map; our database provides coordinates, accessibility evidence, and reports.

```mermaid
flowchart LR
    Browser[Vue + Tailwind] -->|Base map| Google[Google Maps]
    Browser -->|/api| API[FastAPI]
    API --> DB[(PostgreSQL)]
    API --> Images[Photo storage]
    API -->|Validated tool calls| AI[AI provider]
```

During development, Vite will proxy `/api` to FastAPI. The production plan is to serve the built frontend and API from the same FastAPI service and public origin. Hosting is not selected yet.

## Planned project structure

Only the documentation files exist today; application directories will be created during implementation.

```text
frontend/src/
  components/
  views/
  composables/
  services/
backend/app/
  main.py
  models.py
  schemas.py
  database.py
  routers/
  services/
seed/
README.md
onboarding.md
```

## Setup readiness

Installation and startup commands will be added once the scaffold and dependency manifests exist. Do not assume `npm run dev` or a Python entry point is available yet.

Before implementation, prepare:

1. Node.js compatible with the selected Vite release and a Python version supported by the pinned backend dependencies.
2. A PostgreSQL database and backend-only connection URL.
3. A Google Cloud project with billing enabled, Maps JavaScript API enabled, a map ID, and a browser key restricted to approved websites and the required API.
4. A photo-storage provider if uploads are included, and a reviewer-authentication implementation.
5. An AI provider/model and backend credential; agree request limits, timeout, and conversation retention before integration.

Proposed configuration names, to finalize when scaffolding:

| Variable | Side | Purpose |
| --- | --- | --- |
| `VITE_GOOGLE_MAPS_API_KEY` | Browser | Restricted, browser-visible map key |
| `VITE_GOOGLE_MAPS_MAP_ID` | Browser | Map ID for Advanced Markers |
| `DATABASE_URL` | Backend | PostgreSQL connection string; secret |
| `SESSION_SECRET` | Backend | Session signing secret if session authentication is selected |
| `AI_API_KEY` | Backend | AI provider credential; secret, proposed provider-neutral name |
| `AI_MODEL` | Backend | Selected model identifier |

All `VITE_*` variables are public build configuration. Never place database, storage-service, reviewer, or AI secrets in them. Add `.env.example` files with placeholders and ignore real `.env` files when the scaffold is created.

## Google Maps cost

As checked on **16 October 2026**, global Dynamic Maps pricing includes **10,000 free loads per month**, then **US$7 per 1,000 additional loads** through 100,000 monthly loads. Usage is aggregated across projects on the billing account; taxes and other services are excluded. Billing setup is still required. [Official pricing](https://developers.google.com/maps/billing-and-pricing/pricing)

Custom markers, panning, and zooming do not add map loads; recreating the map does. Places search, geocoding, and directions can incur separate charges. Use stored campus coordinates for the MVP. [Billing FAQ](https://developers.google.com/maps/faq)

## Quality and responsible use

- Keep the list and report flow usable with a keyboard and without the map.
- Pair status colors with labels and show unknown information explicitly.
- Label sample data and unverified reports honestly; reviewer confirmation is not accessibility certification.
- Enforce reviewer permissions and report transitions on the backend.
- Verify persistence, filtering, authorization, report history, and the deployed demo flow.
- Avoid collecting disability histories or requiring precise live location.
- Send only necessary context to the AI provider, avoid logging sensitive chat content, and ground answers in database evidence.

No build or application tests have run because implementation has not started. Add actual build, lint, test, seed, and deployment commands as they become available.

## Related work

Existing work includes [Wheelmap](https://news.wheelmap.org/en/), [AccessNow](https://accessnow.com/), [AccessAble university guides](https://www.accessable.co.uk/inspire-me/heading-to-uni), and [IIUM's 2023 accessibility mapping initiative](https://news.iium.edu.my/enhancing-iium-accessibility-empowering-students-of-all-abilities/).

The proposed project angle is campus-specific evidence and a visible report-review-resolution workflow. This is a hypothesis to validate, not a claim that competitors lack these features. See [the onboarding research comparison](onboarding.md#related-work-and-evidence) for sources and limitations.
