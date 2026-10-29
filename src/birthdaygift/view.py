"""Small helpers that turn stored values into things a template can print."""

from __future__ import annotations

import datetime as dt
import math

from .models import Card


def prime_factors(number: int) -> list[int]:
    """The multiset of primes whose product is ``number``."""
    factors: list[int] = []
    remainder = number
    divisor = 2
    while divisor * divisor <= remainder:
        while remainder % divisor == 0:
            factors.append(divisor)
            remainder //= divisor
        divisor += 1 if divisor == 2 else 2
    if remainder > 1:
        factors.append(remainder)
    return factors


def group_thousands(number: int) -> str:
    return f"{number:,}"


def days_left(card: Card) -> int:
    """Whole days remaining, never less than one while the card is alive."""
    expires_at = card.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.UTC)
    remaining = (expires_at - dt.datetime.now(dt.UTC)).total_seconds()
    return max(1, math.ceil(remaining / 86400))


def lived_days(age: int) -> int:
    """Roughly how many days an age covers, averaged over the leap cycle."""
    return round(age * 365.2425)


#: Beyond this the grid stops being readable and starts being a wall.
MAX_CANDLES = 100


def candle_count(age: int | None) -> int:
    return min(max(age or 1, 1), MAX_CANDLES)
