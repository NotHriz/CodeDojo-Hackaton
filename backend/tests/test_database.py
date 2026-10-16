"""Connection configuration and precedence; no external database needed."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.services.postgres_places import PostgresPlaceRepository


@pytest.mark.parametrize("url", ["sqlite:///data.db", "not a URL", "mysql://user:secret@host/db"])
def test_invalid_database_urls_are_sanitized(url):
    with pytest.raises(ValueError, match="PostgreSQL connection URL") as error:
        Database(url)
    assert "secret" not in str(error.value)


def test_configured_database_takes_precedence_without_import_time_connection():
    with patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("Must remain lazy")):
        app = create_app(Settings(_env_file=None, database_url="postgresql://user:secret@localhost/db",
                                  demo_data_enabled=True))
        assert isinstance(app.state.place_repository, PostgresPlaceRepository)
        assert not app.state.demo_mode
    app.state.place_repository.database.close()


def test_injected_repository_precedes_database_configuration():
    class Repository:
        def list_places(self, campus_id):
            return []

    with TestClient(create_app(Settings(_env_file=None, database_url="not a URL"),
                              place_repository=Repository())) as client:
        assert client.get("/api/places").json()["total"] == 0


def test_owned_engine_is_disposed_at_shutdown():
    app = create_app(Settings(_env_file=None, database_url="postgresql://user:secret@localhost/db"))
    database = app.state.place_repository.database
    with patch.object(database, "close") as close:
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200
        close.assert_called_once()
