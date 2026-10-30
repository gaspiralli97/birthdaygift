"""Background upkeep: expiry, the weekly report, and trimming the log.

One loop rather than cron or a systemd timer. The service is a single
long-running process on one box, so an in-process loop is the smallest thing
that works, and it keeps the schedule beside the code it drives.

Everything it does is idempotent and derived from the database, so a missed
tick or a restart mid-cycle costs nothing: the next tick picks up whatever is
still outstanding.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging

from sqlalchemy.orm import Session

from . import cards, usage
from .config import get_settings
from .db import session_scope
from .models import Meta

logger = logging.getLogger(__name__)

TICK_SECONDS = 3600
WEEKLY_KEY = "weekly_report_sent_at"


def _read(session: Session, key: str) -> str | None:
    row = session.get(Meta, key)
    return row.value if row else None


def _write(session: Session, key: str, value: str) -> None:
    row = session.get(Meta, key)
    if row is None:
        session.add(Meta(key=key, value=value))
    else:
        row.value = value
    session.commit()


def weekly_is_due(session: Session, now: dt.datetime) -> bool:
    """Whether a week has passed since the last report.

    The first ever tick records the time instead of reporting, so a fresh
    deployment does not open with an empty summary.
    """
    stamp = _read(session, WEEKLY_KEY)
    if stamp is None:
        _write(session, WEEKLY_KEY, now.isoformat())
        return False
    try:
        last = dt.datetime.fromisoformat(stamp)
    except ValueError:
        return True
    return now - last >= dt.timedelta(days=7)


async def _send_weekly(bot, session: Session, now: dt.datetime) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    pending = list(usage.pending_weekly(session))
    text = usage.weekly_report(pending, session)
    try:
        await bot.send_message(settings.telegram_owner_id, text)
    except Exception:
        # Leave the marker alone so the next tick tries again rather than
        # silently skipping a week.
        logger.exception("could not deliver the weekly report")
        return
    usage.mark_reported(session, pending, "in_weekly_report")
    _write(session, WEEKLY_KEY, now.isoformat())


async def _tick() -> None:
    from .bot import get_bot

    settings = get_settings()
    now = dt.datetime.now(dt.UTC)

    with session_scope() as session:
        removed = cards.purge_expired(session)
        if removed:
            logger.info("purged %d expired card(s)", removed)
        dropped = usage.purge_old_events(session)
        if dropped:
            logger.info("dropped %d usage event(s) past retention", dropped)

        bot = get_bot()
        if bot is not None and settings.telegram_owner_id and weekly_is_due(session, now):
            await _send_weekly(bot, session, now)


async def run() -> None:
    """Tick forever. Cancelled on shutdown."""
    while True:
        try:
            await _tick()
        except Exception:
            logger.exception("scheduler tick failed")
        await asyncio.sleep(TICK_SECONDS)


def start() -> asyncio.Task[None]:
    return asyncio.create_task(run())


async def stop(task: asyncio.Task[None]) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
