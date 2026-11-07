"""ADMIN PORTAL API — HR & recruiters only.

Runs as its own process:  uvicorn peoplepilot.apps.admin.main:app --port 8001
- Reachable only from PP_ADMIN_ALLOWED_CIDRS (office / VPN).
- Password (Argon2) + mandatory TOTP MFA. Sessions are admin-realm JWTs in __Host-pp_admin.
- Every query is tenant-scoped; cross-tenant ids return 404.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pyotp
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...audit import audit
from ...config import get_settings
from ...db import get_scoped, get_session, init_db, scoped, utcnow
from ...models import (AdminUser, AuditEvent, Candidate, ChannelConfig, Employee, Message, ReminderSent, Round,
                       RoundInterviewer, Tenant)
from ...scheduling import engine
from ...security import tokens
from ...security.crypto import (decrypt, decrypt_json, encrypt, encrypt_json, hash_password, lookup_hash, new_token,
                                sha256, verify_password)
from ...security.ratelimit import admin_login_limiter
from ...security.redact import mask_phone
from ..common import lifespan, IPAllowListMiddleware, clear_session_cookie, harden, set_session_cookie
from . import schemas as S
from .deps import COOKIE, AdminCtx, admin_pre_mfa, current_admin, owner_only

app = FastAPI(title="Reporter Admin API", docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=lifespan)
harden(app, origin=get_settings().admin_origin)
app.add_middleware(IPAllowListMiddleware)

LOCK_AFTER = 5
LOCK_FOR = timedelta(minutes=15)



def _issue_cookie(response: Response, user: AdminUser, mfa: bool) -> None:
    token = tokens.issue("admin", sub=user.id, tenant_id=user.tenant_id, session_version=user.session_version,
                         extra={"mfa": mfa, "role": user.role})
    set_session_cookie(response, COOKIE, token, get_settings().admin_session_minutes * 60)


# ================================================================== setup & auth
@app.get("/api/setup/status")
def setup_status(session: Session = Depends(get_session)):
    return {"setup_done": (session.scalar(select(func.count()).select_from(Tenant)) or 0) > 0}


@app.post("/api/setup", status_code=201)
def setup(body: S.SetupIn, response: Response, session: Session = Depends(get_session)):
    """First-run only. Requires PP_SETUP_TOKEN from the server's environment."""
    if session.scalar(select(func.count()).select_from(Tenant)) > 0:
        raise HTTPException(409, "Already set up")
    if not body.setup_token or sha256(body.setup_token) != sha256(get_settings().setup_token):
        raise HTTPException(403, "Invalid setup token")
    tenant = Tenant(name=body.org_name, kind=body.org_kind, timezone=body.timezone)
    session.add(tenant)
    session.flush()
    user = AdminUser(tenant_id=tenant.id, email=body.email.lower(), password_hash=hash_password(body.password),
                     role="owner")
    session.add(user)
    session.flush()
    audit(session, tenant_id=tenant.id, actor_type="admin", actor_id=user.id, action="setup_completed")
    _issue_cookie(response, user, mfa=False)
    return {"mfa_setup_required": True}


@app.post("/api/auth/login", response_model=S.LoginOut)
def login(body: S.LoginIn, request: Request, response: Response, session: Session = Depends(get_session)):
    ip = request.client.host if request.client else "?"
    if not admin_login_limiter.allow(f"ip:{ip}") or not admin_login_limiter.allow(f"em:{body.email.lower()}"):
        raise HTTPException(429, "Too many attempts. Try again later.")
    user = session.scalars(select(AdminUser).where(AdminUser.email == body.email.lower())).first()
    generic = HTTPException(401, "Invalid email, password or code")
    if user and user.locked_until and user.locked_until > utcnow():
        verify_password(None, body.password)  # equalise timing
        raise generic
    def fail(action: str):
        # Commit BEFORE raising: the request's transaction is rolled back on error, and the
        # failure counter / lockout / audit entry must survive that.
        if user:
            user.failed_logins += 1
            if user.failed_logins >= LOCK_AFTER:
                user.locked_until = utcnow() + LOCK_FOR
                user.failed_logins = 0
            audit(session, tenant_id=user.tenant_id, actor_type="admin", actor_id=user.id, action=action,
                  result="failed")
            session.commit()
        return generic

    if not verify_password(user.password_hash if user else None, body.password) or not user or not user.active:
        raise fail("login")
    if user.mfa_enabled:
        if not body.totp:
            return S.LoginOut(mfa_required=True, mfa_setup_required=False)
        if not pyotp.TOTP(decrypt(user.totp_secret_enc)).verify(body.totp, valid_window=1):
            raise fail("login_mfa")
    user.failed_logins = 0
    user.locked_until = None
    _issue_cookie(response, user, mfa=user.mfa_enabled)
    audit(session, tenant_id=user.tenant_id, actor_type="admin", actor_id=user.id, action="login")
    return S.LoginOut(mfa_required=False, mfa_setup_required=not user.mfa_enabled)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, ctx: AdminCtx = Depends(admin_pre_mfa)):
    ctx.user.session_version += 1  # revoke every session of this user
    clear_session_cookie(response, COOKIE)


