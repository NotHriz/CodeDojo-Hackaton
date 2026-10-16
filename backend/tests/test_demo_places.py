"""Explicit demo mode behavior; these tests never call real DeepSeek."""

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.demo_places import DemoPlaceRepository


class Provider:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def complete(self, messages, *, allow_tools):
        self.calls += 1
        assert "all building records are fictional" in messages[0]["content"]
        if self.fail:
            from app.services.chat import AIUnavailable
            raise AIUnavailable()
        if allow_tools:
            return {"tool_calls": [{"id": "call-demo", "type": "function", "function": {"name": "search_places", "arguments": '{"category":"study","step_free_entrance":true,"accessible_toilet":true}'}}]}
        return {"content": json.dumps({"answer": "These fictional study buildings have the requested demo facilities; the annex has an unverified fictional ramp warning.", "cited_place_ids": ["demo-study-hub", "demo-study-annex"]})}


def test_demo_is_opt_in_and_disconnected_default_stays_503():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/places").status_code == 503
    with TestClient(create_app(Settings(_env_file=None, demo_data_enabled=True))) as client:
        response = client.get("/api/places")
        assert response.status_code == 200
        assert response.json()["data_mode"] == "demo"
        assert response.json()["total"] == 3
        assert all(item["is_demo"] for item in response.json()["items"])
        assert "LOCAL DEMO" in client.get("/api/openapi.json").json()["info"]["description"]


def test_demo_filters_keep_warning_and_no_inspection_dates():
    with TestClient(create_app(Settings(_env_file=None, demo_data_enabled=True))) as client:
        result = client.get("/api/places?category=study&step_free_entrance=true&accessible_toilet=true").json()
        assert result["total"] == 2
        annex = next(item for item in result["items"] if item["id"] == "demo-study-annex")
        assert annex["active_warnings"][0]["status"] == "unverified"
        assert annex["active_warnings"][0]["observed_at"] is None
        detail = client.get("/api/places/demo-study-hub").json()
        assert all(item["observed_at"] is None for item in detail["observations"])


def test_demo_chat_uses_provider_and_explicit_labels():
    provider = Provider()
    with TestClient(create_app(Settings(_env_file=None, demo_data_enabled=True), chat_provider=provider)) as client:
        response = client.post("/api/chat", json={"message": "Find a study building with step-free access and an accessible toilet"})
        assert response.status_code == 200
        body = response.json()
        assert body["data_mode"] == "demo"
        assert body["answer"].startswith("LOCAL DEMO")
        assert all(item["is_demo"] for item in body["places"])
        assert len(body["sources"]) == 2
        assert provider.calls == 2


def test_demo_does_not_mock_or_hide_provider_failure():
    with TestClient(create_app(Settings(_env_file=None, demo_data_enabled=True), chat_provider=Provider(fail=True))) as client:
        response = client.post("/api/chat", json={"message": "Find a study building"})
        assert response.status_code == 503
        assert "answer" not in response.json()


def test_production_refuses_flag_and_explicit_demo_adapter():
    with pytest.raises(ValueError, match="not allowed in production"):
        Settings(_env_file=None, app_env="production", demo_data_enabled=True)
    with pytest.raises(ValueError, match="not allowed in production"):
        create_app(Settings(_env_file=None, app_env="production"), place_repository=DemoPlaceRepository())


def test_real_adapter_is_never_replaced_or_used_as_a_demo_fallback():
    class OfflineRepository:
        def list_places(self, campus_id):
            raise RuntimeError("Database offline")

    with TestClient(create_app(Settings(_env_file=None, demo_data_enabled=True), place_repository=OfflineRepository())) as client:
        assert client.get("/api/places").status_code == 500


def test_demo_cannot_mix_with_real_community_persistence():
    with pytest.raises(ValueError, match="community persistence"):
        create_app(Settings(_env_file=None, demo_data_enabled=True), community_repository=object())


def test_records_are_independent_copies_and_other_campuses_are_empty():
    repository = DemoPlaceRepository()
    record = repository.get_place("demo-study-hub")
    record.facilities.step_free_entrance = "no"
    assert repository.get_place("demo-study-hub").facilities.step_free_entrance == "yes"
    assert repository.get_place("missing") is None
    assert repository.list_places("other-campus") == []
