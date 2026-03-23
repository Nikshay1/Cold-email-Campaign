from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://cortexa:cortexa_secret@localhost:5432/cortexa_db"
    postgres_user: str = "cortexa"
    postgres_password: str = "cortexa_secret"
    postgres_db: str = "cortexa_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "dev_secret_key_change_me"
    environment: Literal["development", "production"] = "development"

    # Groq CI
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Hunter.io
    hunter_io_api_key: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Slack
    slack_webhook_url: str = ""
    slack_channel: str = "#vc-replies"

    # Notifications
    founder_email: str = "nikshay@cortexalabs.io"
    sendgrid_api_key: str = ""

    # Sending defaults
    max_sends_per_inbox_per_day: int = 30
    warmup_ratio: float = 0.35
    send_hour_min: int = 7
    send_hour_max: int = 17
    jitter_min_seconds: int = 60
    jitter_max_seconds: int = 480

    # Company
    company_name: str = "Cortexa Labs"
    company_address: str = "New Delhi, India"
    unsubscribe_base_url: str = "http://localhost:8000/unsubscribe"

    @property
    def cold_limit_per_inbox(self) -> int:
        return int(self.max_sends_per_inbox_per_day * (1 - self.warmup_ratio))

    @property
    def mock_mode(self) -> bool:
        """True when API keys are missing — uses mock responses."""
        return not self.groq_api_key or self.groq_api_key.startswith("gsk...")


@lru_cache
def get_settings() -> Settings:
    return Settings()
