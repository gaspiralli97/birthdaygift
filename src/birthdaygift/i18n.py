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

from pydantic import BaseModel, ConfigDict

Lang = Literal["uz", "en", "ko", "ru"]
LANGUAGES: tuple[Lang, ...] = get_args(Lang)
DEFAULT_LANG: Lang = "uz"

_DIR = Path(__file__).parent / "translations"


class _Section(BaseModel):
    """Base for every copy section: an unknown key is a mistake, not an extra."""

    model_config = ConfigDict(extra="forbid")


class CardStrings(_Section):
    eyebrow: str
    happy: str
    blow: str
    relight: str
    hint: str
    wished: str
    lit_label: str
    out_label: str
    years: str
    months: str
    days: str
    expires_in: str
    from_line: str
    views: str


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
