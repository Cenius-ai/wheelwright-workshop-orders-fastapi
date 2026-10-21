"""Iron tyre fitting schedule: month grid, booking, duplicate rejection, status."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.calendar_utils import month_key, parse_month, shift_month
from app.models import FittingBooking, WheelBuild


def _open_wheel(session) -> WheelBuild:
    return session.scalar(select(WheelBuild).where(WheelBuild.status != "complete").order_by(WheelBuild.id))


def _stat_value(html: str, label: str) -> int:
    match = re.search(
        r'<span class="stat__label">' + re.escape(label) + r'</span>\s*<span class="stat__value">(\d+)</span>',
        html,
    )
    assert match, f"stat card {label!r} not found on the overview"
    return int(match.group(1))


@pytest.fixture()
def open_wheel(session):
    return _open_wheel(session)


def test_schedule_renders_the_current_month_with_seeded_fittings(signed_in_client):
    response = signed_in_client.get("/schedule")
    assert response.status_code == 200
    assert parse_month(None).strftime("%B %Y") in response.text
    assert "Book an iron tyre fitting" in response.text
    assert "08:00" in response.text
    assert 'aria-label="Next month"' in response.text


def test_next_month_link_moves_the_grid(signed_in_client):
    current = parse_month(None)
    following = shift_month(current, 1)

    this_page = signed_in_client.get(f"/schedule?month={month_key(current)}")
    assert current.strftime("%B %Y") in this_page.text

    next_page = signed_in_client.get(f"/schedule?month={month_key(following)}")
    assert next_page.status_code == 200
    assert following.strftime("%B %Y") in next_page.text
    assert month_key(current) in next_page.text  # the "previous" link points back


def test_booking_a_free_slot_persists(signed_in_client, session, open_wheel):
    booked = session.scalar(
        select(func.count(FittingBooking.id)).where(FittingBooking.wheel_id == open_wheel.id)
    )
    target_day = date.today() + timedelta(days=40)
    response = signed_in_client.post(
        "/schedule",
        data={
            "wheel_id": str(open_wheel.id),
            "date": target_day.strftime("%Y-%m-%d"),
            "time": "17:00",
            "notes": "Late slot for the museum wheel.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert month_key(target_day) in response.headers["location"]

    session.expire_all()
    after = session.scalar(
        select(func.count(FittingBooking.id)).where(FittingBooking.wheel_id == open_wheel.id)
    )
    assert after == (booked or 0) + 1

    month_page = signed_in_client.get(f"/schedule?month={month_key(target_day)}")
    assert "17:00" in month_page.text
    assert open_wheel.reference in month_page.text


def test_duplicate_slot_is_rejected_and_named(signed_in_client, session):
    existing = session.scalar(
        select(FittingBooking)
        .where(FittingBooking.status == "scheduled")
        .order_by(FittingBooking.scheduled_at)
    )
    assert existing is not None
    before = session.scalar(select(func.count(FittingBooking.id)))

    response = signed_in_client.post(
        "/schedule",
        data={
            "wheel_id": str(existing.wheel_id),
            "date": existing.scheduled_at.strftime("%Y-%m-%d"),
            "time": existing.scheduled_at.strftime("%H:%M"),
            "notes": "Should not be created.",
        },
    )
    assert response.status_code == 422
    assert "is already taken by" in response.text
    assert existing.scheduled_at.strftime("%H:%M") in response.text

    session.expire_all()
    assert (session.scalar(select(func.count(FittingBooking.id))) or 0) == before


def test_booking_requires_a_wheel(signed_in_client):
    response = signed_in_client.post(
        "/schedule", data={"wheel_id": "", "date": date.today().strftime("%Y-%m-%d"), "time": "09:00"}
    )
    assert response.status_code == 422
    assert "Choose the wheel that needs a tyre fitted." in response.text


def test_marking_a_fitting_complete_persists_and_updates_the_cells(signed_in_client, session):
    booking = session.scalar(
        select(FittingBooking)
        .where(
            FittingBooking.status == "scheduled",
            FittingBooking.scheduled_at >= datetime.combine(date.today(), time.min),
        )
        .order_by(FittingBooking.scheduled_at)
    )
    assert booking is not None

    response = signed_in_client.post(
        f"/schedule/{booking.id}/status", data={"status": "completed"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert f"/schedule?month={booking.scheduled_at.strftime('%Y-%m')}" in response.headers["location"]

    session.expire_all()
    assert session.get(FittingBooking, booking.id).status == "completed"

    month_page = signed_in_client.get(f"/schedule?month={booking.scheduled_at.strftime('%Y-%m')}")
    assert "Completed" in month_page.text


def test_cancelling_a_fitting_lowers_the_upcoming_count(signed_in_client, session):
    booking = session.scalar(
        select(FittingBooking)
        .where(FittingBooking.status == "scheduled", FittingBooking.scheduled_at >= datetime.now())
        .order_by(FittingBooking.scheduled_at)
    )
    assert booking is not None

    before = _stat_value(signed_in_client.get("/").text, "Upcoming fittings")
    response = signed_in_client.post(
        f"/schedule/{booking.id}/status", data={"status": "cancelled"}, follow_redirects=False
    )
    assert response.status_code == 303

    session.expire_all()
    assert session.get(FittingBooking, booking.id).status == "cancelled"
    after = _stat_value(signed_in_client.get("/").text, "Upcoming fittings")
    assert after == before - 1

    month_page = signed_in_client.get(f"/schedule?month={booking.scheduled_at.strftime('%Y-%m')}")
    assert "Cancelled" in month_page.text


def test_an_invalid_status_value_is_refused(signed_in_client, session):
    booking = session.scalar(select(FittingBooking).order_by(FittingBooking.id))
    response = signed_in_client.post(
        f"/schedule/{booking.id}/status", data={"status": "exploded"}, follow_redirects=False
    )
    assert response.status_code == 303
    session.expire_all()
    assert session.get(FittingBooking, booking.id).status == "scheduled"


def test_an_empty_month_still_renders(signed_in_client):
    response = signed_in_client.get("/schedule?month=2035-02")
    assert response.status_code == 200
    assert "February 2035" in response.text
    assert "No fittings are booked in February 2035" in response.text


def test_a_malformed_month_falls_back_to_this_month(signed_in_client):
    response = signed_in_client.get("/schedule?month=not-a-month")
    assert response.status_code == 200
    assert parse_month(None).strftime("%B %Y") in response.text
