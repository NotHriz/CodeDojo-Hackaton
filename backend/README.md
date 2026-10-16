# Backend

Owner: the user (backend). Teammate 3 owns `app/models.py` and `app/database.py`; agree their interfaces before backend services depend on them. See [file ownership and handoffs](../COLLABORATION.md).

This is a Python package skeleton for the planned FastAPI, Pydantic, and SQLModel backend. There is no ASGI application, dependency manifest, database connection, or runnable server yet.

| Path | Responsibility |
| --- | --- |
| `app/main.py` | Future application entry point, middleware, and router registration |
| `app/models.py` | Persistence models agreed with the database teammate |
| `app/schemas.py` | Validated API request/response and AI tool schemas |
| `app/database.py` | Connection/session management; no import-time external connections |
| `app/routers/` | Places, reports, votes, clearance observations, identity, and chat endpoints |
| `app/services/` | Query logic, community aggregation, trust rules, and DeepSeek tool orchestration |

Copy `.env.example` to a local `.env` when configuration loading is implemented. Keep credentials on Render/the backend. Supabase Auth tokens must be verified before accepting reports or votes. The backend owns derived report status and private reliability; clients and AI cannot set them directly.

Agree trust thresholds and shared schemas before implementing the services. Register no fake success responses for unimplemented features. Deployment target: Render; persistent data and photos belong in Supabase.

See [project README](../README.md) and [onboarding](../onboarding.md) for scope and acceptance criteria.
