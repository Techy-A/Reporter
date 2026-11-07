"""Employee portal, Phase 2: "Ask HR".

Identity comes ONLY from the portal session. No endpoint takes an employee id, every ticket
lookup is pinned to (tenant, employee), and other people's tickets look like 404s.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...assist.answer import ask, leave_lines
from ...audit import audit
from ...db import get_session, utcnow
from ...models import AskEvent, Employee, HrTicket, HrTicketMessage
from ...security.crypto import decrypt, encrypt
from ...security.ratelimit import RateLimiter
from .deps import current_employee

router = APIRouter()
ask_limiter = RateLimiter(limit=20, window_seconds=60)
ticket_limiter = RateLimiter(limit=10, window_seconds=3600)
Strict = ConfigDict(extra="forbid")
PRIVATE_CONTACT_TEXT = "Please contact me privately. (Sent from the sensitive-topic screen; nothing I typed there was saved.)"


class AskIn(BaseModel):
    model_config = Strict
    text: str = Field(default="", max_length=1000)
    quick: Literal["leave_balance"] | None = None


class FeedbackIn(BaseModel):
    model_config = Strict
    helpful: bool


class TicketIn(BaseModel):
    model_config = Strict
    kind: Literal["question", "talk_to_hr", "sensitive"]
    text: str = Field(default="", max_length=2000)


class ReplyIn(BaseModel):
    model_config = Strict
    text: str = Field(min_length=1, max_length=2000)


class TicketMsgOut(BaseModel):
    sender: str
    text: str
    at: datetime


class TicketOut(BaseModel):
    id: int
    kind: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[TicketMsgOut] = []


@router.post("/api/ask")
def ask_hr(body: AskIn, session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    if not ask_limiter.allow(f"emp:{emp.id}"):
        raise HTTPException(429, "You're asking very quickly. Wait a minute and try again.")
    if not body.quick and not body.text.strip():
        raise HTTPException(422, "Type a question")
    return ask(session, emp, body.text, quick=body.quick).public()


@router.post("/api/ask/{event_id}/feedback", status_code=204)
def feedback(event_id: int, body: FeedbackIn, session: Session = Depends(get_session),
             emp: Employee = Depends(current_employee)):
    ev = session.scalars(select(AskEvent).where(AskEvent.id == event_id, AskEvent.tenant_id == emp.tenant_id,
                                                AskEvent.employee_id == emp.id)).first()
    if not ev:
        raise HTTPException(404, "Not found")
    ev.helpful = body.helpful


@router.get("/api/me/leave")
def my_leave(session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    lines, as_of = leave_lines(session, emp)
    return {"lines": lines, "as_of": as_of.isoformat() if as_of else None}


# ------------------------------------------------------------------ my requests to HR
def _my_ticket(session: Session, emp: Employee, ticket_id: int) -> HrTicket:
    t = session.scalars(select(HrTicket).where(HrTicket.id == ticket_id, HrTicket.tenant_id == emp.tenant_id,
                                               HrTicket.employee_id == emp.id)).first()
    if not t:
        raise HTTPException(404, "Not found")
    return t


def _out(session: Session, t: HrTicket, with_messages: bool) -> TicketOut:
    msgs = []
    if with_messages:
        msgs = [TicketMsgOut(sender=m.sender, text=decrypt(m.text_enc), at=m.created_at) for m in session.scalars(
            select(HrTicketMessage).where(HrTicketMessage.ticket_id == t.id).order_by(HrTicketMessage.id))]
    return TicketOut(id=t.id, kind=t.kind, status=t.status, created_at=t.created_at, updated_at=t.updated_at,
                     messages=msgs)


@router.post("/api/tickets", response_model=TicketOut, status_code=201)
def open_ticket(body: TicketIn, session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    if not ticket_limiter.allow(f"emp:{emp.id}"):
        raise HTTPException(429, "Too many requests to HR in the last hour. Try again later.")
    if body.kind == "sensitive":
        text = PRIVATE_CONTACT_TEXT  # never store what was typed on the sensitive screen
    else:
        text = body.text.strip()
        if not text:
            raise HTTPException(422, "Write your question for HR")
    t = HrTicket(tenant_id=emp.tenant_id, employee_id=emp.id, kind=body.kind, sensitive=body.kind == "sensitive")
    session.add(t)
    session.flush()
    session.add(HrTicketMessage(tenant_id=emp.tenant_id, ticket_id=t.id, sender="employee", text_enc=encrypt(text)))
    session.flush()
    audit(session, tenant_id=emp.tenant_id, actor_type="employee", actor_id=emp.id, action="hr_ticket_opened",
          record_type="hr_ticket", record_id=t.id)
    return _out(session, t, True)


@router.get("/api/tickets", response_model=list[TicketOut])
def my_tickets(session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    rows = session.scalars(select(HrTicket).where(HrTicket.tenant_id == emp.tenant_id, HrTicket.employee_id == emp.id)
                           .order_by(HrTicket.updated_at.desc()).limit(50))
    return [_out(session, t, False) for t in rows]


@router.get("/api/tickets/{ticket_id}", response_model=TicketOut)
def my_ticket(ticket_id: int, session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    return _out(session, _my_ticket(session, emp, ticket_id), True)


@router.post("/api/tickets/{ticket_id}/reply", response_model=TicketOut)
def reply(ticket_id: int, body: ReplyIn, session: Session = Depends(get_session),
          emp: Employee = Depends(current_employee)):
    t = _my_ticket(session, emp, ticket_id)
    if t.status == "closed":
        raise HTTPException(409, "This request is closed. Open a new one.")
    session.add(HrTicketMessage(tenant_id=emp.tenant_id, ticket_id=t.id, sender="employee",
                                text_enc=encrypt(body.text.strip())))
    t.status, t.updated_at = "open", utcnow()
    session.flush()
    return _out(session, t, True)
