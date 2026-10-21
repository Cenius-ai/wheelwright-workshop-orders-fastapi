"""Idempotent demo seed for Wheelwright Workshop Orders.

Run directly with ``python3 -m app.seed`` (or ``python3 -m seed`` from the
project root). It creates the schema if needed, then check-before-insert seeds
staff accounts, heritage clients, cartwheel builds and iron tyre fittings. It
never starts the HTTP server.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import db as db_module
from .db import init_db
from .models import Client, FittingBooking, StaffUser, WheelBuild
from .security import hash_password
from .seed_data import BUILDS, CLIENTS, FITTINGS, STAFF

logger = logging.getLogger("wheelwright.seed")


def _seed_staff(db: Session) -> dict[str, StaffUser]:
    people: dict[str, StaffUser] = {}
    for entry in STAFF:
        user = db.scalar(select(StaffUser).where(func.lower(StaffUser.email) == entry["email"].lower()))
        if user is None:
            user = StaffUser(
                name=entry["name"],
                email=entry["email"].lower(),
                password_hash=hash_password(entry["password"]),
                role=entry["role"],
            )
            db.add(user)
            db.flush()
            logger.info("seeded staff account %s", user.email)
        people[entry["email"]] = user
    return people


def _seed_clients(db: Session) -> dict[str, Client]:
    clients: dict[str, Client] = {}
    for entry in CLIENTS:
        client = db.scalar(select(Client).where(func.lower(Client.name) == entry["name"].lower()))
        if client is None:
            client = Client(
                name=entry["name"],
                contact_email=entry["contact_email"],
                phone=entry["phone"],
                heritage_notes=entry["heritage_notes"],
            )
            db.add(client)
            db.flush()
            logger.info("seeded heritage client %s", client.name)
        clients[entry["name"]] = client
    return clients


def _seed_builds(
    db: Session, staff: dict[str, StaffUser], clients: dict[str, Client]
) -> dict[str, WheelBuild]:
    builds: dict[str, WheelBuild] = {}
    author = staff.get("cenius@cenius.ai") or next(iter(staff.values()))
    now = datetime.now().replace(second=0, microsecond=0)

    for reference, client_name, felloes, spokes, diameter, status, days_ago, notes in BUILDS:
        build = db.scalar(select(WheelBuild).where(WheelBuild.reference == reference))
        if build is None:
            client = clients.get(client_name)
            build = WheelBuild(
                reference=reference,
                client_id=client.id if client is not None else None,
                felloe_count=felloes,
                spoke_count=spokes,
                diameter_inches=diameter,
                status=status,
                notes=notes,
                created_by_id=author.id,
                created_at=now - timedelta(days=days_ago),
            )
            db.add(build)
            db.flush()
            logger.info("seeded build %s", build.reference)
        builds[reference] = build
    return builds


def _seed_fittings(db: Session, builds: dict[str, WheelBuild]) -> None:
    # Fittings are demo content only: once the schedule holds anything (seeded or
    # booked by staff) the seed leaves it alone, so dates never drift on re-runs.
    if (db.scalar(select(func.count(FittingBooking.id))) or 0) > 0:
        return

    today = datetime.now().date()
    for reference, day_offset, slot, status, notes in FITTINGS:
        build = builds.get(reference)
        if build is None:
            continue
        hour, minute = (int(part) for part in slot.split(":"))
        slot_at = datetime.combine(today + timedelta(days=day_offset), time(hour=hour, minute=minute))
        exists = db.scalar(select(FittingBooking.id).where(FittingBooking.scheduled_at == slot_at))
        if exists is not None:
            continue
        db.add(
            FittingBooking(
                wheel_id=build.id,
                scheduled_at=slot_at,
                status=status,
                notes=notes,
                created_at=slot_at - timedelta(days=7),
            )
        )
        logger.info("seeded fitting %s at %s", reference, slot_at.strftime("%Y-%m-%d %H:%M"))


def ensure_seeded() -> bool:
    """Seed the demo workshop. Returns True when the database was empty."""
    with db_module.SessionLocal() as db:
        empty = (db.scalar(select(func.count(StaffUser.id))) or 0) == 0
        try:
            staff = _seed_staff(db)
            clients = _seed_clients(db)
            builds = _seed_builds(db, staff, clients)
            _seed_fittings(db, builds)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("seeding the demo workshop failed")
            raise
    return empty


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    init_db()
    was_empty = ensure_seeded()
    with db_module.SessionLocal() as db:
        staff_total = db.scalar(select(func.count(StaffUser.id))) or 0
        client_total = db.scalar(select(func.count(Client.id))) or 0
        build_total = db.scalar(select(func.count(WheelBuild.id))) or 0
        fitting_total = db.scalar(select(func.count(FittingBooking.id))) or 0
    state = "created" if was_empty else "already present"
    print(
        "Wheelwright seed complete ({state}): "
        f"{staff_total} staff, {client_total} clients, {build_total} builds, {fitting_total} fittings.".format(
            state=state
        )
    )
    print("Demo sign-in: cenius@cenius.ai / cenius")


if __name__ == "__main__":
    main()
