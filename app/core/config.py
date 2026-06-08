from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/voyago.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    pricing_provider: str = "mock"
    travelpayouts_token: str | None = None
    travelpayouts_marker: str | None = None
    default_origin_iata: str = "MOW"
    serpapi_api_key: str | None = None
    makcorps_username: str | None = None
    makcorps_password: str | None = None
    makcorps_jwt: str | None = None
    makcorps_usd_to_rub: float = 95.0
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    app_name: str = "Voyago"
    api_v1_prefix: str = "/api/v1"
    reserve_percent: int = Field(default=10, ge=0, le=50)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    app_public_url: str = "http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
