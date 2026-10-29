"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .db import get_session_factory


def db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(db_session)]


def client_ip(request: Request) -> str:
    """The caller's address.

    uvicorn is started with ``--proxy-headers --forwarded-allow-ips=127.0.0.1``,
    so it has already resolved X-Forwarded-For from our own nginx and nobody
    else's. Reading ``request.client`` therefore gives the real client without
    trusting a header an attacker could set.
    """
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]
