"""Application settings, read once from the environment."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TextProvider = Literal["template", "anthropic"]


class Settings(BaseSettings):
    """Every knob the service has. Secrets come from the environment only."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    site_url: str = "http://localhost:8000"
    database_path: Path = Path("./data/birthdaygift.db")
    card_ttl_days: int = Field(default=5, ge=1, le=365)

    text_provider: TextProvider = "template"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    rate_per_ip_per_day: int = Field(default=5, ge=1)
    rate_per_telegram_user_per_day: int = Field(default=3, ge=1)
    rate_global_per_day: int = Field(default=200, ge=1)

    @field_validator("site_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def bot_enabled(self) -> bool:
        """The bot needs both halves: a token to call out, a secret to be called."""
        return bool(self.telegram_bot_token and self.telegram_webhook_secret)

    def card_url(self, card_id: str) -> str:
        return f"{self.site_url}/c/{card_id}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
