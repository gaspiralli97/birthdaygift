"""When the weekly report is due, and what a restart does to it."""

from __future__ import annotations

import datetime as dt

from birthdaygift.db import session_scope
from birthdaygift.models import Meta
from birthdaygift.scheduler import WEEKLY_KEY, weekly_is_due


def test_a_fresh_deployment_does_not_open_with_an_empty_report(settings) -> None:
    now = dt.datetime.now(dt.UTC)
    with session_scope() as session:
        assert weekly_is_due(session, now) is False
        # ...but it remembers when it started counting
        assert session.get(Meta, WEEKLY_KEY) is not None


def test_nothing_is_due_before_the_week_is_out(settings) -> None:
    now = dt.datetime.now(dt.UTC)
    with session_scope() as session:
        weekly_is_due(session, now)
        assert weekly_is_due(session, now + dt.timedelta(days=6)) is False


def test_the_report_comes_due_after_seven_days(settings) -> None:
    now = dt.datetime.now(dt.UTC)
    with session_scope() as session:
        weekly_is_due(session, now)
        assert weekly_is_due(session, now + dt.timedelta(days=7)) is True


def test_a_corrupted_marker_does_not_wedge_the_schedule(settings) -> None:
    """Better to report once too often than to go quiet forever."""
    with session_scope() as session:
        session.add(Meta(key=WEEKLY_KEY, value="not a timestamp"))
        session.commit()
        assert weekly_is_due(session, dt.datetime.now(dt.UTC)) is True
