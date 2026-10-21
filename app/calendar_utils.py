"""Month-grid maths for the iron tyre fitting calendar (no third-party deps)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
SLOT_TIMES = tuple(f"{hour:02d}:00" for hour in range(8, 18))


@dataclass(frozen=True)
class DayCell:
    day: date
    in_month: bool
    is_today: bool


def today() -> date:
    return date.today()


def now() -> datetime:
    return datetime.now()


def parse_month(raw: str | None) -> date:
    """Parse ``YYYY-MM`` into the first day of that month; fall back to today."""
    text = (raw or "").strip()
    if len(text) == 7:
        try:
            year, month = text.split("-")
            return date(int(year), int(month), 1)
        except (ValueError, TypeError):
            pass
    current = today()
    return current.replace(day=1)


def month_key(anchor: date) -> str:
    return anchor.strftime("%Y-%m")


def month_label(anchor: date) -> str:
    return f"{MONTH_NAMES[anchor.month - 1]} {anchor.year}"


def shift_month(anchor: date, delta: int) -> date:
    index = (anchor.year * 12 + (anchor.month - 1)) + delta
    return date(index // 12, index % 12 + 1, 1)


def month_bounds(anchor: date) -> tuple[datetime, datetime]:
    """Half-open [start, end) datetimes covering the whole month."""
    first = datetime.combine(anchor, time.min)
    next_month = shift_month(anchor, 1)
    return first, datetime.combine(next_month, time.min)


def month_grid(anchor: date) -> list[list[DayCell]]:
    """Six weeks of day cells, Monday-first, padding the month edges."""
    weeks: list[list[DayCell]] = []
    first_weekday = anchor.weekday()  # Monday == 0
    grid_start = anchor - timedelta(days=first_weekday)
    current = today()
    for week_index in range(6):
        row: list[DayCell] = []
        for day_index in range(7):
            day = grid_start + timedelta(days=week_index * 7 + day_index)
            row.append(
                DayCell(day=day, in_month=day.month == anchor.month, is_today=day == current)
            )
        weeks.append(row)
    return weeks


def month_fitting_count(anchor: date) -> int:
    """Number of days in the month, used by the calendar's agenda fallback."""
    return calendar.monthrange(anchor.year, anchor.month)[1]


def combine_slot(day: date, slot: str) -> datetime:
    hour, minute = (int(part) for part in slot.split(":"))
    return datetime.combine(day, time(hour=hour, minute=minute))


def human_date(value: date | datetime) -> str:
    return value.strftime("%d %b %Y")


def human_datetime(value: datetime) -> str:
    return value.strftime("%d %b %Y · %H:%M")
