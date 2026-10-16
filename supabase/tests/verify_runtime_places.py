"""Exercise configured runtime reads against the runner's disposable database."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from fastapi.testclient import TestClient
from sqlalchemy import event
from app.config import Settings
from app.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    options = dict(_env_file=None, app_env="test", ai_api_key="", supabase_url="",
                   demo_data_enabled=True)
    url = f"postgresql://postgres@127.0.0.1:{args.port}/postgres"
    # Recreate the application to prove reads survive process-local state loss.
    for _ in range(2):
        app = create_app(Settings(database_url=url, **options))
        engine = app.state.place_repository.database.engine

        @event.listens_for(engine, "connect")
        def service_role(connection, _):
            with connection.cursor() as cursor:
                cursor.execute("SET ROLE service_role")
            connection.commit()

        with TestClient(app) as client:
            query = {"campus_id": "seed-test-campus"}
            response = client.get("/api/places", params=query)
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["data_mode"] == "live" and result["total"] == 1
            assert result["items"][0]["id"] == "seed-test-building"
            detail = client.get("/api/places/seed-test-building")
            assert detail.status_code == 200, detail.text
            place = detail.json()
            assert not place["is_demo"]
            assert place["facilities"]["step_free_entrance"] == "unknown"
            assert place["observations"][0]["observed_at"] is None
            assert place["active_warnings"][0]["description"] == "Fictional preserved report"
            assert client.get("/api/places", params={**query, "step_free_entrance": True}).json()["total"] == 0
            assert client.get("/api/places", params={"campus_id": "missing"}).json()["total"] == 0
            paged = client.get("/api/places", params={**query, "offset": 1}).json()
            assert paged["total"] == 1 and paged["items"] == []
            for missing in ("missing", "seed-test-building' OR '1'='1"):
                assert client.get(f"/api/places/{missing}").status_code == 404
            assert client.get("/api/reports", params={"place_id": place["id"]}).status_code == 503
            assert engine.pool.checkedout() == 0, "Request sessions must release connections"
    broken = create_app(Settings(database_url="postgresql://postgres:private-test-secret@127.0.0.1:1/postgres", **options))
    with TestClient(broken) as client:
        response = client.get("/api/places")
        assert response.status_code == 500
        assert response.json() == {"error": {"code": "internal_error", "message": "The server could not complete the request."}}
    print("Runtime integration passed: service-role PostgreSQL -> configured repository -> HTTP list/details, persistence, sessions and explicit failures.")


if __name__ == "__main__":
    main()
