from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CoolLink AI API"
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/coollink_ai"
    ai_provider: str = "mock"
    ai_timeout_seconds: int = Field(default=8, ge=1)
    ai_log_payload: bool = False
    ai_prompt_version: str = "v0.3-mock"
    openweathermap_api_key: str = ""
    internal_job_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
