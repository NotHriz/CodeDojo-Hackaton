# Supabase schema and configuration

Owner: teammate 3/database.

Schema changes use the Supabase CLI and versioned PostgreSQL migrations in `migrations/`. The initial places schema is in `migrations/20261016160000_initial_places_schema.sql`. Do not edit a migration after it has been applied to a shared project; add a forward migration instead.

For local database validation, install the Supabase CLI, then run `supabase start` and `supabase db reset` from the repository root. `db reset` is for the local Supabase stack only; never use it against the shared project. After the project owner has created the shared project, link it with `supabase link --project-ref <project-ref>` and apply pending migrations with `supabase db push`. Keep the database password and all Supabase keys outside the repository.

The initial migration creates campuses, places, entrances, and facility observations. It contains no campus records: only add verified observations through a reviewed, repeatable seed/import workflow. It enables row-level security without client-facing policies; application reads and writes must go through the backend using a privileged server-side connection. Never expose a service-role key or database credential to the frontend.

The database owner also owns `backend/app/models.py`, `backend/app/database.py`, and `seed/`. The backend owner owns API schemas and service logic. Before implementing Python models/session access, agree the database dependency, session lifecycle, and adapter interface with the backend owner. The places API contract requires mapping persisted rows into validated `PlaceDetail` records; no runtime adapter is connected yet.

- Version shared schema changes instead of making undocumented dashboard edits.
- Apply shared migrations through the database owner; never rewrite already applied migrations.
- Keep reliability records private and align public access with the backend/API contract.
- Document Auth redirect URLs and Storage/database access rules without storing credentials.
- Coordinate schema, backend, and seed changes before shared deployment.

See [collaboration rules](../COLLABORATION.md#shared-database-rules) and [onboarding](../onboarding.md).
