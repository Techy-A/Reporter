"""Admin-portal authentication dependencies. Only admin-realm tokens are accepted here."""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db import get_session, set_tenant
from ...models import AdminUser
from ...security import tokens

COOKIE = tokens.COOKIE_NAMES["admin"]


@dataclass
class AdminCtx:
    user: AdminUser
    tenant_id: int
    mfa: bool


def _load(request: Request, session: Session) -> AdminCtx:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(401, "Not signed in")
    try:
        claims = tokens.verify("admin", raw)
    except jwt.PyJWTError:
        raise HTTPException(401, "Not signed in")
    user = session.get(AdminUser, int(claims["sub"]))
    if (user is None or not user.active or user.tenant_id != claims.get("tid")
            or user.session_version != claims.get("sv")):
        raise HTTPException(401, "Not signed in")
    set_tenant(session, user.tenant_id)
    return AdminCtx(user=user, tenant_id=user.tenant_id, mfa=bool(claims.get("mfa")))


def admin_pre_mfa(request: Request, session: Session = Depends(get_session)) -> AdminCtx:
    """Signed in with password, MFA possibly not yet completed (only for MFA enrolment)."""
    return _load(request, session)


def current_admin(request: Request, session: Session = Depends(get_session)) -> AdminCtx:
    ctx = _load(request, session)
    if not ctx.mfa:
        raise HTTPException(403, "Complete two-factor setup first")
    return ctx


def owner_only(ctx: AdminCtx = Depends(current_admin)) -> AdminCtx:
    if ctx.user.role != "owner":
        raise HTTPException(403, "Owner role required")
    return ctx
