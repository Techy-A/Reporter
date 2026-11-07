"""Employee-portal authentication dependency. Only portal-realm tokens are accepted here."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db import get_session, set_tenant
from ...models import Employee
from ...security import tokens

COOKIE = tokens.COOKIE_NAMES["portal"]


def current_employee(request: Request, session: Session = Depends(get_session)) -> Employee:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(401, "Not signed in")
    try:
        claims = tokens.verify("portal", raw)
    except jwt.PyJWTError:
        raise HTTPException(401, "Not signed in")
    emp = session.get(Employee, int(claims["sub"]))
    if not emp or not emp.active or emp.tenant_id != claims.get("tid") or emp.session_version != claims.get("sv"):
        raise HTTPException(401, "Not signed in")
    set_tenant(session, emp.tenant_id)
    return emp
