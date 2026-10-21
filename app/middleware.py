"""ASGI middleware: security headers, cross-site POST guard, session user.

Written as pure ASGI middleware so the form body is never buffered — FastAPI
reads ``request.form()`` itself.
"""

from __future__ import annotations

from starlette.datastructures import Headers, MutableHeaders

from .db import SessionLocal
from .deps import SESSION_USER_KEY
from .models import StaffUser

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityHeadersMiddleware:
    """Attach the security header set to every response and reject cross-site POSTs."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["method"] in UNSAFE_METHODS and not _same_origin(scope):
            await _forbidden(send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _same_origin(scope) -> bool:
    """Browsers send Origin (or Referer) on form posts; a foreign origin is CSRF."""
    headers = Headers(scope=scope)
    host = headers.get("host", "")
    origin = headers.get("origin") or ""
    referer = headers.get("referer") or ""
    if origin:
        return _host_of(origin) == host
    if referer:
        return _host_of(referer) == host
    # No browser provenance header (curl, tests, some same-origin edge cases).
    return True


def _host_of(url: str) -> str:
    _, _, rest = url.partition("://")
    return rest.split("/", 1)[0]


async def _forbidden(send) -> None:
    body = b"Cross-site form submission refused."
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class CurrentUserMiddleware:
    """Resolve the signed-in staff member once per request for the page shell.

    Runs inside SessionMiddleware, so it only reads ``scope["session"]``.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            session = scope.get("session") or {}
            user_id = session.get(SESSION_USER_KEY)
            state = scope.setdefault("state", {})
            state.setdefault("current_user", None)
            if isinstance(user_id, int):
                db = SessionLocal()
                try:
                    user = db.get(StaffUser, user_id)
                    if user is not None:
                        # Detach eagerly-loaded columns, drop the connection.
                        db.expunge(user)
                        state["current_user"] = user
                finally:
                    db.close()
        await self.app(scope, receive, send)
