from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ANNEX API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]
    max_upload_size_mb: int = 10

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_media_bucket: str = "annex-media"

    openai_api_key: str = ""
    openai_ocr_model: str = "gpt-4o-mini"
    openai_analysis_model: str = "gpt-4o-mini"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
