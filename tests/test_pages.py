"""The public surface: a card, its image, and nothing that writes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_landing_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "birthdaygift" in response.text


def test_health_reports_live_cards(client: TestClient, make_card) -> None:
    make_card()
    body = client.get("/healthz").json()
    assert body["ok"] is True
    assert body["live_cards"] == 1


def test_card_renders_its_own_colourway(client: TestClient, make_card) -> None:
    card = make_card(theme="vino")
    response = client.get(f"/c/{card.id}")
    assert response.status_code == 200
    # the vino night colour, written onto <html> by the template
    assert "--night:#3a0a16" in response.text
    assert "Sahobiddin" in response.text


def test_card_shows_one_candle_per_year(client: TestClient, make_card) -> None:
    card = make_card(age=7)
    assert 'data-candles="7"' in client.get(f"/c/{card.id}").text


def test_card_escapes_the_senders_text(client: TestClient, make_card) -> None:
    card = make_card(name="<img src=x onerror=alert(1)>")
    body = client.get(f"/c/{card.id}").text
    assert "<img src=x" not in body
    assert "&lt;img" in body


def test_views_are_counted(client: TestClient, make_card) -> None:
    card = make_card()
    for _ in range(3):
        client.get(f"/c/{card.id}")
    assert "3" in client.get(f"/c/{card.id}").text


def test_unknown_card_is_not_found(client: TestClient) -> None:
    assert client.get("/c/" + "b" * 27).status_code == 404


def test_malformed_id_is_rejected(client: TestClient) -> None:
    for bad in ("short", "A" * 27, "../../etc/passwd"):
        assert client.get(f"/c/{bad}").status_code == 404


def test_expired_card_is_gone(client: TestClient, make_card, expire) -> None:
    card = make_card()
    expire(card.id)
    assert client.get(f"/c/{card.id}").status_code == 404


def test_preview_image_is_a_png(client: TestClient, make_card) -> None:
    card = make_card()
    response = client.get(f"/c/{card.id}/og.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_preview_image_does_not_count_as_a_view(client: TestClient, make_card) -> None:
    """Link unfurlers fetch the image; that must not inflate the counter."""
    card = make_card()
    client.get(f"/c/{card.id}/og.png")
    client.get(f"/c/{card.id}/og.png")
    body = client.get(f"/c/{card.id}").text
    assert "2 marta" not in body and "opened 2" not in body


def test_there_is_no_way_to_create_a_card_over_http(client: TestClient) -> None:
    """Cards are made in Telegram; the web side only ever reads."""
    for path in ("/api/cards", "/c", "/create"):
        assert client.post(path, json={"name": "x"}).status_code in (404, 405)
