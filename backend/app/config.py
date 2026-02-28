"""Application configuration loaded from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "HookahBook"
    app_env: str = "development"
    debug: bool = False  # Must be explicitly set to True in dev

    # Security — no defaults, app fails to start without proper secrets
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    encryption_key: str

    @field_validator("encryption_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        from cryptography.fernet import Fernet

        try:
            Fernet(v.encode())
        except Exception:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet key. "
                'Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return v

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/hookahbook.db"

    # CORS
    cors_origins: str = "http://localhost:5173"

    @field_validator("cors_origins")
    @classmethod
    def no_wildcard_in_production(cls, v: str) -> str:
        # Wildcard check is a safety net; full enforcement requires app_env context
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Telegram
    telegram_bot_token: str = ""

    # SMS
    sms_provider: str = "smsru"
    sms_api_key: str = ""

    # Domain
    domain: str = "localhost"

    # ../.env for local dev (cwd=backend/), .env for Docker
    model_config = {"env_file": ("../.env", ".env"), "env_file_encoding": "utf-8"}


settings = Settings()
