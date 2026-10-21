"""Workshop overview plus the app-wide security floor."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Client, FittingBooking, StaffUser, WheelBuild
from app.security import hash_password
from app.seed import ensure_seeded

from .conftest import reset_database

MONTH = date.today().strftime("%Y-%m")


def test_overview_shows_live_counts_and_recent_builds(signed_in_client, session):
    open_builds = session.scalar(
        select(func.count(WheelBuild.id)).where(WheelBuild.status != "complete")
    )
    clients = session.scalar(select(func.count(Client.id)))

    response = signed_in_client.get("/")
    assert response.status_code == 200
    assert "Open builds" in response.text
    assert "Upcoming fittings" in response.text
    assert "Heritage clients" in response.text
    assert f'<span class="stat__value">{open_builds}</span>' in response.text
    assert f'<span class="stat__value">{clients}</span>' in response.text
    assert "Recent builds" in response.text
    assert "CW-1046" in response.text


def test_todays_fittings_are_listed_with_time_and_reference(signed_in_client, session):
    start = datetime.combine(date.today(), time.min)
    todays = session.scalars(
        select(FittingBooking)
        .where(FittingBooking.scheduled_at >= start, FittingBooking.status == "scheduled")
        .order_by(FittingBooking.scheduled_at)
    ).all()
    assert todays, "the seed books fittings for today"

    response = signed_in_client.get("/")
    assert "Today's iron tyre fittings" in response.text
    assert todays[0].time_display in response.text
    assert todays[0].notes in response.text


def test_empty_workshop_invites_the_first_build(empty_client, session):
    session.add(
        StaffUser(
            name="Ada Rendall",
            email="ada@wheelwrightworkshop.co.uk",
            password_hash=hash_password("forgeandfire"),
            role="admin",
        )
    )
    session.commit()

    sign_in = empty_client.post(
        "/login",
        data={"email": "ada@wheelwrightworkshop.co.uk", "password": "forgeandfire"},
        follow_redirects=False,
    )
    assert sign_in.status_code == 303

    response = empty_client.get("/")
    assert response.status_code == 200
    assert "The build book is empty" in response.text
    assert 'href="/wheels/new"' in response.text
    assert "No fittings are booked for today." in response.text


def test_empty_build_list_offers_the_new_build_form(empty_client, session):
    session.add(
        StaffUser(
            name="Ada Rendall",
            email="ada@wheelwrightworkshop.co.uk",
            password_hash=hash_password("forgeandfire"),
            role="admin",
        )
    )
    session.commit()
    empty_client.post(
        "/login",
        data={"email": "ada@wheelwrightworkshop.co.uk", "password": "forgeandfire"},
        follow_redirects=False,
    )

    response = empty_client.get("/wheels")
    assert response.status_code == 200
    assert "No cartwheel builds yet" in response.text


def test_seed_is_idempotent():
    reset_database()
    assert ensure_seeded() is True

    def snapshot():
        with SessionLocal() as db_session:
            return (
                db_session.scalar(select(func.count(StaffUser.id))),
                db_session.scalar(select(func.count(Client.id))),
                db_session.scalar(select(func.count(WheelBuild.id))),
                db_session.scalar(select(func.count(FittingBooking.id))),
            )

    first = snapshot()
    assert ensure_seeded() is False
    assert snapshot() == first
    assert first[0] >= 1 and first[1] >= 8 and first[2] >= 8 and first[3] >= 8


def test_demo_account_is_seeded_and_hashed(session):
    user = session.scalar(select(StaffUser).where(StaffUser.email == "cenius@cenius.ai"))
    assert user is not None
    assert user.role == "admin"
    assert user.password_hash.startswith("pbkdf2_sha256$")
    assert "cenius" not in user.password_hash


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_are_sent(client):
    response = client.get("/login")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_cross_site_form_post_is_refused(client):
    response = client.post(
        "/login",
        data={"email": "cenius@cenius.ai", "password": "cenius"},
        headers={"origin": "https://evil.example"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_no_inline_scripts_or_handlers_are_used(client):
    """The CSP forbids inline script, so no page may rely on it."""
    signed_in = client.post(
        "/login", data={"email": "cenius@cenius.ai", "password": "cenius"}, follow_redirects=False
    )
    assert signed_in.status_code == 303

    for path in ["/login", "/", "/wheels", "/schedule", "/clients", "/wheels/new"]:
        body = client.get(path).text
        assert "<script>" not in body, path
        assert "onclick=" not in body, path
        assert "onchange=" not in body, path
        assert "<style" not in body, path
