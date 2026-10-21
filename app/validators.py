"""Small, explicit form validators shared by every POST handler.

Each helper returns ``(value, error)`` so the router can collect field-level
messages and re-render the form with the values the user typed.
"""

from __future__ import annotations

import re
from datetime import date, datetime

REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 /_-]*$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
NAME_MAX = 160
NOTES_MAX = 2000


def clean_text(raw: str | None, limit: int = 400) -> str:
    return (raw or "").strip()[:limit]


def parse_whole_number(
    raw: str | None, label: str, minimum: int, maximum: int
) -> tuple[int | None, str | None]:
    text = clean_text(raw, 12)
    if text == "":
        return None, f"Enter the number of {label}."
    try:
        value = int(text)
    except ValueError:
        return None, f"Enter a whole number of {label} between {minimum} and {maximum}."
    if value < minimum or value > maximum:
        return None, f"Enter a whole number of {label} between {minimum} and {maximum}."
    return value, None


def parse_decimal(
    raw: str | None, label: str, minimum: float, maximum: float
) -> tuple[float | None, str | None]:
    text = clean_text(raw, 12)
    if text == "":
        return None, f"Enter the {label}."
    try:
        value = float(text)
    except ValueError:
        return None, f"Enter the {label} as a number between {minimum:g} and {maximum:g}."
    if value < minimum or value > maximum:
        return None, f"Enter the {label} as a number between {minimum:g} and {maximum:g}."
    return round(value, 1), None


def parse_reference(raw: str | None) -> tuple[str | None, str | None]:
    text = clean_text(raw, 40)
    if text == "":
        return None, "Give this build a reference, for example CW-1042."
    if len(text) < 3:
        return None, "Use at least 3 characters for the reference."
    if not REFERENCE_PATTERN.match(text):
        return None, "Use letters, numbers, spaces, dashes or slashes only."
    return text.upper(), None


def parse_name(raw: str | None) -> tuple[str | None, str | None]:
    text = clean_text(raw, NAME_MAX)
    if text == "":
        return None, "Enter the client's name."
    if len(text) < 2:
        return None, "Use at least 2 characters for the name."
    return text, None


def parse_email(raw: str | None) -> tuple[str | None, str | None]:
    text = clean_text(raw, 254).lower()
    if text == "":
        return None, None
    if not EMAIL_PATTERN.match(text):
        return None, "Enter an email address like name@example.co.uk."
    return text, None


def parse_phone(raw: str | None) -> tuple[str | None, str | None]:
    text = clean_text(raw, 40)
    if text == "":
        return None, None
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) < 7:
        return None, "Enter a phone number with at least 7 digits."
    return text, None


def parse_status(raw: str | None, allowed: tuple[str, ...], fallback: str) -> str:
    value = clean_text(raw, 20)
    return value if value in allowed else fallback


def parse_date(raw: str | None) -> tuple[date | None, str | None]:
    text = clean_text(raw, 10)
    if text == "":
        return None, "Choose a date for the fitting."
    try:
        return datetime.strptime(text, "%Y-%m-%d").date(), None
    except ValueError:
        return None, "Choose a date in the form 2025-03-14."


def parse_time(raw: str | None) -> tuple[str | None, str | None]:
    text = clean_text(raw, 5)
    if text == "":
        return None, "Choose a start time."
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        return None, "Choose a start time from the list."
    return text, None
