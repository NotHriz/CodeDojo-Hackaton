"""Keep automated tests independent of the developer's local .env credentials."""

import pytest


@pytest.fixture(autouse=True)
def isolate_integration_environment(monkeypatch):
    for name, value in {
        "APP_ENV": "test", "DEMO_DATA_ENABLED": "false",
        "AI_API_KEY": "", "SUPABASE_URL": "", "DATABASE_URL": "",
        "SUPABASE_SERVICE_ROLE_KEY": "", "AI_MODEL": "deepseek-flash",
        "COMMUNITY_POLICY_VERSION": "disabled",
    }.items():
        monkeypatch.setenv(name, value)
