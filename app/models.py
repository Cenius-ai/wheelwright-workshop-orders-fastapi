"""ORM models for the workshop: staff, heritage clients, wheels and fittings."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

BUILD_STATUSES = ("in_build", "awaiting_tyre", "complete")
BUILD_STATUS_LABELS = {
    "in_build": "In build",
    "awaiting_tyre": "Awaiting tyre",
    "complete": "Complete",
}

FITTING_STATUSES = ("scheduled", "completed", "cancelled")
FITTING_STATUS_LABELS = {
    "scheduled": "Scheduled",
    "completed": "Completed",
    "cancelled": "Cancelled",
}


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="staff")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    builds: Mapped[list["WheelBuild"]] = relationship(back_populates="created_by")

    __table_args__ = (CheckConstraint("role IN ('admin', 'staff')", name="ck_staff_role"),)

    @property
    def first_name(self) -> str:
        return self.name.split(" ")[0]

    @property
    def initials(self) -> str:
        parts = [part for part in self.name.split(" ") if part]
        return "".join(part[0].upper() for part in parts[:2]) or "W"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    heritage_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    builds: Mapped[list["WheelBuild"]] = relationship(back_populates="client")

    @property
    def contact_line(self) -> str:
        parts = [value for value in (self.contact_email, self.phone) if value]
        return " · ".join(parts) if parts else "No contact details recorded"


class WheelBuild(Base):
    __tablename__ = "wheel_builds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    felloe_count: Mapped[int] = mapped_column(Integer, nullable=False)
    spoke_count: Mapped[int] = mapped_column(Integer, nullable=False)
    diameter_inches: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False, default=48.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_build", index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("staff_users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True)

    client: Mapped[Client | None] = relationship(back_populates="builds")
    created_by: Mapped[StaffUser] = relationship(back_populates="builds")
    fittings: Mapped[list["FittingBooking"]] = relationship(
        back_populates="wheel", cascade="all, delete-orphan", order_by="FittingBooking.scheduled_at"
    )

    __table_args__ = (
        CheckConstraint("felloe_count BETWEEN 4 AND 20", name="ck_wheel_felloes"),
        CheckConstraint("spoke_count BETWEEN 8 AND 24", name="ck_wheel_spokes"),
        CheckConstraint("status IN ('in_build', 'awaiting_tyre', 'complete')", name="ck_wheel_status"),
    )

    @property
    def status_label(self) -> str:
        return BUILD_STATUS_LABELS.get(self.status, self.status)

    @property
    def client_name(self) -> str:
        return self.client.name if self.client else "Unassigned commission"

    @property
    def diameter_display(self) -> str:
        return f"{float(self.diameter_inches):.1f} in"

    @property
    def is_complete(self) -> bool:
        return self.status == "complete"


class FittingBooking(Base):
    __tablename__ = "fitting_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wheel_id: Mapped[int] = mapped_column(
        ForeignKey("wheel_builds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled", index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    wheel: Mapped[WheelBuild] = relationship(back_populates="fittings")

    __table_args__ = (
        UniqueConstraint("scheduled_at", name="uq_fitting_slot"),
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled')", name="ck_fitting_status"
        ),
    )

    @property
    def status_label(self) -> str:
        return FITTING_STATUS_LABELS.get(self.status, self.status)

    @property
    def time_display(self) -> str:
        return self.scheduled_at.strftime("%H:%M")

    @property
    def date_display(self) -> str:
        return self.scheduled_at.strftime("%d %b %Y")
