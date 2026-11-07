"""EMPLOYEE PORTAL API — employees / interviewers only.

Runs as its own process:  uvicorn peoplepilot.apps.portal.main:app --port 8002
- Separate signing key + audience + cookie (__Host-pp_portal) from the admin portal.
- Sign-in with a one-time email code (no passwords to steal or reuse).
- The employee's identity always comes from the session; no endpoint accepts an employee id.
- Responses are minimal: interviewers see a candidate's first name, role and time,
  never their phone number or email.
"""
from __future__ import annotations

import logging
import secrets
import smtplib
from datetime import timedelta
from email.message import EmailMessage

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...audit import audit
from ...config import get_settings
from ...db import get_session, init_db, set_tenant, utcnow
from ...models import Candidate, Employee, LoginCode, Round, Tenant
from ...scheduling.ics import build_ics
from ...security import tokens
from ...security.crypto import constant_time_eq, lookup_hash
from ...security.ratelimit import portal_code_limiter
from ..common import lifespan, clear_session_cookie, harden, set_session_cookie
from .deps import current_employee

log = logging.getLogger("peoplepilot.portal")
from .deps import COOKIE  # noqa: E402
CODE_TTL = timedelta(minutes=10)
MAX_CODE_ATTEMPTS = 5

app = FastAPI(title="Reporter Employee Portal API", docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=lifespan)
harden(app, origin=get_settings().portal_origin)



# ------------------------------------------------------------------ email delivery
_dev_outbox: list[tuple[str, str]] = []  # dev/test only


def send_code(email: str, code: str) -> None:
    s = get_settings()
    if s.smtp_host:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = s.smtp_from, email, "Your Reporter sign-in code"
        msg.set_content(f"Your sign-in code is {code}. It expires in 10 minutes. "
                        "If you didn't ask for it, ignore this email.")
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password or "")
            smtp.send_message(msg)
    elif s.env in ("dev", "test"):
        _dev_outbox.append((email, code))
        log.info("DEV ONLY: sign-in code generated (no SMTP configured); see dev outbox")
    else:
        raise RuntimeError("SMTP is not configured")


# ------------------------------------------------------------------ schemas
Strict = ConfigDict(extra="forbid")


class CodeRequestIn(BaseModel):
    model_config = Strict
    email: EmailStr


class CodeVerifyIn(BaseModel):
    model_config = Strict
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class MeOut(BaseModel):
    name: str
    email: str
    organisation: str
    is_interviewer: bool


class MyInterviewOut(BaseModel):
    id: int
    candidate_first_name: str
    role_title: str
    round_name: str
    start: str  # ISO, UTC
    duration_min: int
    mode: str
    location: str
    status: str


class OutcomeIn(BaseModel):
    model_config = Strict
    outcome: str = Field(pattern=r"^(attended|no_show)$")


# ------------------------------------------------------------------ auth
GENERIC_SENT = {"detail": "If this email is registered, we've sent a 6-digit code."}


@app.post("/api/auth/code")
def request_code(body: CodeRequestIn, request: Request, session: Session = Depends(get_session)):
    email = body.email.lower()
    ip = request.client.host if request.client else "?"
    if not portal_code_limiter.allow(f"ip:{ip}") or not portal_code_limiter.allow(f"em:{email}"):
        raise HTTPException(429, "Too many requests. Try again later.")
    emp = session.scalars(select(Employee).where(Employee.email == email, Employee.active.is_(True))).first()
    if emp:  # same response either way: no account enumeration
        code = f"{secrets.randbelow(1_000_000):06d}"
        for old in session.scalars(select(LoginCode).where(LoginCode.employee_id == emp.id,
                                                            LoginCode.used.is_(False))):
            old.used = True
        session.add(LoginCode(tenant_id=emp.tenant_id, employee_id=emp.id, code_hash=lookup_hash(f"{emp.id}:{code}"),
                              expires_at=utcnow() + CODE_TTL))
        session.flush()
        send_code(email, code)
        s = get_settings()
        if s.env == "dev" and s.simulator_on and not s.smtp_host:
            # Dev convenience only (no email server): show the code on screen.
            return {**GENERIC_SENT, "dev_code": code}
    return GENERIC_SENT


