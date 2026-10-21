"""Heritage commission clients: register list, add panel, detail and inline edit."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import require_staff
from ..flash import set_flash
from ..models import Client, StaffUser, WheelBuild
from ..templating import render, render_error
from ..validators import NOTES_MAX, clean_text, parse_email, parse_name, parse_phone

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_client(form) -> tuple[dict, dict[str, str]]:
    values = {
        "name": clean_text(form.get("name"), 160),
        "contact_email": clean_text(form.get("contact_email"), 254),
        "phone": clean_text(form.get("phone"), 40),
        "heritage_notes": clean_text(form.get("heritage_notes"), NOTES_MAX),
    }
    errors: dict[str, str] = {}

    name, name_error = parse_name(values["name"])
    if name_error:
        errors["name"] = name_error

    email, email_error = parse_email(values["contact_email"])
    if email_error:
        errors["contact_email"] = email_error

    phone, phone_error = parse_phone(values["phone"])
    if phone_error:
        errors["phone"] = phone_error

    parsed = {
        "name": name,
        "contact_email": email,
        "phone": phone,
        "heritage_notes": values["heritage_notes"],
    }
    return parsed, errors


def _register_rows(db: Session) -> list[dict]:
    rows = db.execute(
        select(Client, func.count(WheelBuild.id))
        .outerjoin(WheelBuild, WheelBuild.client_id == Client.id)
        .group_by(Client.id)
        .order_by(Client.name)
    ).all()
    return [{"client": client, "commission_count": count} for client, count in rows]


@router.get("/clients", include_in_schema=False)
async def list_clients(
    request: Request,
    q: str = "",
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    search = clean_text(q, 80)
    rows = _register_rows(db)
    total = len(rows)
    if search:
        needle = search.lower()
        rows = [
            row
            for row in rows
            if needle in row["client"].name.lower()
            or needle in (row["client"].contact_email or "").lower()
        ]

    return render(
        request,
        "clients/list.html",
        page_title="Heritage clients",
        page_subtitle="Commission briefs, contacts and commissioned wheels",
        rows=rows,
        total=total,
        search=search,
        values={"name": "", "contact_email": "", "phone": "", "heritage_notes": ""},
        field_errors={},
    )


@router.post("/clients", include_in_schema=False)
async def create_client(
    request: Request,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    form = await request.form()
    parsed, errors = _parse_client(form)

    if parsed["name"] and not errors.get("name"):
        existing = db.scalar(select(Client.id).where(func.lower(Client.name) == parsed["name"].lower()))
        if existing is not None:
            errors["name"] = "A client with that name is already on the register."

    if errors:
        rows = _register_rows(db)
        return render(
            request,
            "clients/list.html",
            status_code=422,
            page_title="Heritage clients",
            rows=rows,
            total=len(rows),
            search="",
            values={
                "name": clean_text(form.get("name"), 160),
                "contact_email": clean_text(form.get("contact_email"), 254),
                "phone": clean_text(form.get("phone"), 40),
                "heritage_notes": clean_text(form.get("heritage_notes"), NOTES_MAX),
            },
            field_errors=errors,
            panel_open=True,
        )

    client = Client(
        name=parsed["name"],
        contact_email=parsed["contact_email"],
        phone=parsed["phone"],
        heritage_notes=parsed["heritage_notes"],
    )
    db.add(client)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        rows = _register_rows(db)
        return render(
            request,
            "clients/list.html",
            status_code=422,
            page_title="Heritage clients",
            rows=rows,
            total=len(rows),
            search="",
            values={
                "name": clean_text(form.get("name"), 160),
                "contact_email": clean_text(form.get("contact_email"), 254),
                "phone": clean_text(form.get("phone"), 40),
                "heritage_notes": clean_text(form.get("heritage_notes"), NOTES_MAX),
            },
            field_errors={"name": "A client with that name is already on the register."},
            panel_open=True,
        )

    set_flash(request, f"{client.name} added to the heritage register.")
    return RedirectResponse(f"/clients/{client.id}", status_code=303)


def _load_client(db: Session, client_id: int) -> Client | None:
    return db.scalar(
        select(Client)
        .options(selectinload(Client.builds).joinedload(WheelBuild.client))
        .where(Client.id == client_id)
    )


@router.get("/clients/{client_id}", include_in_schema=False)
async def client_detail(
    request: Request,
    client_id: int,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    client = _load_client(db, client_id)
    if client is None:
        return render_error(
            request,
            code=404,
            title="Client not found",
            detail="No heritage client on the register has that number.",
            back_href="/clients",
            back_label="Back to heritage clients",
        )
    builds = sorted(client.builds, key=lambda build: build.created_at, reverse=True)
    return render(
        request,
        "clients/detail.html",
        page_title=client.name,
        client=client,
        builds=builds,
        field_errors={},
        submitted=None,
    )


@router.post("/clients/{client_id}", include_in_schema=False)
async def update_client(
    request: Request,
    client_id: int,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    client = _load_client(db, client_id)
    if client is None:
        return render_error(
            request,
            code=404,
            title="Client not found",
            detail="No heritage client on the register has that number.",
            back_href="/clients",
            back_label="Back to heritage clients",
        )

    form = await request.form()
    parsed, errors = _parse_client(form)

    if parsed["name"] and not errors.get("name"):
        clash = db.scalar(
            select(Client.id).where(
                func.lower(Client.name) == parsed["name"].lower(), Client.id != client.id
            )
        )
        if clash is not None:
            errors["name"] = "Another client already uses that name."

    if errors:
        return render(
            request,
            "clients/detail.html",
            status_code=422,
            page_title=client.name,
            client=client,
            builds=sorted(client.builds, key=lambda build: build.created_at, reverse=True),
            field_errors=errors,
            submitted={
                "name": clean_text(form.get("name"), 160),
                "contact_email": clean_text(form.get("contact_email"), 254),
                "phone": clean_text(form.get("phone"), 40),
                "heritage_notes": clean_text(form.get("heritage_notes"), NOTES_MAX),
            },
        )

    client.name = parsed["name"]
    client.contact_email = parsed["contact_email"]
    client.phone = parsed["phone"]
    client.heritage_notes = parsed["heritage_notes"]
    db.commit()

    set_flash(request, f"{client.name} updated.")
    return RedirectResponse(f"/clients/{client.id}", status_code=303)
