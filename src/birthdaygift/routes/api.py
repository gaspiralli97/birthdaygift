"""JSON API used by the create form."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import cards
from ..config import get_settings
from ..deps import ClientIp, DbSession
from ..i18n import strings
from ..ratelimit import Budget, consume
from ..schemas import CardCreate, CardCreated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/cards", response_model=CardCreated)
def create_card(payload: CardCreate, session: DbSession, ip: ClientIp) -> JSONResponse:
    settings = get_settings()
    copy = strings(payload.lang).form

    decision = consume(
        session,
        [
            Budget(f"ip:{ip}", settings.rate_per_ip_per_day),
            Budget("global", settings.rate_global_per_day),
        ],
    )
    if not decision.allowed:
        logger.info("rate limited: %s", decision.exceeded.bucket if decision.exceeded else "?")
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "message": copy.error_rate},
        )

    card = cards.create(session, payload)
    created = CardCreated(
        id=card.id,
        url=settings.card_url(card.id),
        expires_at=card.expires_at.isoformat(),
        source=card.source,
    )
    return JSONResponse(status_code=201, content=created.model_dump())
