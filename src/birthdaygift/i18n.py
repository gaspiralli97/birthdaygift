"""Interface copy, one JSON file per language.

The files are validated against these models at import time, so a missing or
misspelled key fails at startup rather than halfway through rendering someone's
birthday card.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, model_validator

Lang = Literal["uz", "en", "ko", "ru"]
LANGUAGES: tuple[Lang, ...] = get_args(Lang)
DEFAULT_LANG: Lang = "uz"

_DIR = Path(__file__).parent / "translations"

PluralCategory = Literal["one", "few", "many", "other"]


def plural_category(lang: str, count: int) -> PluralCategory:
    """Which form `lang` needs for `count`, following the CLDR rules.

    Only the four languages this service speaks are covered, because a card is
    rendered in one of them and nothing else ever reaches here.
    """
    n = abs(count)
    if lang == "ru":
        # 1, 21, 31 take the singular; 2-4 a second form; 11-14 and the rest a
        # third. Getting this wrong is the kind of mistake a reader hears.
        if n % 10 == 1 and n % 100 != 11:
            return "one"
        if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
            return "few"
        return "many"
    if lang == "en":
        return "one" if n == 1 else "other"
    # Uzbek and Korean do not inflect a noun after a numeral.
    return "other"


class _Section(BaseModel):
    """Base for every copy section: an unknown key is a mistake, not an extra."""

    model_config = ConfigDict(extra="forbid")


class Plural(_Section):
    """A phrase that carries a number and may inflect with it.

    A bare JSON string means the phrase never changes, which is the whole
    truth for Uzbek and Korean; an object spells out one form per category.
    Every form is optional because no language uses all four: English writes
    `one` and `other`, Russian writes `one`, `few` and `many` and never needs
    `other` at all, since that category only arises for fractions and a count
    here is always a whole number of candles, months or days.

    Which forms a language actually has to supply is not checked here - it
    depends on the rule, not the file - so `tests/test_plurals.py` walks every
    count the card can show and asserts the form it selects exists.
    """

    one: str | None = None
    few: str | None = None
    many: str | None = None
    other: str | None = None

    #: Tried in turn when a category has no form, commonest first. Reaching
    #: past the first entry means a file is incomplete, which the test above
    #: is there to catch; rendering a slightly wrong noun still beats a 500
    #: on somebody's birthday card.
    _FALLBACK = ("other", "many", "few", "one")

    @model_validator(mode="before")
    @classmethod
    def _accept_a_bare_string(cls, value: object) -> object:
        return {"other": value} if isinstance(value, str) else value

    @model_validator(mode="after")
    def _at_least_one_form(self) -> Plural:
        if not any(getattr(self, name) for name in self._FALLBACK):
            raise ValueError("a plural phrase needs at least one form")
        return self

    def pick(self, lang: str, count: int) -> str:
        """The form `lang` needs for `count`."""
        chosen: str | None = getattr(self, plural_category(lang, count))
        if chosen is not None:
            return chosen
        for name in self._FALLBACK:
            fallback: str | None = getattr(self, name)
            if fallback is not None:
                return fallback
        raise AssertionError("unreachable: the validator requires a form")  # pragma: no cover


class CardStrings(_Section):
    eyebrow: str
    happy: str
    blow: str
    relight: str
    hint: str
    wished: str
    #: Every one of these sits next to a number, so each one inflects.
    lit_label: Plural
    out_label: Plural
    years: Plural
    months: Plural
    days: Plural
    expires_in: Plural
    from_line: str
    views: Plural


class ExpiredStrings(_Section):
    title: str
    body: str
    make_one: str


class LandingStrings(_Section):
    title: str
    lede: str
    how: str


class BotStrings(_Section):
    start: str
    ask_lang: str
    ask_theme: str
    ask_mode: str
    mode_self: str
    mode_ai: str
    ask_name: str
    ask_age: str
    ask_relation: str
    ask_field: str
    ask_brief: str
    ask_letter: str
    ask_from: str
    working: str
    done: str
    expiry: str
    bad_name: str
    bad_age: str
    bad_text: str
    ai_failed: str
    failed: str
    cancelled: str
    unknown: str
    again: str
    limit_user: str
    limit_global: str


class Strings(_Section):
    card: CardStrings
    expired: ExpiredStrings
    landing: LandingStrings
    bot: BotStrings
    relations: dict[str, str]
    themes: dict[str, str]
    fields: dict[str, str]
    #: One title per lens (number, code, heart, …) and one note per fact kind.
    fact_titles: dict[str, str]
    fact_notes: dict[str, str]


@lru_cache
def strings(lang: str) -> Strings:
    """Copy for one language, falling back to the default for anything unknown."""
    key = lang if lang in LANGUAGES else DEFAULT_LANG
    raw = json.loads((_DIR / f"{key}.json").read_text(encoding="utf-8"))
    return Strings.model_validate(raw)


def load_all() -> dict[str, Strings]:
    """Validate every language. Called at startup to fail fast on a bad file."""
    return {lang: strings(lang) for lang in LANGUAGES}


def normalize_lang(value: str | None) -> Lang:
    for candidate in LANGUAGES:
        if value == candidate:
            return candidate
    return DEFAULT_LANG


#: Every arithmetic fact shares one title; the other lenses have their own.
_TITLE_GROUP = {
    "perfect": "number",
    "factorial": "number",
    "primorial": "number",
    "square_triangular": "number",
    "power2": "number",
    "cube": "number",
    "square": "number",
    "fibonacci": "number",
    "triangular": "number",
    "repdigit": "number",
    "prime": "number",
    "round": "number",
    "factors": "number",
}


def fact_title(lang: str, kind: str) -> str:
    return strings(lang).fact_titles[_TITLE_GROUP.get(kind, kind)]


def fact_note(lang: str, kind: str, values: dict[str, object]) -> str:
    return strings(lang).fact_notes[kind].format(**values)
