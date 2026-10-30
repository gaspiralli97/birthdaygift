"""One true thing about the age, chosen to suit what the person does.

This is the part of the card a template can be genuinely clever about, because
it is computed rather than recalled: 28 is a perfect number and 30 is not, and
no amount of rephrasing changes that. Every age gets a different observation,
so nothing here repeats however many cards are made.

Number theory is a lovely thing to say to a mathematician and a strange thing
to say to a nurse, so the person's field picks the lens. The non-mathematical
lenses are computed too - heartbeats, laps of the sun - from honest averages
that the copy always hedges with "about".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, get_args

WorkField = Literal["other", "tech", "math", "medicine", "education", "arts", "sport", "business"]
WORK_FIELDS: tuple[WorkField, ...] = get_args(WorkField)
DEFAULT_WORK_FIELD: WorkField = "other"

FactKind = Literal[
    "perfect",
    "factorial",
    "primorial",
    "square_triangular",
    "power2",
    "cube",
    "square",
    "fibonacci",
    "triangular",
    "repdigit",
    "prime",
    "round",
    "factors",
    "code",
    "heart",
    "words",
    "orbit",
    "seasons",
    "sleep",
]

YEAR_DAYS = 365.2425
#: Honest averages. 70 beats a minute, 16,000 spoken words a day, and one lap
#: of the Earth's orbit at 2*pi*149.6 million km.
PER_YEAR = {
    "heart": 70 * 60 * 24 * YEAR_DAYS,
    "words": 16_000 * YEAR_DAYS,
    "orbit_km": 939_964_521,
}

_FIBONACCI = frozenset({1, 2, 3, 5, 8, 13, 21, 34, 55, 89})
_TRIANGULAR = frozenset((n * (n + 1)) // 2 for n in range(1, 20))
_FACTORIAL = {2: 2, 6: 3, 24: 4, 120: 5}
_PRIMORIAL = {6: 2, 30: 3, 210: 4}
_SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"

#: Which lens suits which trade, strongest first.
_PREFERENCE: dict[WorkField, tuple[str, ...]] = {
    "tech": ("code", "number", "orbit"),
    "math": ("number", "code", "orbit"),
    "medicine": ("heart", "sleep", "orbit"),
    "education": ("words", "seasons", "orbit"),
    "arts": ("seasons", "orbit", "sleep"),
    "sport": ("heart", "orbit", "sleep"),
    "business": ("orbit", "number", "words"),
    "other": ("orbit", "number", "seasons"),
}


@dataclass(frozen=True, slots=True)
class Fact:
    kind: FactKind
    #: The large type on the card, already formatted.
    headline: str
    #: Values the translated note interpolates, e.g. {"k": 4}.
    values: dict[str, object]


def factorise(n: int) -> list[int]:
    factors: list[int] = []
    rest, divisor = n, 2
    while divisor * divisor <= rest:
        while rest % divisor == 0:
            factors.append(divisor)
            rest //= divisor
        divisor += 1 if divisor == 2 else 2
    if rest > 1:
        factors.append(rest)
    return factors


def _proper_divisors(n: int) -> list[int]:
    return [i for i in range(1, n) if n % i == 0]


def _superscript(k: int) -> str:
    return "".join(_SUPERSCRIPT[int(d)] for d in str(k))


def big(n: float, lang: str) -> str:
    """A large number the way the language actually groups it."""
    n = round(n)
    if lang == "ko":
        # Korean groups by 만 (10^4) and 억 (10^8), not by thousands.
        if n >= 10**8:
            return f"{n / 10**8:.1f}".removesuffix(".0") + "억"
        if n >= 10**4:
            return f"{round(n / 10**4)}만"
        return f"{n:,}"
    if n >= 10**9:
        text = f"{n / 10**9:.1f}"
        unit = {"uz": "mlrd", "en": "billion", "ru": "млрд"}.get(lang, "mlrd")
        if lang != "en":
            text = text.replace(".", ",")
        return f"{text} {unit}"
    if n >= 10**6:
        unit = {"uz": "mln", "en": "million", "ru": "млн"}.get(lang, "mln")
        return f"{round(n / 10**6)} {unit}"
    grouped = f"{n:,}"
    return grouped if lang == "en" else grouped.replace(",", " ")


def _number_fact(n: int) -> Fact | None:
    """The most interesting arithmetic statement about ``n``, in priority order."""
    if n < 2:
        return None
    factors = factorise(n)

    divisors = _proper_divisors(n)
    if sum(divisors) == n:
        return Fact("perfect", f"{n} = " + " + ".join(map(str, divisors)), {"n": n})
    if n in _FACTORIAL:
        return Fact("factorial", f"{n} = {_FACTORIAL[n]}!", {"k": _FACTORIAL[n]})
    if n in _PRIMORIAL:
        return Fact("primorial", f"{n} = " + " × ".join(map(str, factors)), {"k": _PRIMORIAL[n]})
    if n == 36:
        return Fact("square_triangular", "36 = 6² = 1+2+…+8", {})
    if n & (n - 1) == 0:
        k = n.bit_length() - 1
        return Fact("power2", f"{n} = 2{_superscript(k)}", {"k": k})
    root = round(n ** (1 / 3))
    if root**3 == n:
        return Fact("cube", f"{n} = {root}³", {"k": root})
    root = math.isqrt(n)
    if root * root == n:
        return Fact("square", f"{n} = {root}²", {"k": root})
    if n in _FIBONACCI:
        return Fact("fibonacci", str(n), {})
    if n in _TRIANGULAR:
        rows = round((math.isqrt(8 * n + 1) - 1) / 2)
        return Fact("triangular", f"{n} = 1+2+…+{rows}", {"k": rows})
    if n >= 11 and len(set(str(n))) == 1:
        return Fact("repdigit", str(n), {})
    if len(factors) == 1:
        return Fact("prime", str(n), {})
    joined = " × ".join(map(str, factors))
    return Fact("round" if n % 10 == 0 else "factors", f"{n} = {joined}", {})


def _lens(kind: str, n: int, lang: str) -> Fact | None:
    if kind == "code":
        return Fact("code", f"{n} = 0b{n:b} = 0x{n:X}", {})
    if kind == "heart":
        return Fact("heart", big(n * PER_YEAR["heart"], lang), {})
    if kind == "words":
        return Fact("words", big(n * PER_YEAR["words"], lang), {})
    if kind == "orbit":
        unit = "км" if lang == "ru" else "km"
        return Fact("orbit", f"{big(n * PER_YEAR['orbit_km'], lang)} {unit}", {"n": n})
    if kind == "seasons":
        return Fact("seasons", str(n), {})
    if kind == "sleep":
        years = f"{n / 3:.1f}".removesuffix(".0")
        return Fact("sleep", years, {})
    return None


def age_fact(age: int | None, lang: str, field: str = DEFAULT_WORK_FIELD) -> Fact | None:
    """The card's one observation about the age, or ``None`` when there is none."""
    if age is None or age < 2:
        return None

    numeric = _number_fact(age)
    # Plain factorisation is the dull end of number theory; let it through only
    # when nothing better is on offer.
    numeric_is_interesting = numeric is not None and numeric.kind != "factors"

    preference = next(
        (_PREFERENCE[known] for known in WORK_FIELDS if known == field),
        _PREFERENCE[DEFAULT_WORK_FIELD],
    )
    for kind in preference:
        if kind == "number":
            if numeric_is_interesting:
                return numeric
            continue
        made = _lens(kind, age, lang)
        if made is not None:
            return made
    return numeric
