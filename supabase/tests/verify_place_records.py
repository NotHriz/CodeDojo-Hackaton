"""Validate disposable PostgreSQL records through real backend DTO/search code."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.schemas import ActiveWarning, Entrance, FacilityObservation, PlaceDetail
from app.services.places import search_places


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True)
    parser.add_argument("--port", required=True)
    args = parser.parse_args()
    command = [str(Path(args.pg_bin) / "psql.exe"), "-X", "-h", "127.0.0.1", "-p", args.port,
               "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-qAt"]
    # The seed integration checks intentionally left one fictional building and
    # report inside this disposable cluster. Read with application-role grants.
    result = subprocess.run(command, input="SET ROLE service_role; SELECT record FROM public.place_detail_records;",
                            encoding="utf-8", capture_output=True,
                            env={**os.environ, "PGCLIENTENCODING": "UTF8"})
    assert result.returncode == 0, result.stderr
    raw_records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(raw_records) == 1, "Expected the isolated seed fixture only"
    for raw in raw_records:
        assert set(raw) == set(PlaceDetail.model_fields), "Unexpected place fields"
        for rows, model in ((raw["entrances"], Entrance), (raw["observations"], FacilityObservation),
                            (raw["active_warnings"], ActiveWarning)):
            assert all(set(row) == set(model.model_fields) for row in rows), "Unexpected nested/private fields"
    places = [PlaceDetail.model_validate(raw) for raw in raw_records]
    place = places[0]
    assert place.id == "seed-test-building" and place.campus_id == "seed-test-campus"
    assert place.facilities.step_free_entrance == "unknown"
    assert place.entrances[0].coordinates is None and place.observations[0].observed_at is None
    assert len(place.active_warnings) == 1 and place.active_warnings[0].status == "unverified"
    assert place.active_warnings[0].observed_at.tzinfo is not None
    assert [str(url) for url in place.observations[0].evidence_urls] == [
        "https://example.com/first.jpg", "https://example.com/second.jpg"]

    class FixtureRepository:
        # Test-only bridge for records actually read above, not a runtime adapter.
        def list_places(self, campus_id):
            return places  # Deliberately over-fetch to exercise backend campus defense.

        def get_place(self, place_id):
            return next((row for row in places if row.id == place_id), None)

    repository = FixtureRepository()
    query = dict(campus_id=place.campus_id, q="O'Brien", category="STUDY", step_free_entrance=False,
                 accessible_toilet=False, designated_parking=False, limit=20, offset=0)
    found = search_places(repository, **query)
    assert found.total == 1 and len(found.items[0].active_warnings) == 1
    assert search_places(repository, **{**query, "step_free_entrance": True}).total == 0
    assert search_places(repository, **{**query, "campus_id": "other-campus"}).total == 0
    paged = search_places(repository, **{**query, "offset": 1})
    assert paged.total == 1 and paged.items == []
    assert repository.get_place("missing") is None
    print("Place-record integration passed: PostgreSQL -> PlaceDetail -> backend filtering/pagination with warnings and privacy.")


if __name__ == "__main__":
    main()
