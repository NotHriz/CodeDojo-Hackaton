# Frontend

Owner: teammate 1.

This is a directory skeleton for the planned Vue 3, Vite, JavaScript, Vue Router, and Tailwind application. Dependencies, entry points, and build configuration have not been scaffolded yet; no npm commands are available.

| Directory | Responsibility |
| --- | --- |
| `src/components/` | Map, custom markers, filters, bottom sheet, chat/source cards, and shared controls |
| `src/views/` | Explore, reports, sign-in, and community pages |
| `src/composables/` | Shared reactive state and logic, including selected building and filters |
| `src/services/` | FastAPI client and Supabase Auth client integration |

Copy `.env.example` to a local `.env` when implementing configuration. All `VITE_*` values are browser-visible. Never put privileged Supabase, database, or DeepSeek credentials here.

Keep map and list selection synchronized. Support English UI, keyboard navigation, yes/no/unknown facilities, and prominent barrier warnings. Deployment target: Netlify, with the Python API on Render.

See [project README](../README.md) and [onboarding](../onboarding.md) before implementing.
