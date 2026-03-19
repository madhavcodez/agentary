from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        extra="ignore",
    )

    database_url: str = "postgresql://soundscore:soundscore@localhost:5432/secretairy"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_webhook_base_url: str = ""
    exa_api_key: str = ""
    openclaw_url: str = "http://localhost:3000"
    google_client_id: str = ""
    google_client_secret: str = ""
    app_env: str = "dev"
    secret_key: str = "dev-secret-key-change-in-production"


settings = Settings()
