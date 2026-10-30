"""The webhook Telegram posts updates to.

The path carries the shared secret and the header is checked as well: Telegram
echoes the secret back on every call, so an update that fails either test did
not come from Telegram and is dropped without being parsed.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

from .. import bot as telegram_bot
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram/{secret}")
async def webhook(secret: str, request: Request) -> Response:
    settings = get_settings()
    expected = settings.telegram_webhook_secret
    header = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not expected or secret != expected or header != expected:
        logger.warning("rejected a webhook call with a bad secret")
        return Response(status_code=403)

    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=400)

    try:
        await telegram_bot.handle_update(payload)
    except Exception:
        # Telegram retries anything that is not a 2xx, and a retry of a
        # malformed update would simply fail again. Log and accept.
        logger.exception("update handling failed")
    return Response(status_code=200)
