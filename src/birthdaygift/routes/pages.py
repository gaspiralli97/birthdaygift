"""The public side: a card, its preview image, and a page explaining the bot.

Cards are made in Telegram, so nothing here creates one. Everything this
router serves is read-only, which is what keeps the only internet-facing
surface this small.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from .. import cards, view
from ..config import get_settings
from ..deps import DbSession
from ..facts import age_fact
from ..i18n import LANGUAGES, fact_note, fact_title, normalize_lang, strings
from ..ids import is_card_id
from ..og import render_card_image
from ..templating import templates
from ..themes import get_theme

router = APIRouter()


@dataclass(frozen=True, slots=True)
class RenderedFact:
    title: str
    headline: str
    note: str


def _negotiate(request: Request) -> str:
    """Pick a language from ?lang= or the browser's Accept-Language."""
    requested = request.query_params.get("lang")
    if requested in LANGUAGES:
        return requested
    for part in request.headers.get("accept-language", "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGUAGES:
            return code
    return "uz"


@router.get("/", response_class=HTMLResponse)
def landing(request: Request) -> Response:
    settings = get_settings()
    lang = _negotiate(request)
    copy = strings(lang)

    bot_username = getattr(request.app.state, "bot_username", None)
    return templates.TemplateResponse(
        request,
        "landing.html",
        {
            "lang": lang,
            "strings": copy,
            "theme": get_theme("qora"),
            "title": copy.landing.title,
            "lede": copy.landing.lede,
            "how": copy.landing.how,
            "bot_url": f"https://t.me/{bot_username}" if bot_username else None,
            "site_url": settings.site_url,
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
            {"lang": lang, "strings": strings(lang), "theme": get_theme("qora")},
            status_code=404,
        )

    lang = normalize_lang(card.lang)
    fact = age_fact(card.age, lang, card.field)
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
            "card_url": get_settings().card_url(card.id),
            "fact": (
                RenderedFact(
                    title=fact_title(lang, fact.kind),
                    headline=fact.headline,
                    note=fact_note(lang, fact.kind, fact.values),
                )
                if fact
                else None
            ),
        },
        headers={"cache-control": "no-store"},
    )


@router.get("/c/{card_id}/og.png")
def card_image(card_id: str, session: DbSession) -> Response:
    if not is_card_id(card_id):
        return Response(status_code=404)

    # Link unfurlers fetch this; counting each as a view would inflate the
    # number the recipient is shown on the page.
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
