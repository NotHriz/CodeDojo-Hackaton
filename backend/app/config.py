"""Environment configuration with optional integration credentials."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    demo_data_enabled: bool = False
    allowed_origins: str = "http://localhost:5173"
    database_url: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    ai_api_key: SecretStr = SecretStr("")
    ai_model: str = "deepseek-flash"
    ai_timeout_seconds: float = Field(default=15, ge=1, le=30)
    ai_max_output_tokens: int = Field(default=600, ge=100, le=1200)
    chat_requests_per_minute: int = Field(default=5, ge=1, le=60)
    chat_requests_per_day: int = Field(default=100, ge=1, le=1000)

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: str) -> str:
        if not value:
            return value
        parts = urlsplit(value)
        if (
            not parts.hostname
            or parts.scheme not in {"https", "http"}
            or (parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"})
            or parts.username is not None
            or parts.password is not None
            or parts.path not in {"", "/"}
            or parts.query
            or parts.fragment
        ):
            raise ValueError("SUPABASE_URL must be an HTTPS project origin (local HTTP is development-only).")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_production_auth(self):
        if self.demo_data_enabled and self.app_env == "production":
            raise ValueError("Demo building data is not allowed in production.")
        if self.app_env == "production" and self.supabase_url.startswith("http:"):
            raise ValueError("Production Supabase authentication requires HTTPS.")
        return self

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
