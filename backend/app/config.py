from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/dealtwin.db"
    hindsight_base_url: str = "http://localhost:8888"
    hindsight_api_key: str | None = None
    hindsight_bank_id: str = "dealtwin-demo"
    hindsight_timeout_seconds: float = 45.0
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

