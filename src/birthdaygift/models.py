"""Database tables."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Card(Base):
    """One generated card.

    The rendered letter is stored rather than regenerated, so a card always
    reads the same however many times it is opened, and reopening it costs
    nothing.
    """

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)

    lang: Mapped[str] = mapped_column(String(2))
    theme: Mapped[str] = mapped_column(String(16))

    name: Mapped[str] = mapped_column(String(40))
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relation: Mapped[str] = mapped_column(String(16))
    #: Drives which observation the card makes about the age.
    field: Mapped[str] = mapped_column(String(16), default="other")
    from_name: Mapped[str] = mapped_column(String(40), default="")
    details: Mapped[str] = mapped_column(String(600), default="")

    # Paragraphs joined by a form feed: SQLite has no array type, and this
    # cannot collide with anything the text layer produces.
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16))

    created_at: Mapped[dt.datetime] = mapped_column()
    expires_at: Mapped[dt.datetime] = mapped_column()
    views: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_cards_expires_at", "expires_at"),)

    SEPARATOR = "\f"

    @property
    def paragraphs(self) -> list[str]:
        return [p for p in self.body.split(self.SEPARATOR) if p]

    @paragraphs.setter
    def paragraphs(self, value: list[str]) -> None:
        self.body = self.SEPARATOR.join(value)


class RateCounter(Base):
    """Per-day counters, one row per bucket.

    Buckets are opaque strings such as ``ip:203.0.113.4``, ``tg:12345`` or
    ``global``, which keeps every limit in one table and one query.
    """

    __tablename__ = "rate_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket: Mapped[str] = mapped_column(String(64))
    day: Mapped[str] = mapped_column(String(10))  # ISO date
    count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("bucket", "day", name="uq_rate_bucket_day"),)


class UsageEvent(Base):
    """One row per card made, kept after the card itself is gone.

    Cards delete themselves on the fifth day, so they cannot carry the record
    of who used the service. This table is append-only and never purged with
    them, which is what lets the weekly report look further back than the
    cards still alive.
    """

    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(32))

    creator_id: Mapped[int] = mapped_column(Integer)
    creator_name: Mapped[str] = mapped_column(String(80), default="")

    recipient: Mapped[str] = mapped_column(String(40))
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lang: Mapped[str] = mapped_column(String(2))
    theme: Mapped[str] = mapped_column(String(16))
    #: "self" when the sender wrote the letter, "ai" when a model did.
    source: Mapped[str] = mapped_column(String(16))

    created_at: Mapped[dt.datetime] = mapped_column()
    #: Cleared once the event has gone out in each kind of report.
    in_batch_report: Mapped[bool] = mapped_column(Boolean, default=False)
    in_weekly_report: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_usage_created_at", "created_at"),
        Index("ix_usage_pending", "in_batch_report", "in_weekly_report"),
    )
