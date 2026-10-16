# Supabase schema and configuration

Owner: teammate 3/database.

This directory is reserved for versioned migrations and documented Auth/Storage policies. Tooling and SQL schema are not implemented yet. `migrations/` is an empty tracked directory; choose and document the migration runner before adding scripts.

The database owner also owns `backend/app/models.py`, `backend/app/database.py`, and `seed/`. The backend owner owns API schemas and service logic; agree fields and session interfaces before either side implements them.

- Version shared schema changes instead of making undocumented dashboard edits.
- Apply shared migrations through the database owner; never rewrite already applied migrations.
- Keep reliability records private and align public access with the backend/API contract.
- Document Auth redirect URLs and Storage/database access rules without storing credentials.
- Coordinate schema, backend, and seed changes before shared deployment.

See [collaboration rules](../COLLABORATION.md#shared-database-rules) and [onboarding](../onboarding.md).
