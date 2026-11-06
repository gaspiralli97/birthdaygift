"""The bot's inline keyboards.

Each one is built by looking up every key of a set at once, so a single
untranslated key takes out the whole step rather than one button. That is how
the theme rename shipped broken: `themes.py` moved to qora/vino/qaymoq, the
translation files kept midnight/paper/neon, and the bot got as far as asking
for a language before raising KeyError on the next message.
"""

from __future__ import annotations

import pytest

from birthdaygift import bot
from birthdaygift.facts import WORK_FIELDS
from birthdaygift.i18n import LANGUAGES, RELATIONS, Strings, strings
from birthdaygift.themes import THEME_KEYS


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_keyboard_builds_in_every_language(lang: str) -> None:
    builders = (
        bot._theme_keyboard,
        bot._mode_keyboard,
        bot._relation_keyboard,
        bot._field_keyboard,
    )
    for build in builders:
        markup = build(lang)
        assert markup.inline_keyboard, f"{build.__name__} produced no buttons for {lang}"


def test_the_language_keyboard_offers_every_language() -> None:
    buttons = [b for row in bot._lang_keyboard().inline_keyboard for b in row]
    assert {b.callback_data for b in buttons} == {f"lang:{lang}" for lang in LANGUAGES}


@pytest.mark.parametrize("lang", LANGUAGES)
@pytest.mark.parametrize(
    ("section", "keys", "prefix"),
    [
        ("themes", THEME_KEYS, "theme"),
        ("relations", RELATIONS, "rel"),
        ("fields", WORK_FIELDS, "field"),
    ],
)
def test_every_choice_is_offered_and_labelled(
    lang: str, section: str, keys: tuple[str, ...], prefix: str
) -> None:
    """The copy covers exactly the keys the application has, no more or fewer.

    A missing key would crash the keyboard; a surplus one would be a button
    the card schema then rejects.
    """
    labels = getattr(strings(lang), section)
    assert set(labels) == set(keys)
    assert all(label.strip() for label in labels.values())


def test_a_stale_theme_key_fails_to_load() -> None:
    """The guarantee the README claims: bad copy fails validation, not a render.

    Rebuilt from a real language file with the pre-rename key put back, which
    is exactly the file that shipped.
    """
    raw = strings("uz").model_dump()
    raw["themes"] = {"midnight": "Tungi osmon", "paper": "Qog‘oz", "neon": "Neon"}
    with pytest.raises(ValueError):
        Strings.model_validate(raw)


def test_dropping_one_theme_label_also_fails() -> None:
    """The other half: a key that exists but was never translated."""
    raw = strings("uz").model_dump()
    raw["themes"].pop("vino")
    with pytest.raises(ValueError, match="themes has no label"):
        Strings.model_validate(raw)
