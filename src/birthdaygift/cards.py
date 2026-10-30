"""Creating, reading and expiring cards."""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import get_settings
from .ids import is_card_id, new_card_id
from .models import Card
from .schemas import CardCreate

logger = logging.getLogger(__name__)

#: How many times a colliding id is retried before giving up. With 43 bits of
#: entropy a single collision is already implausible; two in a row would mean
#: something is wrong with the random source, and failing loudly beats looping.
_ID_ATTEMPTS = 5


def create(
    session: Session,
    payload: CardCreate,
    paragraphs: list[str],
    source: str,
) -> Card:
    """Store a card and return it.

    The letter comes in already written - by the sender or by a model - and is
    stored rather than regenerated, so the card reads the same on every visit
    and reopening it costs nothing.
    """
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)

    for _ in range(_ID_ATTEMPTS):
        card_id = new_card_id()
        if session.get(Card, card_id) is None:
            break
    else:
        raise RuntimeError("could not allocate a card id")

    card = Card(
        id=card_id,
        lang=payload.lang,
        theme=payload.theme,
        name=payload.name,
        age=payload.age,
        relation=payload.relation,
        field=payload.field,
        from_name=payload.from_name,
        details=payload.details,
        source=source,
        created_at=now,
        expires_at=now + dt.timedelta(days=settings.card_ttl_days),
        views=0,
    )
    card.paragraphs = paragraphs
    session.add(card)
    session.commit()
    logger.info("card %s created (lang=%s theme=%s)", card.id, card.lang, card.theme)
    return card


def fetch(session: Session, card_id: str, *, count_view: bool = True) -> Card | None:
    """A live card, or ``None`` if it never existed or its five days are up.

    Expired rows are deleted on the way out rather than merely hidden, so a
    card nobody ever purges still stops existing on time.
    """
    if not is_card_id(card_id):
        return None

    card = session.get(Card, card_id)
    if card is None:
        return None

    # SQLite hands back naive datetimes; compare in UTC either way.
    expires_at = card.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.UTC)

    if expires_at <= dt.datetime.now(dt.UTC):
        session.delete(card)
        session.commit()
        return None

    if count_view:
        card.views += 1
        session.commit()

    return card


def purge_expired(session: Session) -> int:
    """Delete every card past its expiry. Returns the number removed."""
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    result = session.execute(delete(Card).where(Card.expires_at <= now))
    session.commit()
    removed = result.rowcount or 0
    if removed:
        logger.info("purged %d expired card(s)", removed)
    return removed


def count_live(session: Session) -> int:
    """How many cards are currently alive, for the health endpoint."""
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    statement = select(Card.id).where(Card.expires_at > now)
    return len(session.execute(statement).all())
