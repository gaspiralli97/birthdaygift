"""Phrases that sit next to a number.

The card puts a count in front of a noun in six places, and two of the four
languages inflect. Russian is the demanding one: three forms, and the rule
keys off the last two digits rather than the number itself.
"""

from __future__ import annotations

import pytest

from birthdaygift.i18n import LANGUAGES, Plural, plural_category, strings


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, "one"),
        (2, "few"),
        (4, "few"),
        (5, "many"),
        (11, "many"),  # 11 is not "one", even though it ends in 1
        (12, "many"),
        (14, "many"),
        (21, "one"),  # 21 is, because 121 reads like 1
        (22, "few"),
        (25, "many"),
        (100, "many"),
        (101, "one"),
        (111, "many"),
        (0, "many"),
    ],
)
def test_russian_follows_the_cldr_rule(count: int, expected: str) -> None:
    assert plural_category("ru", count) == expected


@pytest.mark.parametrize(("count", "expected"), [(1, "one"), (0, "other"), (2, "other")])
def test_english_splits_at_one(count: int, expected: str) -> None:
    assert plural_category("en", count) == expected


@pytest.mark.parametrize("lang", ["uz", "ko"])
@pytest.mark.parametrize("count", [1, 2, 5, 21])
def test_uzbek_and_korean_never_inflect(lang: str, count: int) -> None:
    assert plural_category(lang, count) == "other"


def test_a_bare_string_is_a_phrase_that_never_changes() -> None:
    """How Uzbek and Korean are written: no object, no repetition."""
    phrase = Plural.model_validate("yoqilgan sham")
    assert phrase.pick("uz", 1) == "yoqilgan sham"
    assert phrase.pick("uz", 7) == "yoqilgan sham"


def test_a_missing_form_falls_back_to_other() -> None:
    """`other` is the only required form, so a partial object still renders."""
    phrase = Plural.model_validate({"other": "candles"})
    assert phrase.pick("en", 1) == "candles"


# The bug this all exists for: a card with no age shows one candle, and before
# the fix that read "1 lit candles" in English and "1 зажжённые свечи" in
# Russian - on the one path the bot offers explicitly, via /skip.
@pytest.mark.parametrize(
    ("lang", "count", "expected"),
    [
        ("en", 1, "lit candle"),
        ("en", 28, "lit candles"),
        ("ru", 1, "зажжённая свеча"),
        ("ru", 2, "зажжённые свечи"),
        ("ru", 5, "зажжённых свечей"),
        ("ru", 21, "зажжённая свеча"),
    ],
)
def test_the_candle_label_agrees_with_its_number(lang: str, count: int, expected: str) -> None:
    assert strings(lang).card.lit_label.pick(lang, count) == expected


@pytest.mark.parametrize(
    ("lang", "count", "expected"),
    [
        ("en", 1, "This link disappears in 1 day."),
        ("en", 5, "This link disappears in 5 days."),
        ("ru", 1, "Эта ссылка исчезнет через 1 день."),
        ("ru", 2, "Эта ссылка исчезнет через 2 дня."),
        ("ru", 5, "Эта ссылка исчезнет через 5 дней."),
    ],
)
def test_the_expiry_sentence_agrees_too(lang: str, count: int, expected: str) -> None:
    phrase = strings(lang).card.expires_in.pick(lang, count)
    assert phrase.format(days=count) == expected


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_language_supplies_every_form_its_rule_can_ask_for(lang: str) -> None:
    """A rule that selects a form nobody wrote would silently fall back.

    Checked across the whole plausible range rather than a sample, because the
    gap would only show on the one count that triggers it.
    """
    card = strings(lang).card
    phrases = {
        "lit_label": card.lit_label,
        "out_label": card.out_label,
        "years": card.years,
        "months": card.months,
        "days": card.days,
        "expires_in": card.expires_in,
        "views": card.views,
    }
    for name, phrase in phrases.items():
        for count in range(0, 130):
            category = plural_category(lang, count)
            assert getattr(phrase, category) is not None, (
                f"{lang}.card.{name} has no '{category}' form, needed at {count}"
            )
