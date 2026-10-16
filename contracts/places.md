# Building discovery API — backend handoff v0.1

Status: implemented and tested in the backend on `feat/backend-places`. Frontend/database review is pending. This is a public API proposal, not a prescribed SQL schema. No campus records or persistence adapter are connected yet.

## Endpoints

Both endpoints are public and require no authentication.

### GET /api/places

| Query field | Default | Meaning |
| --- | --- | --- |
| `campus_id` | `iium-gombak` | Exact campus identifier, nonempty string, max 128 characters |
| `q` | Omitted | Case-insensitive substring of building name, trimmed, max 200 characters |
| `category` | Omitted | Trimmed, case-insensitive exact category, max 64 characters |
| `step_free_entrance` | `false` | `true` requires recorded `yes`; `false` adds no requirement |
| `accessible_toilet` | `false` | Same requirement semantics |
| `designated_parking` | `false` | Same requirement semantics |
| `limit` | `20` | Integer from 1 to 100 |
| `offset` | `0` | Nonnegative integer |

All requirements combine with AND. Unknown never satisfies a required facility. Filters never relax automatically. Sort by case-insensitive name, then ID. `total` counts matches before pagination. Blank/whitespace-only `q` or `category` adds no restriction. Unknown campuses/categories return zero results when an adapter is connected.

Example response with **fictional illustrative data**, not an inspected campus building:

```json
{
  "items": [
    {
      "id": "example-building",
      "campus_id": "iium-gombak",
      "name": "Example study building",
      "category": "study",
      "coordinates": {"latitude": 3.25, "longitude": 101.73},
      "facilities": {
        "step_free_entrance": "yes",
        "accessible_toilet": "yes",
        "designated_parking": "unknown"
      },
      "active_warnings": [
        {
          "report_id": "example-report",
          "description": "Example ramp obstruction",
          "status": "unverified",
          "observed_at": null
        }
      ],
      "is_demo": true
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

`items` contains summaries only, excluding entrance/evidence details. A matching building retains active warnings regardless of warning status; frontend and AI must display them. An actual zero-match result is `items: []`, `total: 0` with requested pagination.

### GET /api/places/{place_id}

Returns one summary's fields plus `description` (nullable), `entrances` (array), and `observations` (array). IDs are opaque case-sensitive strings, 1–128 characters, unique across campuses and suitable for a URL path segment. Do not assume a database ID type in frontend code. Categories are extensible strings; agree their initial vocabulary with the collection team.

Additional fields, illustrated with fictional data:

```json
{
  "description": "Example building details",
  "entrances": [
    {
      "description": "East entrance, ground floor",
      "coordinates": null,
      "photo_urls": []
    }
  ],
  "observations": [
    {
      "facility": "step_free_entrance",
      "value": "yes",
      "observed_at": null,
      "source": "Illustrative data only",
      "notes": null,
      "evidence_urls": []
    }
  ]
}
```

No missing time, source, coordinate, or evidence is fabricated. All non-null timestamps are timezone-aware ISO 8601 strings. Coordinates are latitude [-90, 90] and longitude [-180, 180]. Evidence/photo references are HTTP(S) URLs. An absent facility value defaults to `unknown`; default lists are empty.

Facility names: `step_free_entrance`, `accessible_toilet`, `designated_parking`. Values: `yes`, `no`, `unknown`. Active warning statuses: `unverified`, `community_corroborated`, `disputed`; resolved reports must not enter this active-only field. Private reliability, account secrets, and internal voting records are excluded from these DTOs.

## Errors and current integration status

Application errors use `{"error":{"code":"...","message":"..."}}`.

| Status | Code | Meaning |
| --- | --- | --- |
| 404 | `not_found` | Adapter connected, but building does not exist |
| 422 | `validation_error` | Invalid query/path input |
| 503 | `service_unavailable` | No building repository is connected |
| 500 | `internal_error` | Unexpected adapter/server failure; no exception details exposed |

Without an adapter, both building endpoints return 503. Dependency resolution can produce this 503 before malformed query input is validated. `/api/health` still returns process liveness. CORS/network/platform errors may be non-JSON. Frontend must display errors rather than treating them as an empty list or silently substituting mocks.

## Database teammate handoff

The backend-owned `app.services.places.PlaceRepository` protocol defines:

```python
def list_places(self, campus_id: str) -> Sequence[PlaceDetail]: ...
def get_place(self, place_id: str) -> PlaceDetail | None: ...
```

Implement an adapter over your owned models/session interface; agree its final location with the backend owner. Return validated `app.schemas.PlaceDetail` records mapped from your SQL schema. No table names, SQL types, or migration choices are imposed here.

- `list_places` returns the pilot campus dataset. The backend applies name/category/facility filtering and pagination, and defensively enforces campus ID. This is intentionally for the small pilot; move filtering/pagination into database queries when coverage grows.
- `get_place` returns the matching record or `None` for a genuine miss. Database failures must raise, not return `None` or an empty successful list.
- Aggregate current facility values using your agreed observation rules; defaults must remain unknown. Populate active warnings from actual unresolved reports, keeping reported and observed timestamps distinct.
- Own and close database sessions per operation/request; do not pass ORM objects with expired lazy relationships into response serialization.
- Return only public evidence URLs or appropriately scoped expiring links, never storage service credentials or private contributor records.

The backend owner will connect the adapter through `create_app(place_repository=adapter)` in the composition root after the database handoff. Only tests currently inject a test repository. No runtime mock, credentials, campus data, or migration has been added.

## Frontend teammate handoff

Use `/api/docs` or `/api/openapi.json` to inspect the implemented DTOs. Use `items` for map/list markers and fetch details when selecting a building. Preserve yes/no/unknown and display `active_warnings`. Both selection paths should use the same place ID. Coordinate any contract changes with the backend owner before implementation.
