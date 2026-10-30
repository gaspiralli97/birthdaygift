"""The one observation the card makes about the age."""

from __future__ import annotations

import pytest

from birthdaygift.facts import WORK_FIELDS, Fact, age_fact
from birthdaygift.i18n import LANGUAGES, fact_note, fact_title


def fact_for(age: int, lang: str = "uz", field: str = "math") -> Fact:
    """`age_fact` is optional by signature; every age here has one."""
    found = age_fact(age, lang, field)
    assert found is not None
    return found


@pytest.mark.parametrize(
    ("age", "kind"),
    [
        (6, "perfect"),
        (28, "perfect"),
        (24, "factorial"),
        (30, "primorial"),
        (36, "square_triangular"),
        (64, "power2"),
        (27, "cube"),
        (25, "square"),
        (21, "fibonacci"),
        (45, "triangular"),
        (33, "repdigit"),
        (7, "prime"),
    ],
)
def test_mathematicians_get_the_arithmetic(age: int, kind: str) -> None:
    assert fact_for(age).kind == kind


def test_a_perfect_number_shows_its_divisors() -> None:
    assert fact_for(28).headline == "28 = 1 + 2 + 4 + 7 + 14"


def test_the_field_picks_the_lens() -> None:
    kinds = {field: fact_for(30, field=field).kind for field in WORK_FIELDS}
    assert kinds["tech"] == "code"
    assert kinds["math"] == "primorial"
    assert kinds["medicine"] == "heart"
    assert kinds["education"] == "words"
    assert kinds["arts"] == "seasons"
    assert kinds["other"] == "orbit"


def test_dull_factorisations_give_way_to_another_lens() -> None:
    """18 = 2 x 3 x 3 says nothing; a mathematician gets binary instead."""
    assert fact_for(18).kind != "factors"


def test_korean_groups_by_eok_not_thousands() -> None:
    assert fact_for(50, "ko", "medicine").headline.endswith("억")


def test_russian_gets_a_cyrillic_unit() -> None:
    assert fact_for(30, "ru", "other").headline.endswith("км")


def test_every_age_and_field_renders_in_every_language() -> None:
    for lang in LANGUAGES:
        for field in WORK_FIELDS:
            for age in range(2, 101):
                fact = age_fact(age, lang, field)
                assert fact is not None
                assert fact.headline
                assert fact_title(lang, fact.kind)
                assert fact_note(lang, fact.kind, fact.values)


def test_an_age_too_small_to_say_anything_about() -> None:
    assert age_fact(1, "uz", "math") is None
    assert age_fact(None, "uz", "math") is None
