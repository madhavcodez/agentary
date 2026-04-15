from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        extra="ignore",
    )

    database_url: str = "postgresql://agentary:agentary@localhost:5432/agentary"
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

    # Data Source API Keys (optional — connectors skip if missing)
    google_places_api_key: str = ""
    zillow_api_key: str = ""
    yelp_api_key: str = ""
    crunchbase_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    app_env: str = "dev"
    secret_key: str = ""

    # JWT / Auth
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # Email (Resend)
    resend_api_key: str = ""
    resend_from_email: str = ""
    resend_webhook_secret: str = ""

    # App base URL (for shareable links)
    base_url: str = "http://localhost:3000"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # STORM (Stanford research methodology) — see backend/docs/STORM.md
    agentary_storm_enabled: bool = False
    storm_max_perspectives: int = 4
    storm_max_questions: int = 3
    storm_max_sections: int = 6
    storm_max_refinement: int = 2
    storm_evidence_threshold: float = 0.55
    storm_max_flash_calls: int = 10
    storm_max_pro_calls: int = 8

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_set(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set and at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if not v or v == "dev-secret-key-change-in-production" or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be set and at least 32 characters."
            )
        return v


settings = Settings()
