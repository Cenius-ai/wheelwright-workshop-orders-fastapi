"""Staff accounts, sessions and the signed-out guard."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import StaffUser

from .conftest import DEMO_EMAIL, DEMO_PASSWORD, sign_in

PROTECTED_PATHS = ["/", "/wheels", "/wheels/new", "/schedule", "/clients"]


def test_signed_out_pages_redirect_to_sign_in(client):
    for path in PROTECTED_PATHS:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303, path
        assert response.headers["location"].startswith("/login"), path


def test_login_page_shows_the_demo_credential(client):
    response = client.get("/login")
    assert response.status_code == 200
    body = response.text
    assert "Demo" in body
    assert DEMO_EMAIL in body
    assert DEMO_PASSWORD in body


def test_login_rejects_a_wrong_password_with_one_message(client):
    response = client.post(
        "/login", data={"email": DEMO_EMAIL, "password": "wrong-password"}, follow_redirects=False
    )
    assert response.status_code == 200
    assert "don&#39;t match" in response.text or "don't match" in response.text
    # The typed email is preserved, the password never is.
    assert f'value="{DEMO_EMAIL}"' in response.text
    assert 'value="wrong-password"' not in response.text


def test_login_requires_a_password(client):
    response = client.post("/login", data={"email": DEMO_EMAIL, "password": ""})
    assert response.status_code == 200
    assert "Enter your password." in response.text
    assert "dashboard" not in response.headers.get("location", "")


def test_login_success_opens_the_overview(client):
    response = sign_in(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    overview = client.get("/")
    assert overview.status_code == 200
    assert "Workshop overview" in overview.text
    assert "Cenius Ashby" in overview.text
    assert "Open builds" in overview.text


def test_login_returns_to_the_requested_page(client):
    blocked = client.get("/wheels", follow_redirects=False)
    assert blocked.headers["location"] == "/login?next=/wheels"

    response = client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "next": "/wheels"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/wheels"


def test_login_ignores_an_offsite_next_target(client):
    response = client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "next": "https://evil.example/"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/"


def test_sign_out_clears_the_session(signed_in_client):
    response = signed_in_client.post("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    blocked = signed_in_client.get("/", follow_redirects=False)
    assert blocked.status_code == 303


def test_session_cookie_is_httponly_and_lax(client):
    response = sign_in(client)
    cookie_header = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "secure" not in cookie_header  # plain-http preview must keep the cookie


def test_first_registered_account_becomes_admin(empty_client, session):
    response = empty_client.post(
        "/register",
        data={
            "name": "Ada Rendall",
            "email": "ada@wheelwrightworkshop.co.uk",
            "password": "forgeandfire",
            "confirm_password": "forgeandfire",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    first = session.scalar(select(StaffUser).where(StaffUser.email == "ada@wheelwrightworkshop.co.uk"))
    assert first is not None
    assert first.role == "admin"
    assert first.password_hash != "forgeandfire"
    assert first.password_hash.startswith("pbkdf2_sha256$")

    empty_client.post("/logout", follow_redirects=False)
    empty_client.post(
        "/register",
        data={
            "name": "Tom Vearncombe",
            "email": "tom@wheelwrightworkshop.co.uk",
            "password": "spoketimber",
            "confirm_password": "spoketimber",
        },
        follow_redirects=False,
    )
    session.expire_all()
    second = session.scalar(select(StaffUser).where(StaffUser.email == "tom@wheelwrightworkshop.co.uk"))
    assert second is not None
    assert second.role == "staff"


def test_register_validation_keeps_the_typed_values(empty_client, session):
    response = empty_client.post(
        "/register",
        data={
            "name": "Ada Rendall",
            "email": "ada@wheelwrightworkshop.co.uk",
            "password": "forgeandfire",
            "confirm_password": "different",
        },
    )
    assert response.status_code == 200
    assert "don&#39;t match" in response.text or "don't match" in response.text
    assert 'value="Ada Rendall"' in response.text
    assert 'value="ada@wheelwrightworkshop.co.uk"' in response.text
    assert (session.scalar(select(func.count(StaffUser.id))) or 0) == 0


def test_register_rejects_a_duplicate_email(empty_client, session):
    for _ in range(2):
        response = empty_client.post(
            "/register",
            data={
                "name": "Ada Rendall",
                "email": "ada@wheelwrightworkshop.co.uk",
                "password": "forgeandfire",
                "confirm_password": "forgeandfire",
            },
            follow_redirects=False,
        )
    assert response.status_code == 200
    assert "already uses that email address" in response.text
    assert (session.scalar(select(func.count(StaffUser.id))) or 0) == 1
