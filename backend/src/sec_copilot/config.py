from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "SEC Filing Intelligence Copilot"
    database_url: str = "postgresql+psycopg://sec_copilot:sec_copilot@localhost:5432/sec_copilot"
    qdrant_url: str = "http://localhost:6333"
    sec_user_agent: str = "SEC Filing Intelligence Copilot contact@example.com"
    sec_requests_per_second: int = 5
    sec_raw_data_dir: str = "data/raw/sec"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
