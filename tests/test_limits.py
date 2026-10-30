"""The daily caps, and the things they are there to protect."""

from __future__ import annotations

import datetime as dt

from birthdaygift.bot import _over_budget
from birthdaygift.db import session_scope
from birthdaygift.models import UsageEvent
from birthdaygift.usage import counts_today


def _event(session, creator_id: int = 1, hours_ago: int = 0) -> None:
    session.add(
        UsageEvent(
            card_id="b" * 27,
            creator_id=creator_id,
            creator_name="@aziz",
            recipient="Dilnoza",
            age=30,
            lang="uz",
            theme="qora",
            source="ai",
            created_at=dt.datetime.now(dt.UTC) - dt.timedelta(hours=hours_ago),
        )
    )
    session.commit()


def test_counting_separates_one_person_from_everyone(settings) -> None:
    with session_scope() as session:
        _event(session, creator_id=1)
        _event(session, creator_id=1)
        _event(session, creator_id=2)
        assert counts_today(session, 1) == (2, 3)
        assert counts_today(session, 2) == (1, 3)


def test_the_window_rolls_rather_than_resetting_at_midnight(settings) -> None:
    """A calendar day would hand out two allowances an hour apart."""
    with session_scope() as session:
        _event(session, hours_ago=25)
        _event(session, hours_ago=1)
        assert counts_today(session, 1) == (1, 1)


def test_a_person_under_the_cap_may_carry_on(settings) -> None:
    with session_scope() as session:
        _event(session, creator_id=7)
    assert _over_budget(7) is None


def test_a_person_at_their_cap_is_stopped(settings) -> None:
    with session_scope() as session:
        for _ in range(settings.rate_per_user_per_day):
            _event(session, creator_id=7)
    assert _over_budget(7) == "user"


def test_the_service_cap_stops_everyone(settings) -> None:
    """One person's quota is untouched, but the shared budget is gone."""
    with session_scope() as session:
        for creator in range(settings.rate_global_per_day):
            _event(session, creator_id=1000 + creator)
    assert _over_budget(999) == "global"


def test_the_caps_are_checked_before_the_letter_is_written() -> None:
    """The model call is the expensive part, so the guard precedes it."""
    import inspect

    from birthdaygift import bot

    source = inspect.getsource(bot._finish)
    assert source.index("_over_budget") < source.index("_write_letter")


def test_a_failed_delivery_does_not_mark_the_batch_reported() -> None:
    """Marking first would lose those ten; a duplicate is the better failure."""
    import inspect

    from birthdaygift import bot

    source = inspect.getsource(bot._maybe_report)
    assert source.index("send_message") < source.index("mark_reported")
