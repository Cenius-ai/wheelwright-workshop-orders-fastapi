"""Staff sign-in, sign-up and sign-out."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import SESSION_USER_KEY, get_current_user, safe_next_path
from ..flash import set_flash
from ..models import StaffUser
from ..security import hash_password, validate_password_strength, verify_password
from ..templating import render
from ..validators import clean_text, parse_email

router = APIRouter()

WRONG_CREDENTIALS = "That email and password don't match a workshop account."


@router.get("/login", include_in_schema=False)
async def login_page(
    request: Request,
    next: str = "",
    user: StaffUser | None = Depends(get_current_user),
):
    if user is not None:
        return RedirectResponse(safe_next_path(next), status_code=303)
    return render(
        request,
        "login.html",
        page_title="Sign in",
        next_path=safe_next_path(next) if next else "",
        email="",
        error=None,
        field_errors={},
    )


@router.post("/login", include_in_schema=False)
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    email = clean_text(form.get("email"), 254).lower()
    password = str(form.get("password") or "")
    next_path = safe_next_path(str(form.get("next") or ""))

    field_errors: dict[str, str] = {}
    if not email:
        field_errors["email"] = "Enter your workshop email address."
    if not password:
        field_errors["password"] = "Enter your password."

    if field_errors:
        return render(
            request,
            "login.html",
            page_title="Sign in",
            next_path=next_path,
            email=email,
            error=None,
            field_errors=field_errors,
        )

    user = db.scalar(select(StaffUser).where(func.lower(StaffUser.email) == email))
    if user is None or not verify_password(password, user.password_hash):
        return render(
            request,
            "login.html",
            page_title="Sign in",
            next_path=next_path,
            email=email,
            error=WRONG_CREDENTIALS,
            field_errors={},
        )

    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    set_flash(request, f"Signed in as {user.name}.")
    return RedirectResponse(next_path, status_code=303)


@router.get("/register", include_in_schema=False)
async def register_page(
    request: Request,
    user: StaffUser | None = Depends(get_current_user),
):
    if user is not None:
        return RedirectResponse("/", status_code=303)
    return render(
        request,
        "register.html",
        page_title="Create a staff account",
        values={"name": "", "email": ""},
        field_errors={},
    )


@router.post("/register", include_in_schema=False)
async def register_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    name = clean_text(form.get("name"), 120)
    email = clean_text(form.get("email"), 254).lower()
    password = str(form.get("password") or "")
    confirm = str(form.get("confirm_password") or "")

    field_errors: dict[str, str] = {}
    if len(name) < 2:
        field_errors["name"] = "Enter your full name."
    email_value, email_error = parse_email(email)
    if email == "":
        field_errors["email"] = "Enter your work email address."
    elif email_error:
        field_errors["email"] = email_error
    for message in validate_password_strength(password):
        field_errors["password"] = message
    if not field_errors.get("password") and password != confirm:
        field_errors["confirm_password"] = "The two passwords don't match."

    if not field_errors and email_value:
        existing = db.scalar(select(StaffUser.id).where(func.lower(StaffUser.email) == email_value))
        if existing is not None:
            field_errors["email"] = "An account already uses that email address."

    if field_errors:
        return render(
            request,
            "register.html",
            page_title="Create a staff account",
            values={"name": name, "email": email},
            field_errors=field_errors,
        )

    is_first_account = db.scalar(select(func.count(StaffUser.id))) == 0
    user = StaffUser(
        name=name,
        email=email_value or email,
        password_hash=hash_password(password),
        role="admin" if is_first_account else "staff",
    )
    db.add(user)
    db.commit()

    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    greeting = "You are the workshop admin." if is_first_account else "Welcome to the workshop."
    set_flash(request, f"Account created for {user.name}. {greeting}")
    return RedirectResponse("/", status_code=303)


@router.post("/logout", include_in_schema=False)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
