"""Admin portal, Phase 2: policies, FAQ overrides, leave balances, help-desk tickets, stats, evals.

All queries are tenant-scoped. Sensitive tickets (POSH / private contact) are visible to the
owner role only. Stats are organisation-level counts; nothing here ranks or scores employees.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...assist import embed, llm
from ...assist.answer import ask
from ...assist.evals import ROUTE_OF, run_all, test_employee
from ...assist.parse import UnsupportedDocument, extract_text, split_clauses
from ...audit import audit
from ...db import get_scoped, get_session, scoped, utcnow
from ...models import (AskEvent, Employee, EvalCase, FaqOverride, HrTicket, HrTicketMessage, LeaveBalance, Policy,
                       PolicyClause, Tenant)
from ...security.crypto import decrypt, encrypt
from .deps import AdminCtx, current_admin, owner_only

router = APIRouter()
Strict = ConfigDict(extra="forbid")
MAX_CSV_BYTES = 2_000_000


def _audit(session: Session, ctx: AdminCtx, action: str, rtype: str | None = None, rid: int | None = None):
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action=action,
          record_type=rtype, record_id=rid)


def _clean(raw: str, n: int = 200) -> str:
    return (raw or "").strip()[:n].lstrip("=+-@\t\r")  # neutralise spreadsheet-formula injection


def _list(raw: str) -> list[str]:
    return [_clean(x, 100) for x in (raw or "").split(",") if x.strip()]


# ================================================================== help-desk settings
class HelpdeskSettings(BaseModel):
    model_config = Strict
    ic_contact: str = Field(default="", max_length=500)
    hr_contact: str = Field(default="", max_length=500)


@router.get("/api/settings/helpdesk", response_model=HelpdeskSettings)
def get_helpdesk_settings(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    t = session.get(Tenant, ctx.tenant_id)
    return HelpdeskSettings(ic_contact=t.ic_contact or "", hr_contact=t.hr_contact or "")


@router.put("/api/settings/helpdesk", response_model=HelpdeskSettings)
def put_helpdesk_settings(body: HelpdeskSettings, session: Session = Depends(get_session),
                          ctx: AdminCtx = Depends(owner_only)):
    t = session.get(Tenant, ctx.tenant_id)
    t.ic_contact, t.hr_contact = body.ic_contact.strip(), body.hr_contact.strip()
    _audit(session, ctx, "helpdesk_settings_updated")
    return body


# ================================================================== employee attributes (for policy audiences)
class EmployeeAttrs(BaseModel):
    model_config = Strict
    location: str = Field(default="", max_length=100)
    grade: str = Field(default="", max_length=50)
    employment_type: str = Field(default="", max_length=50)
    is_interviewer: bool | None = None


@router.patch("/api/employees/{employee_id}", status_code=204)
def update_employee(employee_id: int, body: EmployeeAttrs, session: Session = Depends(get_session),
                    ctx: AdminCtx = Depends(current_admin)):
    e = get_scoped(session, Employee, ctx.tenant_id, employee_id)
    if not e:
        raise HTTPException(404, "Not found")
    e.location, e.grade, e.employment_type = body.location.strip(), body.grade.strip(), body.employment_type.strip()
    if body.is_interviewer is not None:
        e.is_interviewer = body.is_interviewer
    _audit(session, ctx, "employee_updated", "employee", e.id)


class CsvReport(BaseModel):
    imported: int
    updated: int = 0
    errors: list[str]


async def _read_csv(file: UploadFile) -> list[dict]:
    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(413, "File is larger than 2 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "Save the CSV as UTF-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in rows[:5000]]


@router.post("/api/employees/csv", response_model=CsvReport)
async def import_employees(file: UploadFile = File(...), session: Session = Depends(get_session),
                           ctx: AdminCtx = Depends(current_admin)):
    """Columns: name, email, location, grade, employment_type, interviewer (yes/no)."""
    from email_validator import EmailNotValidError, validate_email

    rows = await _read_csv(file)
    added = updated = 0
    errors: list[str] = []
    for i, r in enumerate(rows, start=2):
        try:
            email = validate_email(r.get("email", ""), check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            errors.append(f"Row {i}: invalid email")
            continue
        name = _clean(r.get("name", ""))
        if not name:
            errors.append(f"Row {i}: name is missing")
            continue
        e = session.scalars(scoped(Employee, ctx.tenant_id).where(Employee.email == email)).first()
        if not e:
            e = Employee(tenant_id=ctx.tenant_id, name=name, email=email,
                         is_interviewer=r.get("interviewer", "").lower() in ("yes", "y", "true", "1"))
            session.add(e)
            added += 1
        else:
            e.name = name
            updated += 1
        e.location, e.grade = _clean(r.get("location", ""), 100), _clean(r.get("grade", ""), 50)
        e.employment_type = _clean(r.get("employment_type", ""), 50)
    session.flush()
    _audit(session, ctx, "employees_imported")
    return CsvReport(imported=added, updated=updated, errors=errors[:50])


# ================================================================== policies
class ClauseOut(BaseModel):
    id: int
    ref: str
    heading: str
    text: str


class PolicyOut(BaseModel):
    id: int
    title: str
    version: str
    effective_from: date
    status: str
    locations: list[str]
    grades: list[str]
    employment_types: list[str]
    source_name: str
    clause_count: int
    embedded: int
    created_at: datetime
    clauses: list[ClauseOut] | None = None


def _policy_out(session: Session, p: Policy, with_clauses: bool = False) -> PolicyOut:
    clauses = list(session.scalars(select(PolicyClause).where(PolicyClause.policy_id == p.id)
                                   .order_by(PolicyClause.position)))
    return PolicyOut(id=p.id, title=p.title, version=p.version, effective_from=p.effective_from, status=p.status,
                     locations=p.locations or [], grades=p.grades or [], employment_types=p.employment_types or [],
                     source_name=p.source_name, clause_count=len(clauses),
                     embedded=sum(1 for c in clauses if c.embedding),
                     created_at=p.created_at,
                     clauses=[ClauseOut(id=c.id, ref=c.ref, heading=c.heading, text=c.text) for c in clauses]
                     if with_clauses else None)


@router.post("/api/policies", response_model=PolicyOut, status_code=201)
async def upload_policy(file: UploadFile = File(...), title: str = Form(..., min_length=2, max_length=200),
                        version: str = Form(..., min_length=1, max_length=50), effective_from: date = Form(...),
                        locations: str = Form(""), grades: str = Form(""), employment_types: str = Form(""),
                        session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    data = await file.read(5_000_001)
    try:
        text = extract_text(file.filename or "", data)
    except UnsupportedDocument as exc:
        raise HTTPException(422, str(exc))
    clauses = split_clauses(text)
    if not clauses:
        raise HTTPException(422, "No text found in this document")
    p = Policy(tenant_id=ctx.tenant_id, title=_clean(title), version=_clean(version, 50), effective_from=effective_from,
               status="draft", locations=_list(locations), grades=_list(grades),
               employment_types=_list(employment_types), source_name=_clean(file.filename or "", 200),
               created_by=ctx.user.id)
    session.add(p)
    session.flush()
    for i, c in enumerate(clauses[:3000]):
        session.add(PolicyClause(tenant_id=ctx.tenant_id, policy_id=p.id, position=i, ref=c.ref, heading=c.heading,
                                 text=c.text))
    session.flush()
    _audit(session, ctx, "policy_uploaded", "policy", p.id)
    return _policy_out(session, p, True)


@router.get("/api/policies", response_model=list[PolicyOut])
def list_policies(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    return [_policy_out(session, p) for p in session.scalars(scoped(Policy, ctx.tenant_id)
                                                             .order_by(Policy.title, Policy.id.desc()))]


@router.get("/api/policies/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    p = get_scoped(session, Policy, ctx.tenant_id, policy_id)
    if not p:
        raise HTTPException(404, "Not found")
    return _policy_out(session, p, True)


@router.post("/api/policies/{policy_id}/activate", response_model=PolicyOut)
def activate_policy(policy_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    """Make this version live. Other active versions with the same title are superseded."""
    p = get_scoped(session, Policy, ctx.tenant_id, policy_id)
    if not p:
        raise HTTPException(404, "Not found")
    for old in session.scalars(scoped(Policy, ctx.tenant_id).where(Policy.title == p.title, Policy.id != p.id,
                                                                    Policy.status == "active")):
        old.status = "superseded"
    p.status = "active"
    embed.embed_policy_clauses(session, ctx.tenant_id, p.id)  # no-op without an embedding model
    _audit(session, ctx, "policy_activated", "policy", p.id)
    return _policy_out(session, p)


@router.post("/api/policies/{policy_id}/retire", response_model=PolicyOut)
def retire_policy(policy_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    p = get_scoped(session, Policy, ctx.tenant_id, policy_id)
    if not p:
        raise HTTPException(404, "Not found")
    p.status = "superseded"
    _audit(session, ctx, "policy_retired", "policy", p.id)
    return _policy_out(session, p)


@router.delete("/api/policies/{policy_id}", status_code=204)
def delete_draft(policy_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    p = get_scoped(session, Policy, ctx.tenant_id, policy_id)
    if not p:
        raise HTTPException(404, "Not found")
    if p.status != "draft":
        raise HTTPException(409, "Only drafts can be deleted. Retire an active policy instead.")
    for c in session.scalars(select(PolicyClause).where(PolicyClause.policy_id == p.id)):
        session.delete(c)
    session.delete(p)
    _audit(session, ctx, "policy_deleted", "policy", policy_id)


# ================================================================== FAQ overrides
class FaqIn(BaseModel):
    model_config = Strict
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=1, max_length=3000)
    active: bool = True


class FaqOut(FaqIn):
    model_config = ConfigDict()
    id: int
    updated_at: datetime


def _faq_out(f: FaqOverride) -> FaqOut:
    return FaqOut(id=f.id, question=f.question, answer=f.answer, active=f.active, updated_at=f.updated_at)


@router.get("/api/faqs", response_model=list[FaqOut])
def list_faqs(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    return [_faq_out(f) for f in session.scalars(scoped(FaqOverride, ctx.tenant_id).order_by(FaqOverride.id.desc()))]


@router.post("/api/faqs", response_model=FaqOut, status_code=201)
def add_faq(body: FaqIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    f = FaqOverride(tenant_id=ctx.tenant_id, question=body.question.strip(), answer=body.answer.strip(),
                    active=body.active, created_by=ctx.user.id)
    session.add(f)
    session.flush()
    _audit(session, ctx, "faq_created", "faq", f.id)
    return _faq_out(f)


@router.put("/api/faqs/{faq_id}", response_model=FaqOut)
def edit_faq(faq_id: int, body: FaqIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    f = get_scoped(session, FaqOverride, ctx.tenant_id, faq_id)
    if not f:
        raise HTTPException(404, "Not found")
    f.question, f.answer, f.active, f.updated_at = body.question.strip(), body.answer.strip(), body.active, utcnow()
    _audit(session, ctx, "faq_updated", "faq", f.id)
    return _faq_out(f)


@router.delete("/api/faqs/{faq_id}", status_code=204)
def delete_faq(faq_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    f = get_scoped(session, FaqOverride, ctx.tenant_id, faq_id)
    if not f:
        raise HTTPException(404, "Not found")
    session.delete(f)
    _audit(session, ctx, "faq_deleted", "faq", faq_id)


# ================================================================== leave balances
@router.post("/api/leave-balances/csv", response_model=CsvReport)
async def import_leave(file: UploadFile = File(...), session: Session = Depends(get_session),
                       ctx: AdminCtx = Depends(current_admin)):
    """Columns: email, leave_type, balance, as_of (YYYY-MM-DD). Replaces each person's row per leave type."""
    rows = await _read_csv(file)
    emails = {e.email: e for e in session.scalars(scoped(Employee, ctx.tenant_id))}
    added = updated = 0
    errors: list[str] = []
    for i, r in enumerate(rows, start=2):
        emp = emails.get(r.get("email", "").lower())
        if not emp:
            errors.append(f"Row {i}: no employee with that email")
            continue
        ltype = _clean(r.get("leave_type", ""), 50)
        try:
            bal = float(r.get("balance", ""))
            as_of = date.fromisoformat(r.get("as_of", ""))
        except ValueError:
            errors.append(f"Row {i}: balance must be a number and as_of a date like 2026-11-01")
            continue
        if not ltype or not -365 <= bal <= 365:
            errors.append(f"Row {i}: leave type missing or balance out of range")
            continue
        row = session.scalars(scoped(LeaveBalance, ctx.tenant_id).where(LeaveBalance.employee_id == emp.id,
                                                                         LeaveBalance.leave_type == ltype)).first()
        if row:
            row.balance, row.as_of, row.updated_at = bal, as_of, utcnow()
            updated += 1
        else:
            session.add(LeaveBalance(tenant_id=ctx.tenant_id, employee_id=emp.id, leave_type=ltype, balance=bal,
                                     as_of=as_of))
            added += 1
    session.flush()
    _audit(session, ctx, "leave_balances_imported")
    return CsvReport(imported=added, updated=updated, errors=errors[:50])


