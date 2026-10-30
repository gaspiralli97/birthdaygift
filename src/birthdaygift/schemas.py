"""Request and response shapes.

One model serves the HTML form, the JSON API and the bot, so the three paths
cannot drift apart on what counts as valid input.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .facts import WorkField
from .i18n import Lang
from .themes import ThemeKey

Relation = Literal["friend", "classmate", "colleague", "family", "other"]
RELATIONS: tuple[Relation, ...] = get_args(Relation)

_WHITESPACE = re.compile(r"\s+")


def _collapse(value: str) -> str:
    """Flatten newlines and runs of spaces.

    Names and details end up in one-line contexts - a page title, a Telegram
    message, an OG image - so multi-line input is normalised at the edge rather
    than defended against in every renderer.
    """
    return _WHITESPACE.sub(" ", value).strip()


class CardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=40)]
    age: Annotated[int, Field(ge=1, le=129)] | None = None
    relation: Relation = "friend"
    field: WorkField = "other"
    lang: Lang = "uz"
    theme: ThemeKey = "midnight"
    details: Annotated[str, Field(max_length=600)] = ""
    from_name: Annotated[str, Field(max_length=40)] = ""

    @field_validator("name", "details", "from_name", mode="before")
    @classmethod
    def _clean(cls, value: object) -> object:
        return _collapse(value) if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def _name_has_letters(cls, value: str) -> str:
        if len(value.replace(" ", "")) < 2:
            raise ValueError("name is too short")
        return value


class CardCreated(BaseModel):
    """What a successful creation returns."""

    id: str
    url: str
    expires_at: str
    source: str


class ErrorResponse(BaseModel):
    error: Literal["validation", "rate_limited", "internal"]
    message: str
