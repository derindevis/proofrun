"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PROOFRUN_",
        extra="ignore",
    )

    app_name: str = "ProofRun"
    environment: str = "development"
    debug: bool = False

    nebius_token_factory_url: str | None = None
    nebius_token_factory_api_key: str | None = Field(default=None, repr=False)
    nebius_api_key: str | None = Field(default=None, repr=False)
    nebius_base_url: str = "https://api.tokenfactory.us-central1.nebius.com/v1/"
    nebius_model: str = "nvidia/nvidia-nemotron-3-nano-30b-a3b"

    langsmith_tracing: bool = False
    langsmith_endpoint: str | None = None
    langsmith_api_key: str | None = Field(default=None, repr=False)
    langsmith_project: str = "proofrun"

    @model_validator(mode="after")
    def apply_legacy_nebius_key(self) -> "Settings":
        """Temporarily support the initial Token Factory setting name."""
        if self.nebius_api_key is None:
            self.nebius_api_key = self.nebius_token_factory_api_key
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for application use."""
    return Settings()
