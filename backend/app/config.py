from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./nexus.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 60 * 24
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    ai_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_embedding_model: str | None = None
    storage_path: str = "./data/uploads"
    max_external_text_chars: int = 20_000
    rate_limit_requests: int = Field(default=240, ge=1, le=100_000)
    rate_limit_auth_requests: int = Field(default=10, ge=1, le=10_000)
    rate_limit_intensive_requests: int = Field(default=30, ge=1, le=10_000)
    rate_limit_upload_requests: int = Field(default=20, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=86_400)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def validate_for_startup(self) -> None:
        if self.environment == "production":
            if self.secret_key == "development-only-change-me" or len(self.secret_key) < 32:
                raise RuntimeError("SECRET_KEY must be a random value of at least 32 characters")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise RuntimeError("Production requires PostgreSQL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
