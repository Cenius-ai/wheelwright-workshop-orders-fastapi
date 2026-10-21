"""SQLAlchemy engine and session plumbing.

The engine is created from ``settings.database_url`` (relative SQLite file by
default). ``configure_engine`` lets the test suite point the app at an isolated
database without re-importing the whole application.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str) -> Engine:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        _ensure_sqlite_directory(url)
    engine = create_engine(url, connect_args=connect_args, future=True)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def _ensure_sqlite_directory(url: str) -> None:
    """Create the parent directory of a relative SQLite file (sqlite won't)."""
    path = url.split("sqlite:///")[-1]
    if path in ("", ":memory:"):
        return
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


engine: Engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def configure_engine(url: str) -> None:
    """Rebind the module-level engine (used by the test suite)."""
    global engine, SessionLocal
    engine.dispose()
    engine = _make_engine(url)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create every table. Idempotent; safe on every boot."""
    from . import models  # noqa: F401  (registers the mappers)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
