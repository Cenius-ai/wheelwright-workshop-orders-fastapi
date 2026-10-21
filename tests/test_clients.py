"""Heritage commission clients: register, add form, detail and inline edit."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Client


def test_client_list_shows_contact_details_and_commission_counts(signed_in_client):
    response = signed_in_client.get("/clients")
    assert response.status_code == 200
    assert "Bodmin Heritage Trust" in response.text
    assert "enquiries@bodminheritage.org.uk" in response.text
    # Bodmin has two seeded builds.
    assert "commissioned" in response.text


def test_missing_name_is_rejected_and_values_kept(signed_in_client, session):
    before = session.scalar(select(func.count(Client.id)))
    response = signed_in_client.post(
        "/clients",
        data={"name": "", "contact_email": "new@example.co.uk", "phone": "01872 000 000", "heritage_notes": "Brief"},
    )
    assert response.status_code == 422
    assert "Enter the client&#39;s name." in response.text or "Enter the client's name." in response.text
    assert 'value="new@example.co.uk"' in response.text
    assert (session.scalar(select(func.count(Client.id))) or 0) == before


def test_adding_a_client_lists_them_with_zero_commissions(signed_in_client, session):
    response = signed_in_client.post(
        "/clients",
        data={
            "name": "Wadebridge Old Wheels",
            "contact_email": "info@wadebridgeoldwheels.co.uk",
            "phone": "01208 555 121",
            "heritage_notes": "Two barrow wheels for the town trail.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/clients/")

    listing = signed_in_client.get("/clients")
    assert "Wadebridge Old Wheels" in listing.text

    created = session.scalar(select(Client).where(Client.name == "Wadebridge Old Wheels"))
    assert created is not None
    assert created.contact_email == "info@wadebridgeoldwheels.co.uk"


def test_client_detail_lists_their_builds(signed_in_client, session):
    bodmin = session.scalar(select(Client).where(Client.name == "Bodmin Heritage Trust"))
    response = signed_in_client.get(f"/clients/{bodmin.id}")
    assert response.status_code == 200
    assert "CW-1041" in response.text
    assert "CW-1042" in response.text
    assert "Heritage brief" in response.text


def test_inline_edit_persists_the_phone_number(signed_in_client, session):
    client_row = session.scalar(select(Client).where(Client.name == "Fiona Kernow"))
    response = signed_in_client.post(
        f"/clients/{client_row.id}",
        data={
            "name": "Fiona Kernow",
            "contact_email": "fiona.kernow@trembroath.co.uk",
            "phone": "07791 555 900",
            "heritage_notes": "Rebuild of the Trembroath tip cart.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    detail = signed_in_client.get(f"/clients/{client_row.id}")
    assert "07791 555 900" in detail.text

    listing = signed_in_client.get("/clients")
    assert "07791 555 900" in listing.text

    session.expire_all()
    assert session.get(Client, client_row.id).phone == "07791 555 900"


def test_client_without_builds_shows_an_empty_state(signed_in_client, session):
    client_row = Client(name = "St Neot Bell Fund", contact_email=None, phone=None, heritage_notes="")
    session.add(client_row)
    session.commit()

    response = signed_in_client.get(f"/clients/{client_row.id}")
    assert response.status_code == 200
    assert "No wheel builds are linked to this client yet." in response.text
    assert f"/wheels/new?client_id={client_row.id}" in response.text


def test_unknown_client_returns_a_404_page(signed_in_client):
    response = signed_in_client.get("/clients/4242")
    assert response.status_code == 404
    assert "Back to heritage clients" in response.text
