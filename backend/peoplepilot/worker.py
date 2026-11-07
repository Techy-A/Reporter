"""Background worker: reminders + data-retention purge.

Run:  python -m peoplepilot.worker
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from sqlalchemy import delete, select

from .config import get_settings
from .db import init_db, session_scope, utcnow
from .models import ActionNonce, AskEvent, AuditEvent, HrTicket, HrTicketMessage, LoginCode, Message
from .scheduling.engine import due_reminders
from .security.redact import install_log_redaction

log = logging.getLogger("peoplepilot.worker")


def purge(session) -> dict[str, int]:
    s = get_settings()
    now = utcnow()
    out = {}
    out["messages"] = session.execute(
        delete(Message).where(Message.created_at < now - timedelta(days=s.message_retention_days))).rowcount
    out["nonces"] = session.execute(delete(ActionNonce).where(ActionNonce.expires_at < now - timedelta(days=7))).rowcount
    out["login_codes"] = session.execute(delete(LoginCode).where(LoginCode.expires_at < now - timedelta(days=1))).rowcount
    stale_closed = select(HrTicket.id).where(HrTicket.status == "closed",
                                             HrTicket.updated_at < now - timedelta(days=s.ticket_retention_days))
    out["ticket_messages"] = session.execute(
        delete(HrTicketMessage).where(HrTicketMessage.ticket_id.in_(stale_closed))).rowcount
    out["ask_events"] = session.execute(
        delete(AskEvent).where(AskEvent.created_at < now - timedelta(days=s.audit_retention_days))).rowcount
    out["audit"] = session.execute(
        delete(AuditEvent).where(AuditEvent.created_at < now - timedelta(days=s.audit_retention_days))).rowcount
    return out


def run_once() -> None:
    session = session_scope()
    try:
        sent = due_reminders(session)
        purged = purge(session)
        session.commit()
        if sent or any(purged.values()):
            log.info("reminders=%s purged=%s", sent, purged)
    except Exception:
        session.rollback()
        log.exception("worker tick failed")
    finally:
        session.close()


def main() -> None:
    install_log_redaction()
    if get_settings().env != "prod":
        init_db()
    log.info("worker started")
    while True:
        run_once()
        time.sleep(60)


if __name__ == "__main__":
    main()
