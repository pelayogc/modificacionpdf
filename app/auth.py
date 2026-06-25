from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from app.config import settings


@dataclass(frozen=True)
class CurrentUser:
    email: str
    is_admin: bool


def _email_from_request(request: Request) -> str | None:
    for header in (
        "cf-access-authenticated-user-email",
        "x-forwarded-email",
        "x-auth-request-email",
    ):
        value = request.headers.get(header)
        if value:
            return value.strip().lower()
    if settings.local_dev_user_email:
        return settings.local_dev_user_email.strip().lower()
    return None


def _domain_allowed(email: str) -> bool:
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].lower()
    return domain in settings.allowed_domains


def get_current_user(request: Request) -> CurrentUser:
    email = _email_from_request(request)
    if not email:
        raise HTTPException(
            status_code=401,
            detail="Acceso no autenticado. La app debe recibirse a traves de Cloudflare Access.",
        )
    if not _domain_allowed(email):
        raise HTTPException(status_code=403, detail="Dominio de email no autorizado.")
    return CurrentUser(email=email, is_admin=email in settings.admin_emails)


def require_admin(request: Request) -> CurrentUser:
    user = get_current_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores.")
    return user
