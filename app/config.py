from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    litellm_base_url: str = "http://127.0.0.1:4000"
    upstream_timeout_s: float = 60.0
    pii_masking: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
