"""Per-day request budgets.

Generation is paid for by whoever runs the service, and the form is open to
anybody, so every creation path goes through here first.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .models import RateCounter


@dataclass(frozen=True, slots=True)
class Budget:
    bucket: str
    limit: int


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    #: Which budget ran out, when one did.
    exceeded: Budget | None = None
    remaining: int = 0


def _today() -> str:
    return dt.datetime.now(dt.UTC).date().isoformat()


def consume(session: Session, budgets: list[Budget]) -> Decision:
    """Charge one unit against every budget, all or nothing.

    Each counter is incremented and read back in the same statement. If any
    budget turns out to be over its limit the transaction is rolled back, which
    undoes every increment at once - so a request that is refused never leaves a
    partial charge behind, and no compensating "refund" path is needed.
    """
    day = _today()
    counts: dict[str, int] = {}

    for budget in budgets:
        statement = (
            sqlite_insert(RateCounter)
            .values(bucket=budget.bucket, day=day, count=1)
            .on_conflict_do_update(
                index_elements=[RateCounter.bucket, RateCounter.day],
                set_={"count": RateCounter.count + 1},
            )
            .returning(RateCounter.count)
        )
        counts[budget.bucket] = session.execute(statement).scalar_one()

    for budget in budgets:
        if counts[budget.bucket] > budget.limit:
            session.rollback()
            return Decision(allowed=False, exceeded=budget)

    session.commit()
    narrowest = min(budgets, key=lambda b: b.limit - counts[b.bucket])
    return Decision(allowed=True, remaining=narrowest.limit - counts[narrowest.bucket])


def purge_old_counters(session: Session, keep_days: int = 7) -> int:
    """Drop counter rows older than ``keep_days``; nothing reads them."""
    cutoff = (dt.datetime.now(dt.UTC).date() - dt.timedelta(days=keep_days)).isoformat()
    result = session.query(RateCounter).filter(RateCounter.day < cutoff).delete()
    session.commit()
    return int(result)
