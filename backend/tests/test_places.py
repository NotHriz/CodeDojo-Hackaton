"""Endpoint behavior using explicit test-only persistence, never runtime seed data."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import PlaceDetail


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
