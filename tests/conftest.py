"""Shared fixtures.

Every test gets its own SQLite file and its own settings. Both the settings
object and the engine are cached module-level singletons, so the caches have
to be cleared after the environment changes or the first test's database
would be used by all of them.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from birthdaygift import config, db
from birthdaygift.models import Card
from birthdaygift.schemas import CardCreate

SECRET = "test-webhook-secret"


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[config.Settings]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SITE_URL", "https://example.test")
    monkeypatch.setenv("CARD_TTL_DAYS", "5")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    config.get_settings.cache_clear()
    db.reset_state()
    db.create_all()
    yield config.get_settings()
    config.get_settings.cache_clear()
    db.reset_state()


@pytest.fixture
def session(settings: config.Settings) -> Iterator[object]:
    with db.session_scope() as scoped:
        yield scoped


@pytest.fixture
def client(settings: config.Settings) -> Iterator[TestClient]:
    from birthdaygift.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def make_card(settings: config.Settings):  # type: ignore[no-untyped-def]
    """Build a stored card, overriding any field."""

    def _make(**overrides: object) -> Card:
        from birthdaygift import cards

        paragraphs = overrides.pop("paragraphs", ["Birinchi.", "Ikkinchi."])
        source = overrides.pop("source", "self")
        payload = CardCreate.model_validate(
            {
                "name": "Sahobiddin",
                "age": 30,
                "relation": "classmate",
                "field": "math",
                "lang": "uz",
                "theme": "qora",
                "from_name": "Ismoil",
                **overrides,
            }
        )
        with db.session_scope() as scoped:
            return cards.create(scoped, payload, paragraphs, source)  # type: ignore[arg-type]

    return _make


@pytest.fixture
def expire():  # type: ignore[no-untyped-def]
    """Push a card's expiry into the past."""

    def _expire(card_id: str) -> None:
        with db.session_scope() as scoped:
            row = scoped.get(Card, card_id)
            assert row is not None
            row.expires_at = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(seconds=1)

    return _expire