@router.get("/api/leave-balances/summary")
def leave_summary(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    q = select(func.count(func.distinct(LeaveBalance.employee_id)), func.count(), func.max(LeaveBalance.as_of)) \
        .where(LeaveBalance.tenant_id == ctx.tenant_id)
    people, rows, latest = session.execute(q).one()
    return {"employees": people, "rows": rows, "latest_as_of": latest.isoformat() if latest else None}


# ================================================================== tickets
class TicketMsg(BaseModel):
    sender: str
    text: str
    at: datetime


class TicketRow(BaseModel):
    id: int
    employee_name: str
    kind: str
    sensitive: bool
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[TicketMsg] | None = None


class HrReplyIn(BaseModel):
    model_config = Strict
    text: str = Field(min_length=1, max_length=3000)


def _visible(ctx: AdminCtx):
    q = scoped(HrTicket, ctx.tenant_id)
    return q if ctx.user.role == "owner" else q.where(HrTicket.sensitive.is_(False))


def _ticket(session: Session, ctx: AdminCtx, ticket_id: int) -> HrTicket:
    t = session.scalars(_visible(ctx).where(HrTicket.id == ticket_id)).first()
    if not t:
        raise HTTPException(404, "Not found")
    return t


def _ticket_out(session: Session, t: HrTicket, with_messages: bool) -> TicketRow:
    emp = session.get(Employee, t.employee_id)
    msgs = None
    if with_messages:
        msgs = [TicketMsg(sender=m.sender, text=decrypt(m.text_enc), at=m.created_at) for m in session.scalars(
            select(HrTicketMessage).where(HrTicketMessage.ticket_id == t.id).order_by(HrTicketMessage.id))]
    return TicketRow(id=t.id, employee_name=emp.name if emp else "?", kind=t.kind, sensitive=t.sensitive,
                     status=t.status, created_at=t.created_at, updated_at=t.updated_at, messages=msgs)


@router.get("/api/tickets", response_model=list[TicketRow])
def list_tickets(status: Literal["open", "answered", "closed", "all"] = "open", session: Session = Depends(get_session),
                 ctx: AdminCtx = Depends(current_admin)):
    q = _visible(ctx)
    if status != "all":
        q = q.where(HrTicket.status == status)
    return [_ticket_out(session, t, False) for t in session.scalars(q.order_by(HrTicket.updated_at.desc()).limit(200))]


@router.get("/api/tickets/{ticket_id}", response_model=TicketRow)
def get_ticket(ticket_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    t = _ticket(session, ctx, ticket_id)
    _audit(session, ctx, "hr_ticket_viewed", "hr_ticket", t.id)
    return _ticket_out(session, t, True)


@router.post("/api/tickets/{ticket_id}/reply", response_model=TicketRow)
def reply_ticket(ticket_id: int, body: HrReplyIn, session: Session = Depends(get_session),
                 ctx: AdminCtx = Depends(current_admin)):
    t = _ticket(session, ctx, ticket_id)
    session.add(HrTicketMessage(tenant_id=ctx.tenant_id, ticket_id=t.id, sender="hr", admin_id=ctx.user.id,
                                text_enc=encrypt(body.text.strip())))
    t.status, t.updated_at = "answered", utcnow()
    session.flush()
    _audit(session, ctx, "hr_ticket_replied", "hr_ticket", t.id)
    return _ticket_out(session, t, True)


@router.post("/api/tickets/{ticket_id}/close", status_code=204)
def close_ticket(ticket_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    t = _ticket(session, ctx, ticket_id)
    t.status, t.updated_at = "closed", utcnow()
    _audit(session, ctx, "hr_ticket_closed", "hr_ticket", t.id)


# ================================================================== stats (organisation level only)
@router.get("/api/helpdesk/stats")
def helpdesk_stats(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    since = utcnow() - timedelta(days=7)
    evs = list(session.scalars(scoped(AskEvent, ctx.tenant_id).where(AskEvent.created_at >= since)))
    routes: dict[str, int] = {}
    for e in evs:
        routes[e.route] = routes.get(e.route, 0) + 1
    answered = sum(v for k, v in routes.items() if k not in ("no_answer", "sensitive"))
    rated = [e.helpful for e in evs if e.helpful is not None]
    llm_evs = [e for e in evs if e.used_llm]
    open_q = _visible(ctx).where(HrTicket.status == "open")
    from ...config import get_settings

    s = get_settings()
    return {
        "questions_7d": len(evs),
        "answered_without_hr_7d": answered,
        "by_route_7d": routes,
        "helpful_rate": (sum(rated) / len(rated)) if rated else None,
        "open_tickets": session.scalar(select(func.count()).select_from(open_q.subquery())) or 0,
        "model": {
            "configured": llm.enabled(), "name": s.llm_model if llm.enabled() else None,
            "tools": s.llm_tools, "max_steps": s.llm_max_steps, "context_tokens": s.llm_context_tokens,
            "embeddings": embed.enabled(), "embed_model": s.embed_model if embed.enabled() else None,
            "calls_7d": len(llm_evs),
            "tokens_in_7d": sum(e.tokens_in for e in llm_evs), "tokens_out_7d": sum(e.tokens_out for e in llm_evs),
            "avg_steps": (sum(e.agent_steps for e in llm_evs) / len(llm_evs)) if llm_evs else None,
        },
    }


# ================================================================== try a question (preview as an employee profile)
class TryIn(BaseModel):
    model_config = Strict
    question: str = Field(min_length=1, max_length=1000)
    location: str = Field(default="", max_length=100)
    grade: str = Field(default="", max_length=50)
    employment_type: str = Field(default="", max_length=50)


@router.post("/api/helpdesk/try")
def try_question(body: TryIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    case = EvalCase(question=body.question, expect_route="", as_location=body.location, as_grade=body.grade,
                    as_employment_type=body.employment_type)
    res = ask(session, test_employee(ctx.tenant_id, case), body.question, record=False)
    out = res.public()
    out["route"] = ROUTE_OF.get(res.kind, res.kind)
    return out


# ================================================================== evals
class EvalIn(BaseModel):
    model_config = Strict
    question: str = Field(min_length=2, max_length=500)
    expect_route: Literal["faq", "leave", "policy", "no_answer", "sensitive", "agent"]
    expect_policy_title: str = Field(default="", max_length=200)
    expect_ref: str = Field(default="", max_length=30)
    must_include: str = Field(default="", max_length=200)
    as_location: str = Field(default="", max_length=100)
    as_grade: str = Field(default="", max_length=50)
    as_employment_type: str = Field(default="", max_length=50)


class EvalOut(EvalIn):
    model_config = ConfigDict()
    id: int
    last_passed: bool | None
    last_detail: str
    last_run_at: datetime | None


def _eval_out(c: EvalCase) -> EvalOut:
    return EvalOut(id=c.id, question=c.question, expect_route=c.expect_route, expect_policy_title=c.expect_policy_title,
                   expect_ref=c.expect_ref, must_include=c.must_include, as_location=c.as_location,
                   as_grade=c.as_grade, as_employment_type=c.as_employment_type, last_passed=c.last_passed,
                   last_detail=c.last_detail, last_run_at=c.last_run_at)


@router.get("/api/evals", response_model=list[EvalOut])
def list_evals(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    return [_eval_out(c) for c in session.scalars(scoped(EvalCase, ctx.tenant_id).order_by(EvalCase.id))]


@router.post("/api/evals", response_model=EvalOut, status_code=201)
def add_eval(body: EvalIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    c = EvalCase(tenant_id=ctx.tenant_id, created_by=ctx.user.id, **body.model_dump())
    session.add(c)
    session.flush()
    return _eval_out(c)


@router.delete("/api/evals/{eval_id}", status_code=204)
def delete_eval(eval_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    c = get_scoped(session, EvalCase, ctx.tenant_id, eval_id)
    if not c:
        raise HTTPException(404, "Not found")
    session.delete(c)


@router.post("/api/evals/run")
def run_evals(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    rep = run_all(session, ctx.tenant_id)
    _audit(session, ctx, "evals_run")
    return rep.as_dict()
