"""Iron tyre fitting schedule: month calendar, booking and status changes."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..calendar_utils import (
    SLOT_TIMES,
    combine_slot,
    month_bounds,
    month_grid,
    month_key,
    month_label,
    parse_month,
    shift_month,
    today,
)
from ..db import get_db
from ..deps import require_staff
from ..flash import set_flash
from ..models import FITTING_STATUSES, FittingBooking, StaffUser, WheelBuild
from ..templating import render
from ..validators import clean_text, parse_date, parse_time

logger = logging.getLogger(__name__)

router = APIRouter()


def _bookable_wheels(db: Session) -> list[WheelBuild]:
    return list(
        db.scalars(
            select(WheelBuild)
            .options(joinedload(WheelBuild.client))
            .where(WheelBuild.status != "complete")
            .order_by(WheelBuild.reference)
        )
        .unique()
        .all()
    )


def _month_context(db: Session, anchor) -> dict:
    start, end = month_bounds(anchor)
    bookings = (
        db.scalars(
            select(FittingBooking)
            .options(joinedload(FittingBooking.wheel))
            .where(FittingBooking.scheduled_at >= start, FittingBooking.scheduled_at < end)
            .order_by(FittingBooking.scheduled_at)
        )
        .unique()
        .all()
    )
    by_day: dict[str, list[FittingBooking]] = {}
    for booking in bookings:
        by_day.setdefault(booking.scheduled_at.strftime("%Y-%m-%d"), []).append(booking)

    return {
        "anchor": anchor,
        "month_label": month_label(anchor),
        "month_key": month_key(anchor),
        "previous_month": month_key(shift_month(anchor, -1)),
        "next_month": month_key(shift_month(anchor, 1)),
        "weeks": month_grid(anchor),
        "by_day": by_day,
        "month_total": len(bookings),
        "agenda": list(bookings),
    }


@router.get("/schedule", include_in_schema=False)
async def schedule_page(
    request: Request,
    month: str = "",
    wheel_id: str = "",
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    anchor = parse_month(month)
    context = _month_context(db, anchor)
    wheels = _bookable_wheels(db)
    preselected = wheel_id if any(str(wheel.id) == wheel_id for wheel in wheels) else ""
    return render(
        request,
        "schedule/calendar.html",
        page_title="Iron tyre fittings",
        slot_times=SLOT_TIMES,
        wheels=wheels,
        values={"wheel_id": preselected, "date": today().strftime("%Y-%m-%d"), "time": SLOT_TIMES[0], "notes": ""},
        field_errors={},
        booking_error=None,
        **context,
    )


@router.post("/schedule", include_in_schema=False)
async def book_fitting(
    request: Request,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    form = await request.form()
    raw_date = clean_text(form.get("date"), 10)
    raw_time = clean_text(form.get("time"), 5)
    raw_wheel = clean_text(form.get("wheel_id"), 12)
    notes = clean_text(form.get("notes"), 600)

    errors: dict[str, str] = {}
    day, day_error = parse_date(raw_date)
    if day_error:
        errors["date"] = day_error
    slot, slot_error = parse_time(raw_time)
    if slot_error:
        errors["time"] = slot_error
    elif slot not in SLOT_TIMES:
        errors["time"] = "Choose one of the workshop's fitting times."

    wheel = None
    if raw_wheel == "":
        errors["wheel_id"] = "Choose the wheel that needs a tyre fitted."
    else:
        try:
            wheel = db.get(WheelBuild, int(raw_wheel))
        except ValueError:
            wheel = None
        if wheel is None:
            errors["wheel_id"] = "Choose a wheel from the list."

    anchor = parse_month(raw_date[:7] if len(raw_date) >= 7 else None)

    if not errors and day and slot:
        slot_at = combine_slot(day, slot)
        clash = db.scalar(select(FittingBooking).where(FittingBooking.scheduled_at == slot_at))
        if clash is not None:
            errors["time"] = (
                f"{slot} on {day.strftime('%d %b %Y')} is already taken by "
                f"{clash.wheel.reference if clash.wheel else 'another wheel'}."
            )
            anchor = parse_month(slot_at.strftime("%Y-%m"))
        else:
            booking = FittingBooking(wheel_id=wheel.id, scheduled_at=slot_at, notes=notes, status="scheduled")
            db.add(booking)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                errors["time"] = f"{slot} on {day.strftime('%d %b %Y')} was just taken by another booking."
            else:
                set_flash(
                    request,
                    f"{wheel.reference} booked for an iron tyre fitting at {slot} on {day.strftime('%d %b %Y')}.",
                )
                return RedirectResponse(f"/schedule?month={slot_at.strftime('%Y-%m')}", status_code=303)

    context = _month_context(db, anchor)
    return render(
        request,
        "schedule/calendar.html",
        status_code=422,
        page_title="Iron tyre fittings",
        slot_times=SLOT_TIMES,
        wheels=_bookable_wheels(db),
        values={"wheel_id": raw_wheel, "date": raw_date, "time": raw_time, "notes": notes},
        field_errors=errors,
        booking_error=None,
        **context,
    )


@router.post("/schedule/{booking_id}/status", include_in_schema=False)
async def update_fitting_status(
    request: Request,
    booking_id: int,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    form = await request.form()
    requested = clean_text(form.get("status"), 20)
    booking = db.get(FittingBooking, booking_id)
    if booking is None:
        set_flash(request, "That fitting is no longer on the schedule.", "error")
        return RedirectResponse(f"/schedule?month={month_key(today())}", status_code=303)

    if requested not in FITTING_STATUSES:
        set_flash(request, "Choose whether the fitting is completed or cancelled.", "error")
        return RedirectResponse(
            f"/schedule?month={booking.scheduled_at.strftime('%Y-%m')}", status_code=303
        )

    booking.status = requested
    db.commit()
    label = {"completed": "marked complete", "cancelled": "cancelled", "scheduled": "reopened"}[requested]
    set_flash(request, f"{booking.wheel.reference} fitting on {booking.date_display} {label}.")
    return RedirectResponse(
        f"/schedule?month={booking.scheduled_at.strftime('%Y-%m')}", status_code=303
    )
