"""Storing a card, reading it back, and it going away on time."""

from __future__ import annotations

import datetime as dt

from birthdaygift import cards
from birthdaygift.db import session_scope
from birthdaygift.ids import is_card_id, new_card_id
from birthdaygift.models import Card


def test_a_new_card_keeps_what_it_was_given(make_card) -> None:
    card = make_card(paragraphs=["Bir.", "Ikki.", "Uch."], source="ai")
    assert card.paragraphs == ["Bir.", "Ikki.", "Uch."]
    assert card.source == "ai"
    assert is_card_id(card.id)


def test_the_letter_survives_a_form_feed_in_the_text(make_card) -> None:
    """Paragraphs are joined by \\f, so a stray one must not split a card."""
    card = make_card(paragraphs=["Bitta xatboshi."])
    with session_scope() as session:
        stored = cards.fetch(session, card.id)
        assert stored is not None
        assert stored.paragraphs == ["Bitta xatboshi."]


def test_reading_a_card_counts_the_view(make_card) -> None:
    card = make_card()
    with session_scope() as session:
        for expected in (1, 2):
            seen = cards.fetch(session, card.id)
            assert seen is not None
            assert seen.views == expected
        unchanged = cards.fetch(session, card.id, count_view=False)
        assert unchanged is not None
        assert unchanged.views == 2


def test_an_expired_card_is_deleted_not_merely_hidden(make_card, expire) -> None:
    card = make_card()
    expire(card.id)
    with session_scope() as session:
        assert cards.fetch(session, card.id) is None
        assert session.get(Card, card.id) is None


def test_purging_removes_only_what_has_run_out(make_card, expire) -> None:
    stale = make_card()
    fresh = make_card()
    expire(stale.id)
    with session_scope() as session:
        assert cards.purge_expired(session) == 1
        assert session.get(Card, fresh.id) is not None


def test_a_card_lives_for_the_configured_span(make_card, settings) -> None:
    card = make_card()
    span = card.expires_at.replace(tzinfo=dt.UTC) - card.created_at.replace(tzinfo=dt.UTC)
    assert abs(span.days - settings.card_ttl_days) <= 0


def test_ids_are_long_enough_to_be_unguessable() -> None:
    """Short ids get weaker as the service grows; this one does not."""
    import math

    alphabet = len(set("23456789bcdfghjkmnpqrstvwxyz"))
    bits = len(new_card_id()) * math.log2(alphabet)
    assert bits > 120


def test_junk_ids_never_reach_the_filesystem() -> None:
    for bad in ("", "..", "../../etc/passwd", "a" * 27, "SHORT"):
        assert not is_card_id(bad)
        with session_scope() as session:
            assert cards.fetch(session, bad) is None
