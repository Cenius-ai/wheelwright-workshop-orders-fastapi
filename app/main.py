"""Wheelwright Workshop Orders — FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import seed
from .db import init_db
from .deps import SignInRequired
from .middleware import CurrentUserMiddleware, SecurityHeadersMiddleware
from .routers import auth, clients, dashboard, schedule, wheels
from .settings import settings
from .templating import STATIC_DIR, render, render_error

logger = logging.getLogger("wheelwright")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Internal workshop tool for cartwheel builds, iron tyre fittings and heritage commissions.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_lifespan,
    )

    # Most recently added middleware is outermost: headers -> session -> user.
    app.add_middleware(CurrentUserMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie,
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.cookie_secure,
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(wheels.router)
    app.include_router(clients.router)
    app.include_router(schedule.router)

    @app.exception_handler(SignInRequired)
    async def _redirect_to_sign_in(request: Request, exc: SignInRequired) -> RedirectResponse:
        target = exc.next_path or "/"
        if target.startswith("/login") or target.startswith("/register"):
            return RedirectResponse("/login", status_code=303)
        return RedirectResponse(f"/login?next={quote(target, safe='/')}", status_code=303)

    @app.exception_handler(RequestValidationError)
    async def _bad_request(request: Request, exc: RequestValidationError):
        logger.info("rejected malformed request on %s: %s", request.url.path, exc.errors()[:1])
        return render_error(
            request,
            code=400,
            title="That request was not understood",
            detail="The page address or form values were not in a shape the workshop understands.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return render_error(
                request,
                code=404,
                title="Page not found",
                detail="That page is not part of the workshop.",
            )
        return render_error(
            request,
            code=exc.status_code,
            title="Something went wrong",
            detail="The workshop could not complete that request.",
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return render_error(
            request,
            code=500,
            title="Something went wrong",
            detail="The workshop could not complete that request. Please try again.",
        )

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Create the schema and load the demo workshop data on every boot."""
    init_db()
    created = seed.ensure_seeded()
    logger.info("wheelwright ready (seeded=%s, db=%s)", created, settings.database_url)
    yield


app = create_app()
