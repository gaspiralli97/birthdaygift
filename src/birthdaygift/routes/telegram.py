"""The webhook Telegram posts updates to.

The path is static and carries no secret. Telegram echoes the shared secret
back in a header on every call, which is enough to authenticate it, and a
secret in the path would be written into nginx's access log on every request.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Request, Response

from .. import bot as telegram_bot
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

WEBHOOK_PATH = "/telegram/webhook"


@router.post(WEBHOOK_PATH)
async def webhook(request: Request) -> Response:
    expected = get_settings().telegram_webhook_secret
    offered = request.headers.get("x-telegram-bot-api-secret-token", "")
    # compare_digest rather than == : the cost is nothing and it removes the
    # question of whether a timing side channel is reachable here.
    if not expected or not hmac.compare_digest(offered, expected):
        logger.warning("rejected a webhook call without the shared secret")
        return Response(status_code=403)

    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=400)

    try:
        await telegram_bot.handle_update(payload)
    except Exception:
        # Telegram retries anything that is not 2xx, and a retry of a
        # malformed update would simply fail again. Log it and accept.
        logger.exception("update handling failed")
    return Response(status_code=200)