@app.post("/api/auth/verify", status_code=204)
def verify_code(body: CodeVerifyIn, response: Response, session: Session = Depends(get_session)):
    bad = HTTPException(401, "Invalid or expired code")
    emp = session.scalars(select(Employee).where(Employee.email == body.email.lower(),
                                                 Employee.active.is_(True))).first()
    if not emp:
        raise bad
    lc = session.scalars(select(LoginCode).where(LoginCode.employee_id == emp.id, LoginCode.used.is_(False))
                         .order_by(LoginCode.id.desc())).first()
    if not lc or lc.expires_at < utcnow() or lc.attempts >= MAX_CODE_ATTEMPTS:
        raise bad
    lc.attempts += 1
    if not constant_time_eq(lc.code_hash, lookup_hash(f"{emp.id}:{body.code}")):
        if lc.attempts >= MAX_CODE_ATTEMPTS:
            lc.used = True
        session.commit()  # persist the attempt count before failing
        raise bad
    lc.used = True
    token = tokens.issue("portal", sub=emp.id, tenant_id=emp.tenant_id, session_version=emp.session_version)
    set_session_cookie(response, COOKIE, token, get_settings().portal_session_minutes * 60)
    audit(session, tenant_id=emp.tenant_id, actor_type="employee", actor_id=emp.id, action="portal_login")


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, emp: Employee = Depends(current_employee)):
    emp.session_version += 1
    clear_session_cookie(response, COOKIE)


# ------------------------------------------------------------------ my data
@app.get("/api/me", response_model=MeOut)
def me(session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    return MeOut(name=emp.name, email=emp.email, organisation=session.get(Tenant, emp.tenant_id).name,
                 is_interviewer=emp.is_interviewer)


def _my_interviews_query(emp: Employee):
    # Identity from the session only: tenant AND interviewer are both pinned.
    return (select(Candidate, Round).join(Round, Round.id == Candidate.round_id)
            .where(Candidate.tenant_id == emp.tenant_id, Candidate.interviewer_id == emp.id,
                   Candidate.booked_start.is_not(None)))


def _out(c: Candidate, r: Round) -> MyInterviewOut:
    return MyInterviewOut(id=c.id, candidate_first_name=(c.name.split() or ["Candidate"])[0], role_title=r.role_title,
                          round_name=r.round_name, start=c.booked_start.isoformat() + "Z",
                          duration_min=r.duration_min, mode=r.mode, location=r.location,
                          status=c.outcome or c.status)


@app.get("/api/me/interviews", response_model=list[MyInterviewOut])
def my_interviews(session: Session = Depends(get_session), emp: Employee = Depends(current_employee)):
    since = utcnow() - timedelta(days=7)
    rows = session.execute(_my_interviews_query(emp).where(Candidate.booked_start >= since)
                           .order_by(Candidate.booked_start)).all()
    return [_out(c, r) for c, r in rows]


def _mine(session: Session, emp: Employee, interview_id: int) -> tuple[Candidate, Round]:
    row = session.execute(_my_interviews_query(emp).where(Candidate.id == interview_id)).first()
    if not row:
        raise HTTPException(404, "Not found")  # someone else's interview looks identical to a missing one
    return row[0], row[1]


@app.get("/api/me/interviews/{interview_id}.ics")
def interview_ics(interview_id: int, session: Session = Depends(get_session),
                  emp: Employee = Depends(current_employee)):
    c, r = _mine(session, emp, interview_id)
    body = build_ics(uid=f"pp-{c.tenant_id}-{c.id}", start=c.booked_start, minutes=r.duration_min,
                     summary=f"Interview: {(c.name.split() or ['Candidate'])[0]} – {r.role_title} ({r.round_name})",
                     location=r.location)
    return Response(body, media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="interview-{c.id}.ics"'})


@app.post("/api/me/interviews/{interview_id}/outcome", status_code=204)
def mark_outcome(interview_id: int, body: OutcomeIn, session: Session = Depends(get_session),
                 emp: Employee = Depends(current_employee)):
    c, _ = _mine(session, emp, interview_id)
    if c.booked_start > utcnow():
        raise HTTPException(409, "The interview hasn't started yet")
    c.outcome, c.fsm_state = body.outcome, "done"
    audit(session, tenant_id=emp.tenant_id, actor_type="employee", actor_id=emp.id, action=f"outcome:{body.outcome}",
          record_type="candidate", record_id=c.id)


# Phase 2: Ask HR (help desk). Kept in its own module.
from . import helpdesk  # noqa: E402

app.include_router(helpdesk.router)
