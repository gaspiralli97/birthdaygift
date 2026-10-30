"""Reading settings out of an env file, including the disabled ones."""

from __future__ import annotations

import pytest

from birthdaygift import config


@pytest.fixture(autouse=True)
def _fresh_settings() -> None:
    """Settings are a cached singleton; each case sets its own environment."""
    config.get_settings.cache_clear()


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_owner_id_disables_reporting(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty value is how an env file says "off", and must not fail the boot.

    Both `.env.example` and the provisioning script ship TELEGRAM_OWNER_ID
    empty, so this is the documented path rather than an edge case.
    """
    monkeypatch.setenv("TELEGRAM_OWNER_ID", blank)
    assert config.Settings().telegram_owner_id == 0


def test_owner_id_is_still_read_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "123456789")
    assert config.Settings().telegram_owner_id == 123456789


def test_a_real_malformed_owner_id_is_still_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank is a decision; "nope" is a typo, and a typo should fail loudly."""
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "nope")
    with pytest.raises(ValueError, match="telegram_owner_id"):
        config.Settings()


def test_site_url_loses_its_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITE_URL", "https://example.test/")
    assert config.Settings().card_url("abc") == "https://example.test/c/abc"
