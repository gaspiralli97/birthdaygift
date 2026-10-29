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
    math_title: str
    prime_one: str
    prime_many: str
    expires_in: str
    from_line: str
    views: str


class ExpiredStrings(_Section):
    title: str
    body: str
    make_one: str


class FormStrings(_Section):
    title: str
    subtitle: str
    how_it_works: str
    lang_label: str
    theme_label: str
    name_label: str
    name_placeholder: str
    age_label: str
    age_placeholder: str
    relation_label: str
    details_label: str
    details_placeholder: str
    details_hint: str
    from_label: str
    from_placeholder: str
    submit: str
    submitting: str
    preview_title: str
    result_title: str
    result_hint: str
    copy_button: str
    copied: str
    again: str
    open_card: str
    error_generic: str
    error_rate: str
    error_name: str


class BotStrings(_Section):
    start: str
    ask_lang: str
    ask_name: str
    ask_age: str
    ask_relation: str
    ask_theme: str
    ask_details: str
    ask_from: str
    working: str
    done: str
    expiry: str
    bad_name: str
    bad_age: str
    limit_user: str
    limit_global: str
    failed: str
    cancelled: str
    unknown: str
    skip_hint: str


class Strings(_Section):
    card: CardStrings
    expired: ExpiredStrings
    form: FormStrings
    bot: BotStrings
    relations: dict[str, str]
    themes: dict[str, str]


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
    return value if value in LANGUAGES else DEFAULT_LANG  # type: ignore[return-value]