@app.post("/api/auth/mfa/setup", response_model=S.MfaSetupOut)
def mfa_setup(ctx: AdminCtx = Depends(admin_pre_mfa)):
    if ctx.user.mfa_enabled:
        raise HTTPException(409, "Two-factor already enabled")
    secret = pyotp.random_base32()
    ctx.user.totp_secret_enc = encrypt(secret)
    return S.MfaSetupOut(otpauth_uri=pyotp.TOTP(secret).provisioning_uri(ctx.user.email, issuer_name="Reporter"))


@app.post("/api/auth/mfa/confirm", status_code=204)
def mfa_confirm(body: S.MfaConfirmIn, response: Response, session: Session = Depends(get_session),
                ctx: AdminCtx = Depends(admin_pre_mfa)):
    if ctx.user.mfa_enabled or not ctx.user.totp_secret_enc:
        raise HTTPException(409, "Start two-factor setup first")
    if not pyotp.TOTP(decrypt(ctx.user.totp_secret_enc)).verify(body.code, valid_window=1):
        raise HTTPException(400, "Wrong code")
    ctx.user.mfa_enabled = True
    ctx.user.session_version += 1
    _issue_cookie(response, ctx.user, mfa=True)
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="mfa_enabled")


@app.get("/api/auth/me", response_model=S.AdminUserOut)
def me(ctx: AdminCtx = Depends(current_admin)):
    u = ctx.user
    return S.AdminUserOut(id=u.id, email=u.email, role=u.role, mfa_enabled=u.mfa_enabled, active=u.active)


# ================================================================== people
@app.post("/api/admin-users", response_model=S.AdminUserOut, status_code=201)
def add_admin(body: S.AdminUserIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(owner_only)):
    if session.scalars(select(AdminUser).where(AdminUser.email == body.email.lower())).first():
        raise HTTPException(409, "Email already in use")
    u = AdminUser(tenant_id=ctx.tenant_id, email=body.email.lower(), password_hash=hash_password(body.password),
                  role=body.role)
    session.add(u)
    session.flush()
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="admin_user_created",
          record_type="admin_user", record_id=u.id)
    return S.AdminUserOut(id=u.id, email=u.email, role=u.role, mfa_enabled=False, active=True)


@app.post("/api/employees", response_model=S.EmployeeOut, status_code=201)
def add_employee(body: S.EmployeeIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    if session.scalars(scoped(Employee, ctx.tenant_id).where(Employee.email == body.email.lower())).first():
        raise HTTPException(409, "Employee already exists")
    e = Employee(tenant_id=ctx.tenant_id, name=body.name, email=body.email.lower(), is_interviewer=body.is_interviewer)
    session.add(e)
    session.flush()
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="employee_created",
          record_type="employee", record_id=e.id)
    return S.EmployeeOut(id=e.id, name=e.name, email=e.email, is_interviewer=e.is_interviewer, active=e.active)


