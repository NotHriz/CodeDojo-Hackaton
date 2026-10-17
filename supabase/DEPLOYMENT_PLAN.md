# Database-owner migration and import plan

This is a prepared plan, not authorization to write to the shared project.

## Target inspection: 17 October 2026

The ignored backend configuration contains a non-local PostgreSQL URL. Its
credential-free target fingerprint is `efce16da98c9af3c`. The CLI's existing
`.temp/project-ref`, Auth project and database project identifiers match. Demo
data is disabled. Neither credentials nor local link files belong in Git.

The authorized read-only connection attempt, retried outside the network sandbox,
timed out. Shared migration history, PostgreSQL version, installed schema, actual
runtime grants and dataset counts are **unverified**. Do not interpret timeout as
an empty database or a password failure. No migration or import was attempted.

Resolve database network access/project availability and verify the connection
details copied from that project's dashboard. Do not guess another region or
reset the database. Then run from the repository root:

```powershell
backend/.venv/Scripts/python.exe supabase/inspect_target.py
```

The audit reads ignored Settings, uses a read-only transaction and prints no
credentials, user records, evidence URLs or driver exception details. Exit 0
means its inspected checks passed; 1 means configuration/connectivity/inspection
failed; 2 means connected but deployment review is required. Empty data is not a
working application. Inspection does not certify concurrency or real observations.

### Connectivity retry result

On 17 October the user requested a retry after checking network access. SQL connectivity now succeeds with `sslmode=require`; Psycopg confirms client TLS. The current target has PostgreSQL 17.11, zero application tables/views in `public`, and no `supabase_migrations.schema_migrations` table. All 21 expected relations are missing. HTTPS `buildings` also returns 404. Earlier REST counts are historical and do not describe the current target.

The host/port/database fingerprint above is not a unique project identifier for shared poolers. Confirm the actual project-qualified username and Auth origin before approval. All eleven local migrations are candidates for the initial deployment; none were applied by this task. Existing application permissions remain unverifiable until deployment. The configured admin credential is for review/migration, not the deployed runtime. No shared-write approval has been given.

## Migration review gate

The accepted sequence has eleven files, applied in this exact order:

1. `20261016000100_building_foundation.sql`
2. `20261016000200_place_evidence.sql`
3. `20261016000300_barrier_reports.sql`
4. `20261016000400_report_votes.sql`
5. `20261016000500_clearance_observations.sql`
6. `20261016000600_clearance_votes.sql`
7. `20261016000700_report_history.sql`
8. `20261017000100_contributor_state.sql`
9. `20261017000200_community_read_views.sql`
10. `20261017000300_place_detail_records.sql`
11. `20261017000400_community_records.sql`

The audit lists each local filename, version and SHA-256, pending/unrecognized
remote versions when history is readable, missing/extra relations, columns,
RLS/invoker security and effective browser/service grants. Review PostgreSQL 15+
support and grant drift. Owner/admin runtime connections are flagged; deployed
application access must be reviewed separately from migration-owner access.

If the history table is inaccessible, obtain a history read from the database
owner's migration connection before planning writes. If tables already exist
without matching history, or unexpected objects/versions suggest the alternate
`feat/database-foundation` schema, stop and reconcile with the owner. Never mark
versions applied merely to suppress an error, blindly merge conflicting schemas,
rewrite an applied file, or replay this sequence manually over existing tables.

After connectivity/history reconciliation, use the team's Supabase CLI and its
linked-project workflow. If the CLI requires initialization, create local config
with `supabase init`, preserve any existing config, and verify the intended link.
Run `supabase db push --linked --dry-run`; compare its pending filenames with the
audit. Present that concrete diff and the target fingerprint for shared-write
approval. **No such shared-write approval has been given for this task.**

Only after approval, the database owner runs `supabase db push --linked` using
the reviewed connection. Confirm transaction behavior and stop on the first
failure; keep applied files immutable. Rerun the audit and verify runtime reads.
Never run `tests/roles.sql`, local SQL test fixtures, reset, or seed test scripts
against the shared project. The stand-in roles are disposable-cluster fixtures.

## Data collection and insert-only import gate

No actual campus JSON/CSV dataset was found in `seed/` or `supabase/`. Start with
[collection-template.json](../seed/collection-template.json) and the field guide
in [seed/README.md](../seed/README.md). The template intentionally contains no
campus, building, coordinates, dates, photos or accessibility claims.

Collect stable building IDs and confirmed coordinates. Use `iium-gombak` for the
agreed pilot campus. Record the three agreed facility values as yes/no/unknown;
unknown checks and dates remain unknown/null. Source and public image permission
need human review. Do not use fictional unit-test records as real seed data.

Given a collected file, validate and generate its exact insert-only plan:

```powershell
backend/.venv/Scripts/python.exe seed/import_places.py collected-records.json
backend/.venv/Scripts/python.exe seed/import_places.py collected-records.json --sql |
    Set-Content -Encoding UTF8 supabase/reviewed-import.sql
```

Review identities, references and observations with the collection team, then
present the generated SQL, row counts, checksum and target for import approval.
The importer inserts only missing rows, accepts identical existing rows and rolls
back the whole batch on conflicting identities. It never updates/deletes prior
evidence, reports, votes or history. Apply the approved file with `psql -X -v
ON_ERROR_STOP=1 -f supabase/reviewed-import.sql` using the reviewed connection via
the existing credential manager/local environment, never a credential-bearing
command argument. Review corrections separately.

After approval/application, rerun the audit and check list/details through the
configured API, repeat after restarting the backend, and inspect public-field
exclusion. Record actual applied versions/data counts in DATABASE_HANDOFF.md.

## Access controls and evidence storage

The accepted schema keeps all fourteen application tables and seven invoker
views backend-only. Browser roles have no application-table/view privileges.
Service grants allow application record mutations, SELECT/INSERT audit events
and SELECT/INSERT/UPDATE contributor state. Private vote metadata never enters
the record views. Local suites verify these rules; shared rules remain unverified.

Evidence currently consists of approved HTTP(S) references. Photo upload is
deferred from this integration slice. No Storage bucket, upload policy or public
image permission is created here. If upload becomes an agreed requirement,
coordinate bucket visibility, ownership, MIME/size limits and read policy with
the backend upload API owner before applying any Storage configuration.
