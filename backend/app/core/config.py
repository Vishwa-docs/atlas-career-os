"""Application settings, loaded from environment variables.

All configuration is environment-driven (12-factor). Never commit secrets;
see ``.env.example`` for the contract. Settings are cached so the object is
constructed once per process.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- App ---
    app_name: str = "Atlas — Career OS"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- Security ---
    secret_key: str = Field(
        default="dev-insecure-change-me-in-production-please-32+chars",
        min_length=16,
        description="HMAC signing key for JWTs. MUST be overridden in prod.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # --- Database ---
    database_url: str = "postgresql+asyncpg://atlas:atlas@localhost:5432/atlas"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # --- Redis (ARQ + caching + pub/sub) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-10-21"
    embedding_dimensions: int = 1536
    llm_request_timeout_seconds: float = 60.0
    llm_max_retries: int = 3
    # When false (or creds absent) the platform uses the deterministic MockLLMClient.
    use_mock_llm: bool = True
    # In live mode, keep embeddings on the deterministic embedder unless the Azure
    # resource has an embeddings deployment AND the corpus was embedded with it.
    # (The seed embeds with the deterministic embedder, so query vectors must match.)
    use_azure_embeddings: bool = False

    # --- CORS ---
    # NoDecode: let our validator split a comma-separated string itself, instead
    # of pydantic-settings trying to JSON-decode the env value.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Rate limiting ---
    rate_limit_default: str = "200/minute"
    rate_limit_auth: str = "20/minute"
    rate_limit_ai: str = "30/minute"

    # --- Misc ---
    default_locale: Literal["en", "ms", "zh"] = "en"
    project_root_url: str = "http://localhost:8000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def azure_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def use_live_llm(self) -> bool:
        """Use the real Azure client only when explicitly enabled AND configured."""
        return not self.use_mock_llm and self.azure_configured

    # Pydantic-asyncpg DSN sanity (kept permissive for SQLite-free local/test).
    @field_validator("database_url")
    @classmethod
    def _validate_db(cls, v: str) -> str:
        if v and "+asyncpg" not in v and v.startswith("postgresql"):
            # Force the async driver so the engine is always async.
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
