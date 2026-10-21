"""Shared pytest fixtures: an isolated SQLite file and a TestClient."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_DB = Path(__file__).resolve().parent / "wheelwright_test.db"

# Configure the app before importing it: a throwaway database, deterministic secret.
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SESSION_SECRET"] = "test-session-secret-not-for-production"
os.environ["COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app import db as db_module  # noqa: E402
from app import models  # noqa: E402,F401  (register the mappers)
from app.main import app  # noqa: E402
from app.seed import ensure_seeded  # noqa: E402

DEMO_EMAIL = "cenius@cenius.ai"
DEMO_PASSWORD = "cenius"


def reset_database() -> None:
    db_module.configure_engine(os.environ["DATABASE_URL"])
    db_module.Base.metadata.drop_all(bind=db_module.engine)
    db_module.Base.metadata.create_all(bind=db_module.engine)


@pytest.fixture()
def client():
    """A client over a freshly seeded workshop database."""
    reset_database()
    ensure_seeded()
    return TestClient(app)


@pytest.fixture()
def empty_client():
    """A client over an empty, migrated database (no demo rows)."""
    reset_database()
    return TestClient(app)


@pytest.fixture()
def session():
    """A raw SQLAlchemy session for assertions against the test database."""
    with db_module.SessionLocal() as db_session:
        yield db_session


def sign_in(test_client: TestClient, email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD):
    return test_client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )


@pytest.fixture()
def signed_in_client(client):
    response = sign_in(client)
    assert response.status_code == 303
    return client
