"""Cartwheel builds: list, create with felloe/spoke validation, edit, delete."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import FittingBooking, WheelBuild


def _build_payload(**overrides):
    payload = {
        "reference": "CW-1053",
        "client_id": "",
        "felloe_count": "12",
        "spoke_count": "14",
        "diameter_inches": "48",
        "status": "in_build",
        "notes": "Ash felloes, banded tyre.",
    }
    payload.update(overrides)
    return payload


def test_new_build_form_ships_usable_defaults(signed_in_client):
    """A new record only needs its own reference typed in."""
    body = signed_in_client.get("/wheels/new").text
    assert 'name="felloe_count"' in body and 'value="12"' in body
    assert 'name="spoke_count"' in body and 'value="14"' in body
    assert 'name="diameter_inches"' in body and 'value="48"' in body
    assert 'name="reference"' in body
    # The heritage client picker is populated from the register, first option = no commission.
    assert "No heritage commission" in body
    assert "Bodmin Heritage Trust" in body


def test_build_list_shows_seeded_builds(signed_in_client):
    response = signed_in_client.get("/wheels")
    assert response.status_code == 200
    assert "CW-1041" in response.text
    assert "Bodmin Heritage Trust" in response.text
    assert "Awaiting tyre" in response.text


def test_create_build_persists_and_renders_everywhere(signed_in_client, session):
    response = signed_in_client.post("/wheels", data=_build_payload(), follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/wheels/")

    build = session.scalar(select(WheelBuild).where(WheelBuild.reference == "CW-1053"))
    assert build is not None
    assert build.felloe_count == 12
    assert build.spoke_count == 14

    detail = signed_in_client.get(location)
    assert detail.status_code == 200
    assert "CW-1053" in detail.text

    listing = signed_in_client.get("/wheels")
    assert "CW-1053" in listing.text

    overview = signed_in_client.get("/")
    assert "CW-1053" in overview.text


def test_create_build_links_a_heritage_client(signed_in_client, session):
    from app.models import Client

    client_row = session.scalar(select(Client).where(Client.name == "Fiona Kernow"))
    response = signed_in_client.post(
        "/wheels", data=_build_payload(reference="CW-1060", client_id=str(client_row.id)), follow_redirects=False
    )
    assert response.status_code == 303

    session.expire_all()
    build = session.scalar(select(WheelBuild).where(WheelBuild.reference == "CW-1060"))
    assert build is not None and build.client_id == client_row.id

    client_page = signed_in_client.get(f"/clients/{client_row.id}")
    assert "CW-1060" in client_page.text

    listing = signed_in_client.get("/wheels")
    assert "Fiona Kernow" in listing.text


def test_out_of_range_spoke_count_is_rejected_with_a_field_message(signed_in_client, session):
    before = session.scalar(select(func.count(WheelBuild.id)))
    response = signed_in_client.post("/wheels", data=_build_payload(reference="CW-1061", spoke_count="0"))
    assert response.status_code == 422
    assert "between 8 and 24" in response.text
    # The typed values survive the failed submit.
    assert 'value="CW-1061"' in response.text
    assert (session.scalar(select(func.count(WheelBuild.id))) or 0) == before


def test_out_of_range_felloe_count_is_rejected(signed_in_client):
    response = signed_in_client.post("/wheels", data=_build_payload(reference="CW-1062", felloe_count="32"))
    assert response.status_code == 422
    assert "between 4 and 20" in response.text


def test_duplicate_reference_is_rejected(signed_in_client):
    response = signed_in_client.post("/wheels", data=_build_payload(reference="CW-1041"))
    assert response.status_code == 422
    assert "already uses that reference" in response.text


def test_status_change_shows_on_detail_and_list(signed_in_client, session):
    build = session.scalar(select(WheelBuild).where(WheelBuild.reference == "CW-1042"))
    response = signed_in_client.post(
        f"/wheels/{build.id}", data=_build_payload(reference="CW-1042", status="complete"), follow_redirects=False
    )
    assert response.status_code == 303

    detail = signed_in_client.get(f"/wheels/{build.id}")
    assert "Complete" in detail.text

    session.expire_all()
    updated = session.get(WheelBuild, build.id)
    assert updated.status == "complete"


def test_delete_removes_the_build_and_its_fittings(signed_in_client, session):
    build = session.scalar(select(WheelBuild).where(WheelBuild.reference == "CW-1041"))
    build_id = build.id
    booked = session.scalar(select(func.count(FittingBooking.id)).where(FittingBooking.wheel_id == build_id))
    assert booked and booked > 0

    response = signed_in_client.post(f"/wheels/{build_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/wheels"

    session.expire_all()
    assert session.get(WheelBuild, build_id) is None
    assert (
        session.scalar(select(func.count(FittingBooking.id)).where(FittingBooking.wheel_id == build_id)) or 0
    ) == 0
    listing = signed_in_client.get("/wheels")
    assert f'href="/wheels/{build_id}"' not in listing.text


def test_status_filter_narrows_the_list(signed_in_client):
    response = signed_in_client.get("/wheels?status=complete")
    assert response.status_code == 200
    assert "CW-1043" in response.text  # a completed seeded build
    assert "CW-1042" not in response.text  # an in-build seeded build


def test_unknown_build_returns_a_404_page(signed_in_client):
    response = signed_in_client.get("/wheels/9999")
    assert response.status_code == 404
    assert "Back to cartwheel builds" in response.text
