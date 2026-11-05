"""Single-use, expiring, candidate-bound button actions.

A chat button carries only an opaque random token. The server stores (hash of token ->
candidate, action, payload, payload hash, expiry). Redeeming checks every binding and
marks it used in the same transaction, so a replayed, forwarded or forged button does nothing.
"""
from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import ActionNonce
from .crypto import new_token, sha256

DEFAULT_TTL = timedelta(hours=72)


def _payload_hash(action: str, payload: dict) -> str:
    return sha256(action + "|" + json.dumps(payload, sort_keys=True, default=str))


def mint(session: Session, *, tenant_id: int, candidate_id: int, action: str, payload: dict,
         ttl: timedelta = DEFAULT_TTL) -> str:
    token = new_token(12)
    session.add(
        ActionNonce(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            nonce_hash=sha256(token),
            action=action,
            payload=payload,
            payload_hash=_payload_hash(action, payload),
            expires_at=utcnow() + ttl,
        )
    )
    session.flush()
    return token


def redeem(session: Session, *, token: str, tenant_id: int, candidate_id: int) -> ActionNonce | None:
    row = session.scalars(
        select(ActionNonce).where(ActionNonce.nonce_hash == sha256(token)).with_for_update()
    ).first()
    if row is None:
        return None
    if row.tenant_id != tenant_id or row.candidate_id != candidate_id:
        return None  # someone else's button
    if row.used_at is not None or row.expires_at < utcnow():
        return None
    if row.payload_hash != _payload_hash(row.action, row.payload):
        return None  # payload altered in storage
    row.used_at = utcnow()
    return row


def invalidate_all(session: Session, *, tenant_id: int, candidate_id: int) -> None:
    """Called whenever the conversation moves on, so stale buttons stop working."""
    now = utcnow()
    for row in session.scalars(
        select(ActionNonce).where(
            ActionNonce.tenant_id == tenant_id,
            ActionNonce.candidate_id == candidate_id,
            ActionNonce.used_at.is_(None),
        )
    ):
        row.used_at = now
