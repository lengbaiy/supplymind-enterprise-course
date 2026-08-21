from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "development-only-change-me-please-change-me"
DEVELOPMENT_CREDENTIAL_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SUPPLYMIND_", extra="ignore")

    env: str = "development"
    auto_create_schema: bool = False
    database_url: str = "sqlite+aiosqlite:///./supplymind.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = DEVELOPMENT_JWT_SECRET
    credential_key: str = DEVELOPMENT_CREDENTIAL_KEY
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    sql_timeout_seconds: int = 15
    sql_max_rows: int = 500
    refresh_token_days: int = 14
    datasource_allowed_hosts: str = "localhost,127.0.0.1,demo-data,demo-postgres,demo-mysql,retail-postgres"
    datasource_allowed_cidrs: str = "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    chat_base_url: str | None = None
    chat_model: str | None = None
    chat_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_dimension: int = 1024
    ai_max_graph_steps: int = 12
    ai_max_tool_calls: int = 8
    ai_answer_model: str | None = None
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str = "http://localhost:5173/auth/callback"
    oidc_state_ttl_seconds: int = 300
    oidc_auto_provision: bool = False
    report_directory: str = "./data/reports"
    document_directory: str = "./data/documents"
    ingestion_mode: str = "eager"
    s3_endpoint: str | None = None
    s3_bucket: str = "supplymind"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    task_queued_timeout_seconds: int = 600
    task_running_timeout_seconds: int = 1800

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def datasource_host_list(self) -> set[str]:
        return {
            value.strip().lower()
            for value in self.datasource_allowed_hosts.split(",")
            if value.strip()
        }

    @property
    def is_development(self) -> bool:
        return self.env.lower() in {"development", "dev", "test"}

    def validate_trial_runtime(self) -> None:
        """Reject a trial deployment that accidentally uses development secrets."""
        if self.env.lower() != "trial":
            return
        invalid = []
        if len(self.jwt_secret) < 32 or self.jwt_secret == DEVELOPMENT_JWT_SECRET:
            invalid.append("SUPPLYMIND_JWT_SECRET")
        if self.credential_key == DEVELOPMENT_CREDENTIAL_KEY:
            invalid.append("SUPPLYMIND_CREDENTIAL_KEY")
        if not self.s3_endpoint or not self.s3_access_key or not self.s3_secret_key:
            invalid.append("SUPPLYMIND_S3_ENDPOINT/S3_ACCESS_KEY/S3_SECRET_KEY")
        if invalid:
            raise ValueError("trial runtime configuration is unsafe: " + ", ".join(invalid))


@lru_cache
def get_settings() -> Settings:
    return Settings()
