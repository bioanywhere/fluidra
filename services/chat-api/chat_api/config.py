from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime
    env: str = "dev"
    port: int = 8080
    log_level: str = "INFO"

    # Database — async driver for the app, sync driver for Alembic
    database_url: str = "postgresql+asyncpg://postgres:localdev@localhost:5432/assistant"
    database_url_sync: str = "postgresql://postgres:localdev@localhost:5432/assistant"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # GCP
    gcp_project_id: str = "fluidra-pool-asst-dev"
    gcp_region: str = "europe-west1"

    # AI
    vertex_location: str = "europe-west1"
    gemini_model_fast: str = "gemini-2.0-flash"
    gemini_model_deep: str = "gemini-2.0-pro"
    embedding_model: str = "text-embedding-005"

    # Safety
    safety_policy_version: str = "2025.06.0"
    kill_switch_flag: str = "assistant_enabled"
    max_turns_memory: int = 10

    # Admin (corpus administration). Empty => admin endpoints are disabled
    # (fail-closed). Set ADMIN_TOKEN on the service to enable the /admin page.
    admin_token: str = ""


settings = Settings()
