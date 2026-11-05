"""Session tokens. Admin and portal tokens differ in key, audience and cookie name.

A portal token presented to the admin API fails signature verification (different key)
AND audience verification (different `aud`), so the two portals can never share a session.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

import jwt

from ..config import get_settings
from ..db import utcnow

Realm = Literal["admin", "portal"]

ISSUER = "peoplepilot"
COOKIE_NAMES: dict[str, str] = {"admin": "__Host-pp_admin", "portal": "__Host-pp_portal"}


def _key(realm: Realm) -> str:
    s = get_settings()
    return s.admin_jwt_key if realm == "admin" else s.portal_jwt_key


def issue(realm: Realm, *, sub: int, tenant_id: int, session_version: int, extra: dict | None = None) -> str:
    s = get_settings()
    minutes = s.admin_session_minutes if realm == "admin" else s.portal_session_minutes
    now = utcnow()
    claims = {
        "iss": ISSUER,
        "aud": realm,
        "sub": str(sub),
        "tid": tenant_id,
        "sv": session_version,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        **(extra or {}),
    }
    return jwt.encode(claims, _key(realm), algorithm="HS256")


def verify(realm: Realm, token: str) -> dict:
    """Raises jwt.PyJWTError on any problem (bad signature, wrong audience, expired...)."""
    return jwt.decode(
        token,
        _key(realm),
        algorithms=["HS256"],
        audience=realm,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "aud", "iss", "sub"]},
    )
