"""The record of who used the service, and the two reports built from it."""

from __future__ import annotations

import datetime as dt

from birthdaygift import usage
from birthdaygift.db import session_scope
from birthdaygift.models import UsageEvent


def _event(session, **overrides):  # type: ignore[no-untyped-def]
    defaults = {
        "card_id": "b" * 27,
        "creator_id": 1,
        "creator_name": "@aziz",
        "recipient": "Dilnoza",
        "age": 30,
        "lang": "uz",
        "theme": "qora",
        "source": "ai",
        "created_at": dt.datetime.now(dt.UTC),
    }
    event = UsageEvent(**{**defaults, **overrides})
    session.add(event)
    session.commit()
    return event


def test_a_card_leaves_a_record(make_card, settings) -> None:
    card = make_card()
    with session_scope() as session:
        event = usage.record(session, card, creator_id=42, creator_name="@aziz")
        assert event.card_id == card.id
        assert event.recipient == card.name
        assert usage.pending_batch(session)


def test_the_record_outlives_the_card(make_card, expire) -> None:
    """Cards expire; the weekly report still has to know they happened."""
    from birthdaygift import cards

    card = make_card()
    with session_scope() as session:
        usage.record(session, card, 42, "@aziz")
    expire(card.id)
    with session_scope() as session:
        cards.purge_expired(session)
        assert len(usage.pending_weekly(session)) == 1


def test_reported_events_do_not_come_round_again(settings) -> None:
    with session_scope() as session:
        for _ in range(3):
            _event(session)
        pending = list(usage.pending_batch(session))
        usage.mark_reported(session, pending, "in_batch_report")
        assert usage.pending_batch(session) == []
        # the weekly report has not seen them yet
        assert len(usage.pending_weekly(session)) == 3


def test_the_digest_names_everyone_and_counts_the_split(settings) -> None:
    with session_scope() as session:
        _event(session, creator_name="@aziz", recipient="Dilnoza", source="ai")
        _event(session, creator_name="@nodira", recipient="Bekzod", source="self")
        text = usage.batch_report(usage.pending_batch(session))
    assert "@aziz" in text and "@nodira" in text
    assert "Dilnoza" in text and "Bekzod" in text
    assert "1 ta AI" in text


def test_a_creator_without_a_username_is_still_identifiable(settings) -> None:
    with session_scope() as session:
        _event(session, creator_id=777, creator_name="")
        assert "id777" in usage.batch_report(usage.pending_batch(session))


def test_a_quiet_week_still_reports(settings) -> None:
    with session_scope() as session:
        assert "Haftalik" in usage.weekly_report([], session)


def test_the_weekly_report_groups_by_person(settings) -> None:
    with session_scope() as session:
        for _ in range(4):
            _event(session, creator_id=1, creator_name="@aziz")
        _event(session, creator_id=2, creator_name="@nodira")
        text = usage.weekly_report(usage.pending_weekly(session), session)
    assert "2 kishi" in text
    assert "@aziz — 4 ta" in text


def test_old_events_are_eventually_dropped(settings) -> None:
    with session_scope() as session:
        _event(session, created_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=500))
        _event(session)
        assert usage.purge_old_events(session, keep_days=400) == 1
        assert len(usage.pending_batch(session)) == 1