@app.get("/api/employees", response_model=list[S.EmployeeOut])
def list_employees(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    return [S.EmployeeOut(id=e.id, name=e.name, email=e.email, is_interviewer=e.is_interviewer, active=e.active)
            for e in session.scalars(scoped(Employee, ctx.tenant_id).order_by(Employee.name))]


@app.post("/api/employees/{employee_id}/deactivate", status_code=204)
def deactivate_employee(employee_id: int, session: Session = Depends(get_session),
                        ctx: AdminCtx = Depends(current_admin)):
    e = get_scoped(session, Employee, ctx.tenant_id, employee_id)
    if not e:
        raise HTTPException(404, "Not found")
    e.active = False
    e.session_version += 1  # kicks them out of the employee portal immediately
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="employee_deactivated",
          record_type="employee", record_id=e.id)


# ================================================================== rounds
def _round_out(session: Session, r: Round) -> S.RoundOut:
    ids = list(session.scalars(select(RoundInterviewer.employee_id).where(RoundInterviewer.round_id == r.id)))
    return S.RoundOut(id=r.id, role_title=r.role_title, round_name=r.round_name, duration_min=r.duration_min,
                      mode=r.mode, location=r.location, window_start=r.window_start, window_end=r.window_end,
                      interviewer_ids=ids)


@app.post("/api/rounds", response_model=S.RoundOut, status_code=201)
def create_round(body: S.RoundIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    if body.day_end_hour <= body.day_start_hour:
        raise HTTPException(422, "Day end must be after day start")
    for iid in body.interviewer_ids:
        e = get_scoped(session, Employee, ctx.tenant_id, iid)
        if not e or not e.active or not e.is_interviewer:
            raise HTTPException(422, "Unknown interviewer")
    tz = ZoneInfo(session.get(Tenant, ctx.tenant_id).timezone)
    ws = datetime.combine(body.start_date, time(0, 0), tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    we = datetime.combine(body.end_date, time(23, 59), tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    r = Round(tenant_id=ctx.tenant_id, role_title=body.role_title, round_name=body.round_name,
              duration_min=body.duration_min, buffer_min=body.buffer_min, mode=body.mode, location=body.location,
              window_start=ws, window_end=we, day_start_hour=body.day_start_hour, day_end_hour=body.day_end_hour,
              max_slots_offered=body.max_slots_offered, created_by=ctx.user.id)
    session.add(r)
    session.flush()
    for iid in dict.fromkeys(body.interviewer_ids):
        session.add(RoundInterviewer(tenant_id=ctx.tenant_id, round_id=r.id, employee_id=iid))
    session.flush()
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="round_created",
          record_type="round", record_id=r.id)
    return _round_out(session, r)


@app.get("/api/rounds", response_model=list[S.RoundOut])
def list_rounds(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    return [_round_out(session, r) for r in session.scalars(scoped(Round, ctx.tenant_id).order_by(Round.id.desc()))]


# ================================================================== candidates
_PHONE_IN = re.compile(r"^\+?[0-9]{10,15}$")
MAX_CSV_BYTES = 1_000_000
MAX_ROWS = 2000


def _normalise_phone(raw: str) -> str | None:
    p = re.sub(r"[\s\-().]", "", raw or "")
    if not _PHONE_IN.match(p):
        return None
    if not p.startswith("+"):
        if len(p) == 10 and p[0] in "6789":
            p = "+91" + p
        elif len(p) == 12 and p.startswith("91"):
            p = "+" + p
        else:
            return None
    return p


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()[:200]
    return name.lstrip("=+-@\t\r")  # neutralise spreadsheet-formula injection


@app.post("/api/rounds/{round_id}/candidates/csv", response_model=S.CsvResult)
async def upload_candidates(round_id: int, file: UploadFile = File(...), session: Session = Depends(get_session),
                            ctx: AdminCtx = Depends(current_admin)):
    rnd = get_scoped(session, Round, ctx.tenant_id, round_id)
    if not rnd:
        raise HTTPException(404, "Not found")
    data = await file.read(MAX_CSV_BYTES + 1)
    if len(data) > MAX_CSV_BYTES:
        raise HTTPException(413, "File too large (max 1 MB)")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "File must be UTF-8 CSV")
    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower() for h in (reader.fieldnames or [])}
    if not {"name", "phone", "consent"} <= headers:
        raise HTTPException(422, "CSV needs columns: name, phone, consent (optional: email, channel)")
    existing = set(session.scalars(select(Candidate.phone_hash).where(Candidate.tenant_id == ctx.tenant_id,
                                                                      Candidate.round_id == rnd.id)))
    created, errors = 0, []
    for i, raw_row in enumerate(reader, start=2):
        if i - 1 > MAX_ROWS:
            errors.append(S.CsvRowError(row=i, error=f"More than {MAX_ROWS} rows; rest ignored"))
            break
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw_row.items()}
        name = _clean_name(row.get("name", ""))
        phone = _normalise_phone(row.get("phone", ""))
        consent = row.get("consent", "").lower() in ("yes", "y", "true", "1")
        channel = (row.get("channel") or "whatsapp").lower()
        if not name:
            errors.append(S.CsvRowError(row=i, error="Missing name"))
            continue
        if not phone:
            errors.append(S.CsvRowError(row=i, error="Invalid phone number"))
            continue
        if not consent:
            errors.append(S.CsvRowError(row=i, error="No consent to be contacted"))
            continue
        if channel not in ("whatsapp", "telegram"):
            errors.append(S.CsvRowError(row=i, error="Channel must be whatsapp or telegram"))
            continue
        ph = lookup_hash(phone)
        if ph in existing:
            errors.append(S.CsvRowError(row=i, error="Duplicate phone in this round"))
            continue
        existing.add(ph)
        email = row.get("email") or None
        session.add(Candidate(tenant_id=ctx.tenant_id, round_id=rnd.id, name=name, phone_enc=encrypt(phone),
                              phone_hash=ph, phone_last4=phone[-4:], email_enc=encrypt(email) if email else None,
                              consent=True, channel=channel))
        created += 1
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="candidates_uploaded",
          record_type="round", record_id=rnd.id)
    return S.CsvResult(created=created, errors=errors)


