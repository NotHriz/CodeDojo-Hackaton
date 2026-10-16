"""Behavioral checks for configuration, HTTP boundaries, and process liveness."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings():
    # Explicit values keep tests independent of local credentials/configuration.
    return Settings(
        _env_file=None,
        app_env="test",
        allowed_origins="http://localhost:5173",
        database_url="",
        supabase_url="",
        supabase_service_role_key="",
        ai_api_key="",
        ai_model="deepseek-flash",
    )


def test_liveness_without_provider_credentials(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "akses-campus-api"}
        assert client.get("/api/docs").status_code == 200
        assert "/api/health" in client.get("/api/openapi.json").json()["paths"]


def test_unimplemented_endpoint_is_not_fake_success(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/not-implemented")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


def test_wrong_method_retains_allow_header(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/health")
        assert response.status_code == 405
        assert response.json()["error"]["code"] == "method_not_allowed"
        assert "GET" in response.headers["allow"]


def test_validation_does_not_echo_invalid_input(settings):
    api = create_app(settings)

    @api.get("/test-number")
    def number(value: int):
        return {"value": value}

    with TestClient(api) as client:
        response = client.get("/test-number", params={"value": "sensitive-value"})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert "sensitive-value" not in response.text


def test_unexpected_failure_is_sanitized_and_has_cors(settings):
    api = create_app(settings)

    @api.get("/test-failure")
    def failure():
        raise RuntimeError("private-provider-credential")

    with TestClient(api) as client:
        response = client.get(
            "/test-failure", headers={"Origin": "http://localhost:5173"}
        )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
        assert "private-provider-credential" not in response.text
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_only_allows_configured_origin(settings):
    with TestClient(create_app(settings)) as client:
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
        allowed = client.options("/api/reports", headers=headers)
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == headers["Origin"]
        headers["Origin"] = "https://untrusted.example"
        denied = client.options("/api/reports", headers=headers)
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://app.example/path",
        "https://user:pass@app.example",
        "ftp://app.example",
        "https://app.example:bad",
    ],
)
def test_invalid_origin_configuration_is_rejected(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_origins=origin)


def test_multiple_origins_and_environment_override(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("AI_MODEL=from-file\n", encoding="utf-8")
    monkeypatch.setenv("AI_MODEL", "from-environment")
    settings = Settings(
        _env_file=env_file,
        allowed_origins="https://app.example, http://localhost:5173,https://app.example",
    )
    assert settings.ai_model == "from-environment"
    assert settings.cors_origins == ["https://app.example", "http://localhost:5173"]


def test_secrets_are_redacted_from_settings_representation():
    settings = Settings(
        _env_file=None,
        database_url="private-database-credential",
        ai_api_key="private-ai-credential",
        supabase_service_role_key="private-storage-credential",
    )
    assert "private-database-credential" not in repr(settings)
    assert "private-ai-credential" not in repr(settings)
    assert "private-storage-credential" not in repr(settings)
