"""Engine and session plumbing."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base


def _configure_sqlite(dbapi_connection: object, _record: object) -> None:
    """Settings SQLite needs to behave under a concurrent web server.

    WAL lets readers run while a write is in flight, and a busy timeout turns
    the occasional lock collision into a short wait instead of an exception.
    """
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    if url is None:
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{settings.database_path}"
    engine = create_engine(url, future=True)
    event.listen(engine, "connect", _configure_sqlite)
    return engine


_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session that commits on success and rolls back on failure."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all(engine: Engine | None = None) -> None:
    """Create the schema directly.

    Used by the tests and the first-run path; migrations own the real database.
    """
    Base.metadata.create_all(engine or get_engine())


def reset_state() -> None:
    """Drop cached engine and session factory, so tests can repoint the URL."""
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None
