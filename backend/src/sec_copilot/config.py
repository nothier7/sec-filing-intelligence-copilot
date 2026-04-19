from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "SEC Filing Intelligence Copilot"
    database_url: str = "postgresql+psycopg://sec_copilot:sec_copilot@localhost:5432/sec_copilot"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "sec_filings"
    sec_user_agent: str = "SEC Filing Intelligence Copilot contact@example.com"
    sec_requests_per_second: int = 5
    sec_raw_data_dir: str = "data/raw/sec"
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_eval_model: str = "gpt-5-mini"
    openai_eval_max_output_tokens: int = 800
    openai_eval_reasoning_effort: str = "minimal"
    openai_eval_web_search_reasoning_effort: str = "low"
    openai_eval_web_search_context_size: str = "low"
    openai_eval_web_search_max_tool_calls: int = 3
    openai_eval_cache_dir: str = "evals/results/cache/openai"
    openai_eval_context_chars: int = 3500

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