def _row(c: Candidate) -> dict:
    return dict(id=c.id, round_id=c.round_id, name=c.name, phone_masked=mask_phone(c.phone_last4), channel=c.channel,
                status=c.outcome or c.status, booked_start=c.booked_start, interviewer_id=c.interviewer_id,
                needs_attention=c.needs_attention, bot_paused=c.bot_paused, last_message_at=c.last_message_at)


@app.get("/api/candidates", response_model=list[S.CandidateRow])
def list_candidates(round_id: int | None = None, needs_attention: bool | None = None,
                    session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    q = scoped(Candidate, ctx.tenant_id)
    if round_id is not None:
        q = q.where(Candidate.round_id == round_id)
    if needs_attention is not None:
        q = q.where(Candidate.needs_attention.is_(needs_attention))
    return [S.CandidateRow(**_row(c)) for c in session.scalars(q.order_by(Candidate.id))]


def _cand(session: Session, ctx: AdminCtx, candidate_id: int) -> Candidate:
    c = get_scoped(session, Candidate, ctx.tenant_id, candidate_id)
    if not c:
        raise HTTPException(404, "Not found")
    return c


@app.get("/api/candidates/{candidate_id}", response_model=S.CandidateDetail)
def candidate_detail(candidate_id: int, session: Session = Depends(get_session),
                     ctx: AdminCtx = Depends(current_admin)):
    c = _cand(session, ctx, candidate_id)
    msgs = session.scalars(scoped(Message, ctx.tenant_id).where(Message.candidate_id == c.id)
                           .order_by(Message.id)).all()
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="candidate_viewed",
          record_type="candidate", record_id=c.id)
    return S.CandidateDetail(**_row(c), messages=[
        S.MessageOut(direction=m.direction, sender=m.sender, text=m.text_redacted, intent=m.intent, at=m.created_at)
        for m in msgs])


@app.post("/api/candidates/{candidate_id}/invite", response_model=S.InviteOut)
def invite_candidate(candidate_id: int, session: Session = Depends(get_session),
                     ctx: AdminCtx = Depends(current_admin)):
    c = _cand(session, ctx, candidate_id)
    if c.fsm_state not in ("new", "invited"):
        raise HTTPException(409, "Candidate already in conversation")
    try:
        res = engine.invite(session, c, admin_id=ctx.user.id)
    except LookupError:
        raise HTTPException(409, f"Configure the {c.channel} channel first")
    except PermissionError:
        raise HTTPException(409, "Candidate has not consented to messages")
    link = None
    if "start_token" in res:
        cfg = session.scalars(scoped(ChannelConfig, ctx.tenant_id).where(ChannelConfig.kind == "telegram")).first()
        if not cfg:
            raise HTTPException(409, "Configure the telegram channel first")
        username = decrypt_json(cfg.config_enc).get("bot_username", "")
        link = f"https://t.me/{username}?start={res['start_token']}"
    return S.InviteOut(channel=res["channel"], sent=res["sent"], telegram_link=link)


