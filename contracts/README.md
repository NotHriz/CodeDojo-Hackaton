# Shared contracts

Editor: the user/backend owner. Affected frontend and database teammates review changes before implementation.

This directory holds future versioned API examples and shared interface decisions. **No finalized schemas or endpoint specifications exist here yet.** The planned endpoints in [onboarding](../onboarding.md#initial-api-contract) are the starting point.

Agree the first building list/details slice before three teammates implement incompatible shapes. For each slice, record:

1. Endpoint method/path, authentication, parameters, and example success/error JSON.
2. IDs, facility values, report statuses, nullability, and date formats.
3. Data fields owned by the database and public fields exposed by the backend.
4. Frontend behavior for loading, empty, partial, warning, and error states.
5. Contract version/change notes and which consumers must be updated.

Future FastAPI-generated OpenAPI should be checked against the agreed examples. Generation must not overwrite teammate edits or unrelated documentation.

See [collaboration rules](../COLLABORATION.md#api-and-database-contracts-come-first).
