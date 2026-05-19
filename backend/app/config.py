from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://localhost/agentcogs"
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "dev-secret-change-me"
    cors_origins: str = "https://app.agentcogs.dev,http://localhost:5173"
    app_base_url: str = "https://app.agentcogs.dev"

    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_connect_client_id: str = ""
    stripe_meter_event_name: str = "agentcogs_ai_usage"

    resend_api_key: str = ""
    alert_from_email: str = "alerts@agentcogs.dev"

    environment: str = "development"

    demo_enabled: bool = False
    demo_workspace_email: str = "demo@agentcogs.dev"


settings = Settings()
