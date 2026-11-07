"""Recover access to the admin portal. Run ON THE SERVER (whoever can run this already controls the data).

    python -m peoplepilot.reset_admin owner@old.example --new-email you@example.com

You're asked for a new password (typed, never shown). Two-factor is switched off for that account, so
the next sign-in shows a fresh QR code to scan with your own authenticator app. Every existing session
of that account is signed out, and the reset is written to the audit log.
"""
from __future__ import annotations

import argparse
import getpass

from sqlalchemy import select

from .audit import audit
from .db import init_db, session_scope
from .models import AdminUser
from .security.crypto import hash_password


def reset(email: str, new_password: str, new_email: str | None = None) -> AdminUser:
    if len(new_password) < 12:
        raise SystemExit("Password must be at least 12 characters")
    s = session_scope()
    try:
        user = s.scalars(select(AdminUser).where(AdminUser.email == email.lower())).first()
        if not user:
            raise SystemExit(f"No admin account with email {email}")
        if new_email:
            new_email = new_email.strip().lower()
            if s.scalars(select(AdminUser).where(AdminUser.email == new_email, AdminUser.id != user.id)).first():
                raise SystemExit(f"{new_email} is already used by another admin")
            user.email = new_email
        user.password_hash = hash_password(new_password)
        user.mfa_enabled = False
        user.totp_secret_enc = None
        user.failed_logins = 0
        user.locked_until = None
        user.active = True
        user.session_version += 1
        audit(s, tenant_id=user.tenant_id, actor_type="system", actor_id=user.id, action="admin_access_reset",
              record_type="admin_user", record_id=user.id)
        s.commit()
        return user
    finally:
        s.close()


def main() -> None:  # pragma: no cover - interactive
    ap = argparse.ArgumentParser(description="Reset an admin's password and two-factor (run on the server)")
    ap.add_argument("email", help="the admin account's current email")
    ap.add_argument("--new-email", help="optionally change the sign-in email")
    args = ap.parse_args()
    init_db()
    pw = getpass.getpass("New password (12+ characters): ")
    if pw != getpass.getpass("Repeat it: "):
        raise SystemExit("Passwords don't match")
    user = reset(args.email, pw, args.new_email)
    print(f"Done. Sign in as {user.email}; you'll be asked to set up two-factor with your authenticator app.")


if __name__ == "__main__":
    main()
