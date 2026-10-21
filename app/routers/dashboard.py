"""Workshop overview — the home page."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from ..calendar_utils import now as workshop_now
from ..db import get_db
from ..deps import require_staff
from ..models import Client, FittingBooking, StaffUser, WheelBuild
from ..templating import render

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", include_in_schema=False)
async def home(
    request: Request,
    user: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
):
    current = workshop_now()
    day_start = datetime.combine(current.date(), time.min)
    day_end = day_start + timedelta(days=1)

    try:
        open_builds = db.scalar(
            select(func.count(WheelBuild.id)).where(WheelBuild.status != "complete")
        )
        upcoming_fittings = db.scalar(
            select(func.count(FittingBooking.id)).where(
                FittingBooking.status == "scheduled",
                FittingBooking.scheduled_at >= current,
            )
        )
        client_count = db.scalar(select(func.count(Client.id)))
        todays_fittings = (
            db.scalars(
                select(FittingBooking)
                .options(joinedload(FittingBooking.wheel))
                .where(
                    FittingBooking.status == "scheduled",
                    FittingBooking.scheduled_at >= day_start,
                    FittingBooking.scheduled_at < day_end,
                )
                .order_by(FittingBooking.scheduled_at)
            )
            .unique()
            .all()
        )
        recent_builds = (
            db.scalars(
                select(WheelBuild)
                .options(joinedload(WheelBuild.client))
                .order_by(WheelBuild.created_at.desc(), WheelBuild.id.desc())
                .limit(6)
            )
            .unique()
            .all()
        )
        total_builds = db.scalar(select(func.count(WheelBuild.id))) or 0
    except SQLAlchemyError:
        logger.exception("overview query failed for staff user %s", user.id)
        return render(
            request,
            "dashboard.html",
            status_code=500,
            page_title="Workshop overview",
            load_error="The workshop records could not be read just now.",
            open_builds=0,
            upcoming_fittings=0,
            client_count=0,
            todays_fittings=[],
            recent_builds=[],
            total_builds=0,
        )

    return render(
        request,
        "dashboard.html",
        page_title="Workshop overview",
        page_subtitle="Where the workshop stands today",
        load_error=None,
        open_builds=open_builds or 0,
        upcoming_fittings=upcoming_fittings or 0,
        client_count=client_count or 0,
        todays_fittings=list(todays_fittings),
        recent_builds=list(recent_builds),
        total_builds=total_builds,
    )
