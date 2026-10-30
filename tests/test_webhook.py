"""The only endpoint that accepts a POST, and what it refuses."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import SECRET

UPDATE = {
    "update_id": 1,
    "message": {"message_id": 1, "date": 0, "chat": {"id": 1, "type": "private"}, "text": "/start"},
}


def test_a_call_without_the_header_is_refused(client: TestClient) -> None:
    assert client.post(f"/telegram/{SECRET}", json=UPDATE).status_code == 403


def test_a_call_with_the_wrong_path_secret_is_refused(client: TestClient) -> None:
    response = client.post(
        "/telegram/not-the-secret",
        json=UPDATE,
        headers={"x-telegram-bot-api-secret-token": SECRET},
    )
    assert response.status_code == 403


def test_a_call_with_the_wrong_header_is_refused(client: TestClient) -> None:
    response = client.post(
        f"/telegram/{SECRET}",
        json=UPDATE,
        headers={"x-telegram-bot-api-secret-token": "wrong"},
    )
    assert response.status_code == 403


def test_a_matching_call_is_accepted(client: TestClient) -> None:
    """Both halves match, so the update is taken even with no bot running."""
    response = client.post(
        f"/telegram/{SECRET}",
        json=UPDATE,
        headers={"x-telegram-bot-api-secret-token": SECRET},
    )
    assert response.status_code == 200


def test_a_malformed_body_does_not_crash_the_endpoint(client: TestClient) -> None:
    response = client.post(
        f"/telegram/{SECRET}",
        content=b"not json",
        headers={
            "x-telegram-bot-api-secret-token": SECRET,
            "content-type": "application/json",
        },
    )
    assert response.status_code == 400
