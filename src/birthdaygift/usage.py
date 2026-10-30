"""Who used the service, and the two reports that go to the operator.

Cards delete themselves on the fifth day, so the record of who made them lives
in its own append-only table. Reports are driven from that table rather than
from a counter, which means a restart or a missed send never loses an event:
anything not yet marked as reported simply goes out in the next one.
"""

from __future__ import annotations

import datetime as dt
import html
import logging
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Card, UsageEvent

logger = logging.getLogger(__name__)


def record(session: Session, card: Card, creator_id: int, creator_name: str) -> UsageEvent:
    event = UsageEvent(
        card_id=card.id,
        creator_id=creator_id,
        creator_name=creator_name,
        recipient=card.name,
        age=card.age,
        lang=card.lang,
        theme=card.theme,
        source=card.source,
        created_at=dt.datetime.now(dt.UTC),
    )
    session.add(event)
    session.commit()
    return event


def _pending(session: Session, column: str) -> Sequence[UsageEvent]:
    field = getattr(UsageEvent, column)
    statement = select(UsageEvent).where(field.is_(False)).order_by(UsageEvent.created_at)
    return session.execute(statement).scalars().all()


def pending_batch(session: Session) -> Sequence[UsageEvent]:
    return _pending(session, "in_batch_report")


def pending_weekly(session: Session) -> Sequence[UsageEvent]:
    return _pending(session, "in_weekly_report")


def mark_reported(session: Session, events: Sequence[UsageEvent], column: str) -> None:
    for event in events:
        setattr(event, column, True)
    session.commit()


def _ago(then: dt.datetime, now: dt.datetime) -> str:
    if then.tzinfo is None:
        then = then.replace(tzinfo=dt.UTC)
    minutes = int((now - then).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}m"
    hours = minutes // 60
    return f"{hours}h" if hours < 48 else f"{hours // 24}d"


def _handle(event: UsageEvent) -> str:
    """A name for the sender, safe to drop into an HTML message.

    Both reports go out with parse_mode=HTML, and every name in them was typed
    by somebody: a recipient called "<b" is enough to make Telegram reject the
    whole message, which would lose the report rather than render oddly.
    """
    return html.escape(event.creator_name) if event.creator_name else f"id{event.creator_id}"


def batch_report(events: Sequence[UsageEvent]) -> str:
    """The message sent after every tenth card."""
    now = dt.datetime.now(dt.UTC)
    lines = [f"<b>{len(events)} ta yangi tabriknoma</b>", ""]
    for event in events:
        who = html.escape(event.recipient) + (f" ({event.age})" if event.age else "")
        mark = "AI" if event.source == "ai" else "qo‘lda"
        lines.append(f"{_handle(event)} → {who} · {mark} · {_ago(event.created_at, now)}")
    people = len({event.creator_id for event in events})
    ai = sum(1 for event in events if event.source == "ai")
    lines += ["", f"{people} kishi · {ai} ta AI, {len(events) - ai} ta qo‘lda"]
    return "\n".join(lines)


def weekly_report(events: Sequence[UsageEvent], session: Session) -> str:
    """The Monday message: a week in one block, even a quiet one."""
    now = dt.datetime.now(dt.UTC)
    if not events:
        return "<b>Haftalik hisobot</b>\n\nBu hafta birorta tabriknoma yaratilmadi."

    by_person: dict[int, list[UsageEvent]] = {}
    for event in events:
        by_person.setdefault(event.creator_id, []).append(event)

    ai = sum(1 for event in events if event.source == "ai")
    languages: dict[str, int] = {}
    for event in events:
        languages[event.lang] = languages.get(event.lang, 0) + 1

    live = session.execute(select(Card.id).where(Card.expires_at > now.replace(tzinfo=None))).all()

    lines = [
        f"<b>Haftalik hisobot</b> — {len(events)} ta tabriknoma, {len(by_person)} kishi",
        "",
    ]
    for own in sorted(by_person.values(), key=len, reverse=True):
        names = ", ".join(html.escape(event.recipient) for event in own[:4])
        more = f" +{len(own) - 4}" if len(own) > 4 else ""
        lines.append(f"{_handle(own[0])} — {len(own)} ta: {names}{more}")
    lines += [
        "",
        f"AI yozgani: {ai} · qo‘lda: {len(events) - ai}",
        "Tillar: " + ", ".join(f"{lang} {count}" for lang, count in sorted(languages.items())),
        f"Hozir tirik havolalar: {len(live)}",
    ]
    return "\n".join(lines)


def purge_old_events(session: Session, keep_days: int = 400) -> int:
    """Drop events older than a year; both reports have long since seen them."""
    cutoff = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(days=keep_days)
    removed = session.query(UsageEvent).filter(UsageEvent.created_at < cutoff).delete()
    session.commit()
    return int(removed)


def counts_today(session: Session, creator_id: int) -> tuple[int, int]:
    """How many cards this person and everyone together made in the last day.

    A rolling 24 hours rather than a calendar day: a midnight boundary would
    let someone take two allowances an hour apart.
    """
    since = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(days=1)
    mine = session.execute(
        select(func.count())
        .select_from(UsageEvent)
        .where(UsageEvent.created_at >= since, UsageEvent.creator_id == creator_id)
    ).scalar_one()
    everyone = session.execute(
        select(func.count()).select_from(UsageEvent).where(UsageEvent.created_at >= since)
    ).scalar_one()
    return int(mine), int(everyone)
