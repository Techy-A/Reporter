"""Metadata-only audit trail. Never pass message content or personal data here."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models import AuditEvent


def audit(session: Session, *, tenant_id: int, actor_type: str, actor_id: int | None, action: str,
          record_type: str | None = None, record_id: int | None = None, result: str = "ok") -> None:
    session.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            record_type=record_type,
            record_id=record_id,
            result=result,
        )
    )
