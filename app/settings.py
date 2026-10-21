"""Runtime configuration for Wheelwright Workshop Orders.

Every value is read from the environment with a working default, so a fresh
clone boots with no .env file present. If a .env file exists (written by
install.sh with a generated session secret) it is read first, without ever
overriding a value the environment already provides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEV_SESSION_SECRET = "cenius-dev-6b1f4c8d2a97e350"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv(path: Path) -> None:
    """Minimal KEY=VALUE reader so the app needs no extra dependency."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _int_env(name: str, fallback: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


_load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    app_name: str = "Wheelwright Workshop Orders"
    secret_key: str = os.getenv("SESSION_SECRET") or DEV_SESSION_SECRET
    database_url: str = os.getenv("DATABASE_URL") or "sqlite:///./wheelwright.db"
    port: int = _int_env("PORT", 8000)
    session_cookie: str = os.getenv("SESSION_COOKIE_NAME") or "wheelwright_session"
    session_max_age: int = _int_env("SESSION_MAX_AGE", 60 * 60 * 12)
    # The preview and local runs are plain http, so the Secure flag is opt-in.
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"


settings = Settings()
