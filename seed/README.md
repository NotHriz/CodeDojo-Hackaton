# Campus seed data

Owner: teammate 3, using observations collected by the whole team.

`import_places.py` validates collection JSON and emits a reviewed, insert-only PostgreSQL import. It never connects to a database or reads credentials. No real campus dataset is included. The tests contain explicitly fictional fixtures only.

Start with approximately 10–15 IIUM Gombak building records. The input maps to the accepted campus/building/evidence schema. Record campus/building identity, coordinates, entrance location, facility yes/no/unknown values, evidence references, and observation dates.

## Validate and prepare

Use the existing backend Python environment and pinned dependencies; no additional packages are needed. From the repository root:

```powershell
backend/.venv/Scripts/python.exe seed/import_places.py collected-records.json
backend/.venv/Scripts/python.exe seed/import_places.py collected-records.json --sql | Set-Content -Encoding UTF8 reviewed-import.sql
```

The default command reports validation counts and makes no writes. `--sql` emits a transaction but does not execute it. Review the generated file and the intended database connection before the database owner applies it using `psql -X -v ON_ERROR_STOP=1 -f reviewed-import.sql`. Shared application is a separate task; this implementation has not applied records to Supabase. Keep private data and credentials out of both input and generated SQL.

## Collection format

The root object has required `campuses` and `buildings` arrays and optional `entrances` and `observations` arrays. An empty structural template is:

```json
{"campuses": [], "buildings": [], "entrances": [], "observations": []}
```

| Collection | Fields |
| --- | --- |
| `campuses` | Required opaque string `id` (1–128 characters) and `name` (1–200) |
| `buildings` | Required `id`, `campus_id`, `name`, `category` (1–64), `coordinates` with latitude/longitude; optional nullable `description` and `facilities` |
| `entrances` | Required stable UUID `id`, `building_id`, `description`; optional nullable coordinate pair and `photo_urls` |
| `observations` | Required stable UUID `id`, `building_id`, `facility`, `value`; optional nullable `observed_at`, `source`, `notes`, and `evidence_urls` |

Coordinate, facility, timestamp and HTTP(S) URL definitions reuse the backend DTOs. Facilities are only `step_free_entrance`, `accessible_toilet`, `designated_parking`; values are `yes`, `no`, `unknown`. Omitted building facilities remain unknown, omitted entrance coordinates and observation dates remain null, and no evidence dates are invented. Non-null dates need an explicit timezone.

Use stable collected identities, not new UUIDs on every run. IDs must be unique within each collection; every building's campus and every entrance/observation's building must be declared in the same batch. Unknown fields, private fields, runtime `is_demo`/warning data, duplicate JSON keys, invalid references, nonfinite numbers and NUL are rejected. This validator checks structure, not whether an observation is true or permission to publish a photo exists.

## Repeatability and conflicts

The SQL targets only campuses, buildings, entrances, facility observations, entrance photos, and observation evidence. Each transaction inserts missing rows; identical existing rows are accepted; conflicting values for an existing identity raise an error and roll back the whole batch. It never updates or deletes existing records. Corrections to previously imported facts require a separately reviewed change; new observations use new stable identities.

Photos/evidence use their array position as identity within their parent. Reordering or replacing a stored reference conflicts. Omitted rows/references remain stored; omission is not deletion. Ingestion timestamps are database defaults only for newly inserted observations and are not compared to user observation time. Current building facilities are imported as explicitly provided; no rule derives them from the observation list.

Reports, votes, history, contributor restrictions and existing evidence are not replaced or erased. The importer is not a runtime fixture mode, a backend outage fallback, a Storage uploader, or an API adapter. No fictional campus records are supplied for a real deployment.

## Checks

```powershell
backend/.venv/Scripts/python.exe seed/tests/test_import_places.py
powershell -NoProfile -ExecutionPolicy Bypass -File supabase/tests/run-local.ps1
```

The first command runs ten unit/CLI checks. The second runs all ten SQL suites, repeats those checks, and executes generated imports in the runner's disposable PostgreSQL cluster. It verifies repeat imports, exact text/escaping, null/unknown preservation, retained reports, full-batch rollback, and unchanged evidence after conflict. Seed fixtures are committed only inside the disposable test cluster, whose server stops afterward; no shared database is used. The runner now needs `backend/.venv` in addition to PostgreSQL 18.

- Keep real observations separate from clearly labelled fictional demo records.
- Do not invent accessibility, evidence, or check dates.
- Keep credentials, private contributor reputation, and personal account data out of seed files.
- Use permitted images without identifiable people or sensitive information.
- Make future imports repeatable without duplicating buildings or erasing community reports.
- Clearly label any demo accounts/votes; seeded consensus does not validate the trust algorithm.

See [onboarding](../onboarding.md) for facility definitions and data integrity rules.
