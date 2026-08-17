from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SUPPLYMIND_", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./supplymind.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-change-me-please-change-me"
    credential_key: str = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    sql_timeout_seconds: int = 15
    sql_max_rows: int = 500
    datasource_allowed_hosts: str = "localhost,127.0.0.1,demo-data"
    datasource_allowed_cidrs: str = "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    chat_base_url: str | None = None
    chat_model: str | None = None
    chat_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str = "http://localhost:5173/auth/callback"
    report_directory: str = "./data/reports"

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def datasource_host_list(self) -> set[str]:
        return {value.strip().lower() for value in self.datasource_allowed_hosts.split(",") if value.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
