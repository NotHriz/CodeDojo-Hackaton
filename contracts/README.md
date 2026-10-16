# Shared contracts

Editor: the user/backend owner. Affected frontend and database teammates review changes before implementation.

This directory holds versioned API examples and shared interface decisions. [Building discovery v0.1](places.md) is implemented/tested in the backend and awaits frontend/database review; its persistence adapter is not connected. Other planned endpoints in [onboarding](../onboarding.md#initial-api-contract) remain unimplemented.

Agree the first building list/details slice before three teammates implement incompatible shapes. For each slice, record:

Authentication: [Supabase bearer verification](auth.md) implements `/api/auth/me` and documents frontend sign-in and signing-key requirements.

Assistant: [chat contract](chat.md) describes the read-only tools, structured UI response, provider configuration, request limits, and explicit failure behavior.

Community: [reporting/voting contract](community.md) specifies signed-in submissions, clearing observations, private reliability inputs, explicit-policy trust functions, and required atomic database behavior. Persistence and numeric-policy review remain pending.

1. Endpoint method/path, authentication, parameters, and example success/error JSON.
2. IDs, facility values, report statuses, nullability, and date formats.
3. Data fields owned by the database and public fields exposed by the backend.
4. Frontend behavior for loading, empty, partial, warning, and error states.
5. Contract version/change notes and which consumers must be updated.

Future FastAPI-generated OpenAPI should be checked against the agreed examples. Generation must not overwrite teammate edits or unrelated documentation.

See [collaboration rules](../COLLABORATION.md#api-and-database-contracts-come-first).
