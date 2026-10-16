"""Environment configuration with optional integration credentials."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    allowed_origins: str = "http://localhost:5173"
    database_url: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    ai_api_key: SecretStr = SecretStr("")
    ai_model: str = "deepseek-flash"

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        for origin in origins:
            try:
                parts = urlsplit(origin)
                port = parts.port
            except ValueError:
                raise ValueError("ALLOWED_ORIGINS must contain valid HTTP(S) origins.")
            if (
                parts.scheme not in {"http", "https"}
                or not parts.hostname
                or "*" in origin
                or parts.username is not None
                or parts.password is not None
                or parts.path
                or parts.query
                or parts.fragment
                or (port is not None and port == 0)
            ):
                raise ValueError(
                    "Use explicit HTTP(S) origins without paths, wildcards, or credentials."
                )
        return ",".join(dict.fromkeys(origins))

    @property
    def cors_origins(self) -> list[str]:
        return self.allowed_origins.split(",") if self.allowed_origins else []
