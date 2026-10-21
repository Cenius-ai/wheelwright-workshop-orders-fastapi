"""Jinja2 environment: one render helper that always carries the request."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from .calendar_utils import human_date, human_datetime, now as workshop_now
from .flash import pop_flash
from .models import BUILD_STATUS_LABELS, FITTING_STATUS_LABELS

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.filters["human_date"] = human_date
templates.env.filters["human_datetime"] = human_datetime
templates.env.globals["build_status_labels"] = BUILD_STATUS_LABELS
templates.env.globals["fitting_status_labels"] = FITTING_STATUS_LABELS


def relative_day(value: date) -> str:
    """Humanised date: Today / Yesterday / N days ago, then an absolute date."""
    delta = (date.today() - value).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    if 1 < delta <= 13:
        return f"{delta} days ago"
    return human_date(value)


templates.env.filters["relative_day"] = relative_day


def _nav_counts(request: Request) -> dict[str, int]:
    """Small live numbers beside the rail navigation, computed at most once per request."""
    cached = getattr(request.state, "nav_counts", None)
    if cached is not None:
        return cached

    from .db import SessionLocal
    from .models import Client, FittingBooking, WheelBuild

    counts: dict[str, int] = {}
    try:
        with SessionLocal() as db:
            counts = {
                "open_builds": db.scalar(
                    select(func.count(WheelBuild.id)).where(WheelBuild.status != "complete")
                )
                or 0,
                "upcoming_fittings": db.scalar(
                    select(func.count(FittingBooking.id)).where(
                        FittingBooking.status == "scheduled",
                        FittingBooking.scheduled_at >= workshop_now(),
                    )
                )
                or 0,
                "clients": db.scalar(select(func.count(Client.id))) or 0,
            }
    except SQLAlchemyError:
        logger.exception("could not compute the rail counts")
        counts = {}
    request.state.nav_counts = counts
    return counts


def render(
    request: Request,
    template_name: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    **context: Any,
) -> HTMLResponse:
    """Render a template with the request, the current staff user and any flash."""
    payload = {
        "request": request,
        "current_user": getattr(request.state, "current_user", None),
        "nav_counts": _nav_counts(request),
        "flash": pop_flash(request),
        "today": date.today(),
        "now": datetime.now(),
        **context,
    }
    return templates.TemplateResponse(
        request, template_name, payload, status_code=status_code, headers=headers
    )


def render_error(
    request: Request,
    *,
    code: int,
    title: str,
    detail: str,
    back_href: str = "/",
    back_label: str = "Back to the workshop overview",
) -> HTMLResponse:
    """Render an error page: inside the workshop shell when signed in."""
    signed_in = getattr(request.state, "current_user", None) is not None
    template_name = "404.html" if signed_in else "error_plain.html"
    return render(
        request,
        template_name,
        status_code=code,
        page_title=title,
        code=code,
        detail=detail,
        back_href=back_href,
        back_label=back_label,
    )
