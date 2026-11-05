"""Database tables. Every tenant-owned table carries tenant_id (enforced by RLS in Postgres)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, utcnow


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))  # company | staffing_agency | placement_cell
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    messaging_paused: Mapped[bool] = mapped_column(Boolean, default=False)  # kill switch
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- admin portal users
class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (UniqueConstraint("email"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="recruiter")  # owner | recruiter
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, default=1)  # bump to revoke all sessions
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- employee portal users
class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(254), index=True)
    is_interviewer: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LoginCode(Base):
    """Employee-portal one-time sign-in codes (hashed, single use, short-lived)."""

    __tablename__ = "login_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- scheduling
class Round(Base):
    __tablename__ = "rounds"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    role_title: Mapped[str] = mapped_column(String(200))
    round_name: Mapped[str] = mapped_column(String(100), default="Round 1")
    duration_min: Mapped[int] = mapped_column(Integer, default=30)
    buffer_min: Mapped[int] = mapped_column(Integer, default=10)
    mode: Mapped[str] = mapped_column(String(20), default="video")  # video | in_person
    location: Mapped[str] = mapped_column(String(500), default="")  # address or meeting link
    window_start: Mapped[datetime] = mapped_column(DateTime)  # date range (UTC, naive)
    window_end: Mapped[datetime] = mapped_column(DateTime)
    day_start_hour: Mapped[int] = mapped_column(Integer, default=10)  # local hours
    day_end_hour: Mapped[int] = mapped_column(Integer, default=18)
    max_slots_offered: Mapped[int] = mapped_column(Integer, default=3)
    created_by: Mapped[int] = mapped_column(ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RoundInterviewer(Base):
    __tablename__ = "round_interviewers"
    __table_args__ = (UniqueConstraint("round_id", "employee_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone_enc: Mapped[str] = mapped_column(Text)  # encrypted at rest
    phone_hash: Mapped[str] = mapped_column(String(64), index=True)  # HMAC for lookups
    phone_last4: Mapped[str] = mapped_column(String(4))
    email_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")  # whatsapp | telegram
    channel_user_id_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_user_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    invite_token_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="new")
    fsm_state: Mapped[str] = mapped_column(String(30), default="new")
    bot_paused: Mapped[bool] = mapped_column(Boolean, default=False)  # recruiter takeover
    needs_attention: Mapped[bool] = mapped_column(Boolean, default=False)
    booked_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    interviewer_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    recruiter_touches: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)  # attended | no_show
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Message(Base):
    """Conversation log. Text is PII-redacted before storage and purged after retention."""

    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    direction: Mapped[str] = mapped_column(String(10))  # in | out
    sender: Mapped[str] = mapped_column(String(20))  # candidate | bot | recruiter
    text_redacted: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ActionNonce(Base):
    """Single-use, expiring, candidate-bound button actions."""

    __tablename__ = "action_nonces"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    nonce_hash: Mapped[str] = mapped_column(String(64), unique=True)
    action: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReminderSent(Base):
    __tablename__ = "reminders_sent"
    __table_args__ = (UniqueConstraint("candidate_id", "kind", "slot_start"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    kind: Mapped[str] = mapped_column(String(10))  # t24 | t2
    slot_start: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- channels & audit
class ChannelConfig(Base):
    __tablename__ = "channel_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # whatsapp | telegram
    lookup_key: Mapped[str] = mapped_column(String(128), index=True)  # WA phone_number_id / TG secret hash
    config_enc: Mapped[str] = mapped_column(Text)  # encrypted JSON (tokens)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditEvent(Base):
    """Append-only, metadata only. Never put message content or PII here."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    actor_type: Mapped[str] = mapped_column(String(20))  # admin | employee | candidate | system
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    record_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
