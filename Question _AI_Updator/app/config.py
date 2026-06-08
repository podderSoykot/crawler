from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Question AI Updator"
    database_url: str = "sqlite:///./qa_updator.db"
    redis_url: str = "redis://localhost:6379/0"

    tavily_api_key: str = ""
    serpapi_api_key: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    max_search_results: int = 8
    max_crawl_pages: int = 5
    crawl_timeout_seconds: int = 20
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
