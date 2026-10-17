"""Endpoint behavior using explicit test-only persistence, never runtime seed data."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import FacilityObservation, PlaceDetail
from app.services.auth import AuthenticatedUser, InvalidAccessToken
from app.services.postgres_places import ObservationIdempotencyConflict, ObservationTargetMissing


class TestPlaceRepository:
    __test__ = False

    def __init__(self, records):
        self.records = records

    def list_places(self, campus_id):
        # Deliberately over-fetch to exercise the service's campus boundary check.
        return self.records

    def get_place(self, place_id):
        return next((place for place in self.records if place.id == place_id), None)


def building(place_id, name, **changes):
    return PlaceDetail.model_validate(
        {
            "id": place_id,
            "campus_id": "iium-gombak",
            "name": name,
            "category": "study",
            "coordinates": {"latitude": 3.25, "longitude": 101.73},
            "is_demo": True,
            **changes,
        }
    )


@pytest.fixture
def client():
    settings = Settings(_env_file=None, allowed_origins="")
    records = [
        building(
            "b",
            "Beta study building",
            facilities={"step_free_entrance": "yes", "accessible_toilet": "yes"},
            active_warnings=[
                {
                    "report_id": "r1",
                    "description": "Ramp blocked",
                    "status": "unverified",
                    "observed_at": "2026-10-16T04:00:00Z",
                }
            ],
            entrances=[{"description": "East entrance"}],
            observations=[
                {
                    "facility": "step_free_entrance",
                    "value": "yes",
                    "source": "Test observation",
                    "observed_at": "2026-10-15T04:00:00Z",
                }
            ],
        ),
        building("a", "Alpha building", facilities={"step_free_entrance": "no"}),
        building("c", "Gamma building"),
        building("other", "Other campus", campus_id="other-campus"),
    ]
    with TestClient(
        create_app(settings, place_repository=TestPlaceRepository(records))
    ) as test_client:
        yield test_client


def test_default_list_is_sorted_and_campus_scoped(client):
    response = client.get("/api/places")
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == ["a", "b", "c"]
    assert body["total"] == 3
    assert "observations" not in body["items"][1]


def test_required_facility_excludes_no_and_unknown_but_keeps_warnings(client):
    response = client.get(
        "/api/places", params={"step_free_entrance": True, "accessible_toilet": True}
    )
    body = response.json()
    assert [item["id"] for item in body["items"]] == ["b"]
    assert body["items"][0]["active_warnings"][0]["status"] == "unverified"


def test_false_filter_means_no_requirement_not_inaccessible_only(client):
    assert client.get("/api/places?step_free_entrance=false").json()["total"] == 3


def test_no_matches_is_empty_not_relaxed_filters(client):
    response = client.get("/api/places?designated_parking=true")
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_search_category_and_pagination(client):
    response = client.get(
        "/api/places",
        params={"q": "  BUILDING  ", "category": "STUDY", "limit": 1, "offset": 1},
    )
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert body["items"][0]["id"] == "b"
    assert client.get("/api/places?offset=99").json()["items"] == []


def test_details_include_entrance_evidence_dates_and_unknowns(client):
    response = client.get("/api/places/b")
    assert response.status_code == 200
    body = response.json()
    assert body["entrances"][0]["description"] == "East entrance"
    assert body["observations"][0]["source"] == "Test observation"
    assert body["observations"][0]["observed_at"] is not None
    assert body["facilities"]["designated_parking"] == "unknown"
    assert client.get("/api/places/c").json()["observations"] == []


def test_missing_building_returns_404(client):
    response = client.get("/api/places/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=101", "offset=-1", "step_free_entrance=perhaps", "campus_id="],
)
def test_invalid_queries_return_422(client, query):
    response = client.get(f"/api/places?{query}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_missing_repository_is_explicit_503_and_liveness_still_works():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        for path in ("/api/places", "/api/places/b"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "service_unavailable"
        assert client.get("/api/health").status_code == 200


def test_repository_failure_does_not_become_empty_success():
    class BrokenRepository:
        def list_places(self, campus_id):
            raise RuntimeError("private-database-credential")

        def get_place(self, place_id):
            raise RuntimeError("private-database-credential")

    with TestClient(create_app(place_repository=BrokenRepository())) as client:
        for path in ("/api/places", "/api/places/b"):
            response = client.get(path)
            assert response.status_code == 500
            assert response.json()["error"]["code"] == "internal_error"
            assert "private-database-credential" not in response.text


class ObservationVerifier:
    def verify(self, token):
        try:
            return AuthenticatedUser(UUID(token))
        except ValueError:
            raise InvalidAccessToken() from None


class ObservationWriter(TestPlaceRepository):
    def __init__(self, records):
        super().__init__(records)
        self.keys = {}

    def create_observation(self, building_id, author_id, body, key, now):
        place = self.get_place(building_id)
        if place is None:
            raise ObservationTargetMissing()
        payload = body.model_dump_json()
        existing = self.keys.get((author_id, building_id, key))
        if existing is not None:
            if existing[0] != payload:
                raise ObservationIdempotencyConflict()
            return existing[1]
        updated = place.model_copy(update={"observations": [FacilityObservation(**body.model_dump())]})
        self.records = [updated if item.id == building_id else item for item in self.records]
        self.keys[(author_id, building_id, key)] = (payload, updated)
        return updated


def observation_app():
    settings = Settings(_env_file=None, supabase_url="")
    return create_app(settings, place_repository=ObservationWriter([building("b", "Beta study building")]), token_verifier=ObservationVerifier())


def observation_headers(key=None, user=None):
    return {"Authorization": "Bearer " + str(user or uuid4()), **({"Idempotency-Key": str(key)} if key else {})}


def valid_observation(**updates):
    return {"facility": "step_free_entrance", "value": "yes", "observed_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), "evidence_urls": [], **updates}


def test_observation_requires_authentication_and_idempotency_key():
    with TestClient(observation_app()) as client:
        assert client.post("/api/places/b/observations", json=valid_observation()).status_code == 401
        assert client.post("/api/places/b/observations", json=valid_observation(), headers=observation_headers()).status_code == 422


def test_observation_rejects_invalid_facility_and_future_date():
    with TestClient(observation_app()) as client:
        response = client.post("/api/places/b/observations", json=valid_observation(facility="lift"), headers=observation_headers(uuid4()))
        assert response.status_code == 422
        response = client.post("/api/places/b/observations", json=valid_observation(observed_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()), headers=observation_headers(uuid4()))
        assert response.status_code == 422


def test_observation_is_idempotent_and_conflicting_retry_is_rejected():
    key = uuid4()
    user = uuid4()
    with TestClient(observation_app()) as client:
        body = valid_observation()
        first = client.post("/api/places/b/observations", json=body, headers=observation_headers(key, user))
        second = client.post("/api/places/b/observations", json=body, headers=observation_headers(key, user))
        conflict = client.post("/api/places/b/observations", json=valid_observation(value="no"), headers=observation_headers(key, user))
        assert first.status_code == second.status_code == 201
        assert first.json() == second.json()
        assert conflict.status_code == 409


def test_observation_missing_building_returns_not_found():
    with TestClient(observation_app()) as client:
        response = client.post("/api/places/missing/observations", json=valid_observation(), headers=observation_headers(uuid4()))
        assert response.status_code == 404
