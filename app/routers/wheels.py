"""Cartwheel builds: list, create, detail/edit, delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from ..db import get_db
from ..deps import require_staff
from ..flash import set_flash
from ..models import BUILD_STATUSES, Client, StaffUser, WheelBuild
from ..templating import render, render_error
from ..validators import (
    NOTES_MAX,
    clean_text,
    parse_decimal,
    parse_reference,
    parse_status,
    parse_whole_number,
)

logger = logging.getLogger(__name__)

router = APIRouter()

STATUS_ORDER = case(
    (WheelBuild.status == "in_build", 0),
    (WheelBuild.status == "awaiting_tyre", 1),
    else_=2,
)


def _status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(select(WheelBuild.status, func.count(WheelBuild.id)).group_by(WheelBuild.status))
    counts = {status: 0 for status in BUILD_STATUSES}
    for status, total in rows:
        counts[status] = total
    return counts


def _client_options(db: Session) -> list[Client]:
    return list(db.scalars(select(Client).order_by(Client.name)).all())


def _resolve_client(db: Session, raw: str | None) -> tuple[Client | None, str | None]:
    text = clean_text(raw, 12)
    if text == "":
        return None, None
    try:
        client_id = int(text)
    except ValueError:
        return None, "Choose a heritage client from the list."
    client = db.get(Client, client_id)
    if client is None:
        return None, "Choose a heritage client from the list."
    return client, None


def _parse_build(db: Session, form) -> tuple[dict, dict[str, str], Client | None]:
    """Validate a build form once, shared by create and update."""
    values = {
        "reference": clean_text(form.get("reference"), 40).upper(),
        "client_id": clean_text(form.get("client_id"), 12),
        "felloe_count": clean_text(form.get("felloe_count"), 12),
        "spoke_count": clean_text(form.get("spoke_count"), 12),
        "diameter_inches": clean_text(form.get("diameter_inches"), 12),
        "status": parse_status(form.get("status"), BUILD_STATUSES, "in_build"),
        "notes": clean_text(form.get("notes"), NOTES_MAX),
    }
    errors: dict[str, str] = {}

    reference, reference_error = parse_reference(values["reference"])
    if reference_error:
        errors["reference"] = reference_error
    else:
        values["reference"] = reference

    felloe_count, felloe_error = parse_whole_number(values["felloe_count"], "felloes", 4, 20)
    if felloe_error:
        errors["felloe_count"] = felloe_error

    spoke_count, spoke_error = parse_whole_number(values["spoke_count"], "spokes", 8, 24)
    if spoke_error:
        errors["spoke_count"] = spoke_error

    diameter, diameter_error = parse_decimal(values["diameter_inches"], "diameter in inches", 24, 72)
    if diameter_error:
        errors["diameter_inches"] = diameter_error

    client, client_error = _resolve_client(db, values["client_id"])
    if client_error:
        errors["client_id"] = client_error

    parsed = {
        "reference": reference,
        "felloe_count": felloe_count,
        "spoke_count": spoke_count,
        "diameter_inches": diameter,
        "status": values["status"],
        "notes": values["notes"],
        "client": client,
    }
    return parsed, errors, client


def _reference_taken(db: Session, reference: str, exclude_id: int | None = None) -> bool:
    query = select(WheelBuild.id).where(func.upper(WheelBuild.reference) == reference.upper())
    if exclude_id is not None:
        query = query.where(WheelBuild.id != exclude_id)
    return db.scalar(query) is not None


@router.get("/wheels", include_in_schema=False)
async def list_builds(
    request: Request,
    status: list[str] = Query(default=[]),
    q: str = "",
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    selected_statuses = [value for value in status if value in BUILD_STATUSES]
    search = clean_text(q, 80)

    query = select(WheelBuild).options(joinedload(WheelBuild.client))
    if selected_statuses:
        query = query.where(WheelBuild.status.in_(selected_statuses))
    if search:
        like = f"%{search}%"
        query = query.outerjoin(Client).where(
            or_(
                WheelBuild.reference.ilike(like),
                Client.name.ilike(like),
                WheelBuild.notes.ilike(like),
            )
        )
    builds = (
        db.scalars(query.order_by(STATUS_ORDER, WheelBuild.created_at.desc()))
        .unique()
        .all()
    )

    load_error = None
    try:
        counts = _status_counts(db)
        total = db.scalar(select(func.count(WheelBuild.id))) or 0
    except SQLAlchemyError:
        logger.exception("build list query failed")
        counts = {status_name: 0 for status_name in BUILD_STATUSES}
        total = 0
        load_error = "The build list could not be read just now."

    return render(
        request,
        "wheels/list.html",
        page_title="Cartwheel builds",
        page_subtitle="Every wheel in the workshop, with felloe and spoke counts",
        builds=list(builds),
        counts=counts,
        total=total,
        selected_statuses=selected_statuses,
        search=search,
        load_error=load_error,
        filters_active=bool(selected_statuses or search),
    )


@router.get("/wheels/new", include_in_schema=False)
async def new_build_page(
    request: Request,
    client_id: str = "",
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return render(
        request,
        "wheels/form.html",
        page_title="Record a build",
        clients=_client_options(db),
        values={
            "reference": "",
            "client_id": clean_text(client_id, 12),
            # Workshop defaults so a new record only needs its own reference typed in.
            "felloe_count": "12",
            "spoke_count": "14",
            "diameter_inches": "48",
            "status": "in_build",
            "notes": "",
        },
        field_errors={},
    )


@router.post("/wheels", include_in_schema=False)
async def create_build(
    request: Request,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    form = await request.form()
    parsed, errors, _client = _parse_build(db, form)

    if not errors.get("reference") and _reference_taken(db, str(parsed["reference"])):
        errors["reference"] = "Another build already uses that reference."

    if errors:
        values = {key: clean_text(form.get(key), NOTES_MAX) for key in (
            "reference",
            "client_id",
            "felloe_count",
            "spoke_count",
            "diameter_inches",
            "notes",
        )}
        values["status"] = parsed["status"]
        return render(
            request,
            "wheels/form.html",
            status_code=422,
            page_title="Record a build",
            clients=_client_options(db),
            values=values,
            field_errors=errors,
        )

    build = WheelBuild(
        reference=parsed["reference"],
        client_id=parsed["client"].id if parsed["client"] else None,
        felloe_count=parsed["felloe_count"],
        spoke_count=parsed["spoke_count"],
        diameter_inches=parsed["diameter_inches"],
        status=parsed["status"],
        notes=parsed["notes"],
        created_by_id=user.id,
    )
    db.add(build)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("duplicate build reference rejected: %s", parsed["reference"])
        values = {key: clean_text(form.get(key), NOTES_MAX) for key in (
            "reference",
            "client_id",
            "felloe_count",
            "spoke_count",
            "diameter_inches",
            "notes",
        )}
        values["status"] = parsed["status"]
        return render(
            request,
            "wheels/form.html",
            status_code=422,
            page_title="Record a build",
            clients=_client_options(db),
            values=values,
            field_errors={"reference": "Another build already uses that reference."},
        )

    set_flash(request, f"Build {build.reference} recorded.")
    return RedirectResponse(f"/wheels/{build.id}", status_code=303)


def _load_build(db: Session, wheel_id: int) -> WheelBuild | None:
    return db.scalar(
        select(WheelBuild)
        .options(
            joinedload(WheelBuild.client),
            joinedload(WheelBuild.created_by),
            selectinload(WheelBuild.fittings),
        )
        .where(WheelBuild.id == wheel_id)
    )


@router.get("/wheels/{wheel_id}", include_in_schema=False)
async def build_detail(
    request: Request,
    wheel_id: int,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    build = _load_build(db, wheel_id)
    if build is None:
        return render_error(
            request,
            code=404,
            title="Build not found",
            detail="No cartwheel build carries that reference number.",
            back_href="/wheels",
            back_label="Back to cartwheel builds",
        )
    return render(
        request,
        "wheels/detail.html",
        page_title=build.reference,
        build=build,
        clients=_client_options(db),
        field_errors={},
        fittings=sorted(build.fittings, key=lambda booking: booking.scheduled_at),
    )


@router.post("/wheels/{wheel_id}", include_in_schema=False)
async def update_build(
    request: Request,
    wheel_id: int,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    build = _load_build(db, wheel_id)
    if build is None:
        return render_error(
            request,
            code=404,
            title="Build not found",
            detail="No cartwheel build carries that reference number.",
            back_href="/wheels",
            back_label="Back to cartwheel builds",
        )

    form = await request.form()
    parsed, errors, _client = _parse_build(db, form)
    if not errors.get("reference") and _reference_taken(db, str(parsed["reference"]), exclude_id=build.id):
        errors["reference"] = "Another build already uses that reference."

    if errors:
        return render(
            request,
            "wheels/detail.html",
            status_code=422,
            page_title=build.reference,
            build=build,
            clients=_client_options(db),
            field_errors=errors,
            submitted={
                "reference": clean_text(form.get("reference"), 40).upper(),
                "client_id": clean_text(form.get("client_id"), 12),
                "felloe_count": clean_text(form.get("felloe_count"), 12),
                "spoke_count": clean_text(form.get("spoke_count"), 12),
                "diameter_inches": clean_text(form.get("diameter_inches"), 12),
                "status": parsed["status"],
                "notes": clean_text(form.get("notes"), NOTES_MAX),
            },
            fittings=sorted(build.fittings, key=lambda booking: booking.scheduled_at),
        )

    build.reference = parsed["reference"]
    build.client_id = parsed["client"].id if parsed["client"] else None
    build.felloe_count = parsed["felloe_count"]
    build.spoke_count = parsed["spoke_count"]
    build.diameter_inches = parsed["diameter_inches"]
    build.status = parsed["status"]
    build.notes = parsed["notes"]
    db.commit()

    set_flash(request, f"Build {build.reference} updated.")
    return RedirectResponse(f"/wheels/{build.id}", status_code=303)


@router.post("/wheels/{wheel_id}/delete", include_in_schema=False)
async def delete_build(
    request: Request,
    wheel_id: int,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    build = db.get(WheelBuild, wheel_id)
    if build is None:
        set_flash(request, "That build was already removed.", "error")
        return RedirectResponse("/wheels", status_code=303)

    reference = build.reference
    db.delete(build)
    db.commit()
    set_flash(request, f"Build {reference} and its fittings were removed.", "error")
    return RedirectResponse("/wheels", status_code=303)
