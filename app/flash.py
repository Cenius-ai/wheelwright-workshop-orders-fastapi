"""One-shot flash messages carried in the signed session cookie."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

FLASH_KEY = "flash"


@dataclass(frozen=True)
class Flash:
    message: str
    kind: str = "success"

    @property
    def css_class(self) -> str:
        return f"notice notice--{self.kind}"


def set_flash(request: Request, message: str, kind: str = "success") -> None:
    request.session[FLASH_KEY] = {"message": message, "kind": kind}


def pop_flash(request: Request) -> Flash | None:
    raw = request.session.pop(FLASH_KEY, None)
    if not isinstance(raw, dict):
        return None
    message = raw.get("message")
    if not message:
        return None
    return Flash(message=str(message), kind=str(raw.get("kind") or "success"))
