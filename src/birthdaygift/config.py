"""Application settings, read once from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    #: The Claude Code CLI, which authenticates with the operator's own
    #: subscription rather than a metered API key.
    claude_bin: str = "claude"
    claude_model: str = "sonnet"
    letter_min_words: int = 60
    letter_max_words: int = 110

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    #: Where both usage reports are delivered. Empty disables reporting.
    telegram_owner_id: int = 0
    #: Cards per digest. The weekly report covers whatever is left over.
    report_every: int = 10

    #: Every letter is a CLI session drawn from one subscription, so the bot
    #: caps what a single person - and everyone together - can spend in a day.
    rate_per_user_per_day: int = Field(default=5, ge=1)
    rate_global_per_day: int = Field(default=60, ge=1)

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