@app.post("/api/candidates/{candidate_id}/reply", status_code=204)
def reply(candidate_id: int, body: S.ReplyIn, session: Session = Depends(get_session),
          ctx: AdminCtx = Depends(current_admin)):
    engine.recruiter_reply(session, _cand(session, ctx, candidate_id), body.text, ctx.user.id)


@app.post("/api/candidates/{candidate_id}/takeover", status_code=204)
def takeover(candidate_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    c = _cand(session, ctx, candidate_id)
    c.bot_paused = True
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action="bot_paused",
          record_type="candidate", record_id=c.id)


@app.post("/api/candidates/{candidate_id}/resume", status_code=204)
def resume(candidate_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    engine.resume_bot(session, _cand(session, ctx, candidate_id), ctx.user.id)


@app.post("/api/candidates/{candidate_id}/cancel", status_code=204)
def cancel_booking(candidate_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    engine.cancel(session, _cand(session, ctx, candidate_id), by="admin", actor_id=ctx.user.id)


@app.post("/api/candidates/{candidate_id}/outcome", status_code=204)
def outcome(candidate_id: int, body: S.OutcomeIn, session: Session = Depends(get_session),
            ctx: AdminCtx = Depends(current_admin)):
    c = _cand(session, ctx, candidate_id)
    if not c.booked_start:
        raise HTTPException(409, "No booking")
    c.outcome, c.fsm_state = body.outcome, "done"
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id, action=f"outcome:{body.outcome}",
          record_type="candidate", record_id=c.id)


# ================================================================== dashboard
@app.get("/api/kpis", response_model=S.Kpis)
def kpis(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    cands = session.scalars(scoped(Candidate, ctx.tenant_id)).all()
    booked = [c for c in cands if c.booked_start is not None]
    zero = [c for c in booked if c.recruiter_touches == 0]
    week_ago = utcnow() - timedelta(days=7)
    reminders = session.scalar(select(func.count()).select_from(ReminderSent)
                               .where(ReminderSent.tenant_id == ctx.tenant_id)) or 0
    return S.Kpis(
        invited=sum(c.fsm_state != "new" for c in cands),
        booked=len(booked),
        zero_touch_pct=round(100 * len(zero) / len(booked), 1) if booked else 0.0,
        reminders_sent=reminders,
        no_shows_7d=sum(c.outcome == "no_show" and c.booked_start >= week_ago for c in booked),
        needs_attention=sum(c.needs_attention for c in cands),
    )


# ================================================================== settings (owner only)
@app.put("/api/settings/channel", response_model=S.ChannelOut)
def set_channel(body: S.ChannelIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(owner_only)):
    existing = session.scalars(scoped(ChannelConfig, ctx.tenant_id).where(ChannelConfig.kind == body.kind)).first()
    secret_shown = None
    if body.kind == "whatsapp":
        if not (body.phone_number_id and body.access_token and body.app_secret and body.verify_token):
            raise HTTPException(422, "WhatsApp needs phone_number_id, access_token, app_secret, verify_token")
        cfg = {"phone_number_id": body.phone_number_id, "access_token": body.access_token,
               "app_secret": body.app_secret, "verify_token": body.verify_token,
               "invite_template": body.invite_template or "interview_invite"}
        lookup = body.phone_number_id
        path = "/webhooks/whatsapp"
    else:
        if not (body.bot_token and body.bot_username):
            raise HTTPException(422, "Telegram needs bot_token and bot_username")
        secret_shown = new_token(24)
        cfg = {"bot_token": body.bot_token, "bot_username": body.bot_username}
        lookup = sha256(secret_shown)
        path = f"/webhooks/telegram/{ctx.tenant_id}"
    if existing:
        existing.config_enc, existing.lookup_key, existing.updated_at = encrypt_json(cfg), lookup, utcnow()
    else:
        session.add(ChannelConfig(tenant_id=ctx.tenant_id, kind=body.kind, lookup_key=lookup,
                                  config_enc=encrypt_json(cfg)))
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id,
          action=f"channel_configured:{body.kind}")
    return S.ChannelOut(kind=body.kind, configured=True, webhook_path=path, webhook_secret=secret_shown)


@app.post("/api/settings/pause", status_code=204)
def pause(body: S.PauseIn, session: Session = Depends(get_session), ctx: AdminCtx = Depends(owner_only)):
    session.get(Tenant, ctx.tenant_id).messaging_paused = body.paused
    audit(session, tenant_id=ctx.tenant_id, actor_type="admin", actor_id=ctx.user.id,
          action="messaging_paused" if body.paused else "messaging_resumed")


@app.get("/api/audit", response_model=list[S.AuditOut])
def audit_log(limit: int = 200, session: Session = Depends(get_session), ctx: AdminCtx = Depends(owner_only)):
    rows = session.scalars(scoped(AuditEvent, ctx.tenant_id).order_by(AuditEvent.id.desc()).limit(min(limit, 1000)))
    return [S.AuditOut(at=a.created_at, actor_type=a.actor_type, actor_id=a.actor_id, action=a.action,
                       record_type=a.record_type, record_id=a.record_id, result=a.result) for a in rows]


@app.get("/api/health", response_model=S.HealthOut)
def health(session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
    kinds = {c.kind for c in session.scalars(scoped(ChannelConfig, ctx.tenant_id))}
    s = get_settings()
    return S.HealthOut(
        database=True,
        channels={"whatsapp": "whatsapp" in kinds, "telegram": "telegram" in kinds},
        llm_configured=bool(s.llm_base_url and s.llm_model),
        messaging_paused=session.get(Tenant, ctx.tenant_id).messaging_paused,
        simulator=s.simulator_on,
        candidates_without_consent=session.scalar(select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == ctx.tenant_id, Candidate.consent.is_(False))) or 0,
    )


# ================================================================== dev-only candidate simulator
# Lets you play the candidate from the admin UI without WhatsApp/Telegram. Registered only when
# PP_SIMULATOR=true and PP_ENV is not prod, so these routes don't exist in production.
if get_settings().simulator_on:
    from pydantic import BaseModel, ConfigDict, Field

    from ...channels.base import sim_channel

    class SimIn(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: str | None = Field(default=None, max_length=1000)
        token: str | None = Field(default=None, max_length=64)

    class SimButton(BaseModel):
        label: str
        token: str

    class SimOut(BaseModel):
        messages: list[S.MessageOut]
        buttons: list[SimButton]

    def _sim_state(session: Session, ctx: AdminCtx, c: Candidate) -> SimOut:
        msgs = session.scalars(scoped(Message, ctx.tenant_id).where(Message.candidate_id == c.id)
                               .order_by(Message.id)).all()
        live = not c.bot_paused and c.fsm_state not in ("needs_recruiter", "cancelled", "done")
        buttons = sim_channel.latest_buttons.get(engine.channel_address(c), []) if live else []
        return SimOut(
            messages=[S.MessageOut(direction=m.direction, sender=m.sender, text=m.text_redacted, intent=m.intent,
                                   at=m.created_at) for m in msgs],
            buttons=[SimButton(label=b.label, token=b.token) for b in buttons],
        )

    @app.get("/api/dev/sim/{candidate_id}", response_model=SimOut)
    def sim_get(candidate_id: int, session: Session = Depends(get_session), ctx: AdminCtx = Depends(current_admin)):
        return _sim_state(session, ctx, _cand(session, ctx, candidate_id))

    @app.post("/api/dev/sim/{candidate_id}", response_model=SimOut)
    def sim_post(candidate_id: int, body: SimIn, session: Session = Depends(get_session),
                 ctx: AdminCtx = Depends(current_admin)):
        c = _cand(session, ctx, candidate_id)
        if not (body.text or body.token):
            raise HTTPException(422, "Send text or tap a button")
        if body.token:
            sim_channel.latest_buttons.pop(engine.channel_address(c), None)
        engine.handle_inbound(session, c, text=body.text, button_token=body.token)
        session.flush()
        return _sim_state(session, ctx, c)
