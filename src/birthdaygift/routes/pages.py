"""HTML pages and the preview image."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from .. import cards, view
from ..config import get_settings
from ..deps import DbSession
from ..i18n import LANGUAGES, normalize_lang, strings
from ..ids import is_card_id
from ..og import render_card_image
from ..templating import templates
from ..themes import THEMES, get_theme

router = APIRouter()

LANGUAGE_NAMES = {
    "uz": "O‘zbekcha",
    "en": "English",
    "ko": "한국어",
    "ru": "Русский",
}


def _negotiate(request: Request) -> str:
    """Pick a UI language from ?lang= or the browser's Accept-Language."""
    requested = request.query_params.get("lang")
    if requested in LANGUAGES:
        return requested
    header = request.headers.get("accept-language", "")
    for part in header.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGUAGES:
            return code
    return "uz"


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> Response:
    settings = get_settings()
    lang = _negotiate(request)
    theme = get_theme("midnight")

    # The form restyles itself as the theme radio changes, so the palettes have
    # to reach the client as data rather than as pre-rendered CSS.
    theme_json = {
        key: {
            "variables": dict(pair.split(":", 1) for pair in value.css_variables.split(";")),
            "color_scheme": value.color_scheme,
        }
        for key, value in THEMES.items()
    }

    bot_url = None
    if settings.bot_enabled and request.app.state.bot_username:
        bot_url = f"https://t.me/{request.app.state.bot_username}"

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "lang": lang,
            "strings": strings(lang),
            "theme": theme,
            "themes": THEMES,
            "theme_json": json.dumps(theme_json),
            "language_names": LANGUAGE_NAMES,
            "bot_url": bot_url,
        },
    )


@router.get("/c/{card_id}", response_class=HTMLResponse)
def show_card(card_id: str, request: Request, session: DbSession) -> Response:
    card = cards.fetch(session, card_id)
    if card is None:
        lang = _negotiate(request)
        return templates.TemplateResponse(
            request,
            "expired.html",
            {"lang": lang, "strings": strings(lang), "theme": get_theme("midnight")},
            status_code=404,
        )

    lang = normalize_lang(card.lang)
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "card.html",
        {
            "card": card,
            "lang": lang,
            "strings": strings(lang),
            "theme": get_theme(card.theme),
            "candles": view.candle_count(card.age),
            "days_left": view.days_left(card),
            "card_url": settings.card_url(card.id),
        },
        headers={"cache-control": "no-store"},
    )


@router.get("/c/{card_id}/og.png")
def card_image(card_id: str, session: DbSession) -> Response:
    if not is_card_id(card_id):
        return Response(status_code=404)

    # Link unfurlers fetch this; counting each as a view would inflate the
    # number the recipient sees on the page.
    card = cards.fetch(session, card_id, count_view=False)
    if card is None:
        return Response(status_code=404)

    return Response(
        content=render_card_image(card),
        media_type="image/png",
        headers={"cache-control": "public, max-age=3600"},
    )


@router.get("/healthz")
def healthz(session: DbSession) -> dict[str, object]:
    return {"ok": True, "live_cards": cards.count_live(session)}
