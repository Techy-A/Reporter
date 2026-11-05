"""Admin-portal request/response schemas. Responses are explicit allow-lists of fields;
ORM objects are never returned directly."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Strict = ConfigDict(extra="forbid")


class SetupIn(BaseModel):
    model_config = Strict
    setup_token: str
    org_name: str = Field(min_length=2, max_length=200)
    org_kind: Literal["company", "staffing_agency", "placement_cell"]
    timezone: str = "Asia/Kolkata"
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        from zoneinfo import ZoneInfo

        ZoneInfo(v)
        return v


class LoginIn(BaseModel):
    model_config = Strict
    email: EmailStr
    password: str = Field(max_length=200)
    totp: str | None = Field(default=None, pattern=r"^\d{6}$")


class LoginOut(BaseModel):
    mfa_required: bool
    mfa_setup_required: bool


class MfaSetupOut(BaseModel):
    otpauth_uri: str


class MfaConfirmIn(BaseModel):
    model_config = Strict
    code: str = Field(pattern=r"^\d{6}$")


class AdminUserIn(BaseModel):
    model_config = Strict
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    role: Literal["owner", "recruiter"] = "recruiter"


class AdminUserOut(BaseModel):
    id: int
    email: str
    role: str
    mfa_enabled: bool
    active: bool


class EmployeeIn(BaseModel):
    model_config = Strict
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    is_interviewer: bool = True


class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    is_interviewer: bool
    active: bool


class RoundIn(BaseModel):
    model_config = Strict
    role_title: str = Field(min_length=2, max_length=200)
    round_name: str = Field(default="Round 1", max_length=100)
    duration_min: int = Field(default=30, ge=10, le=240)
    buffer_min: int = Field(default=10, ge=0, le=120)
    mode: Literal["video", "in_person"] = "video"
    location: str = Field(default="", max_length=500)
    start_date: date
    end_date: date
    day_start_hour: int = Field(default=10, ge=0, le=23)
    day_end_hour: int = Field(default=18, ge=1, le=24)
    max_slots_offered: int = Field(default=3, ge=1, le=9)
    interviewer_ids: list[int] = Field(min_length=1, max_length=20)

    @field_validator("end_date")
    @classmethod
    def _order(cls, v: date, info):
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date before start_date")
        return v


class RoundOut(BaseModel):
    id: int
    role_title: str
    round_name: str
    duration_min: int
    mode: str
    location: str
    window_start: datetime
    window_end: datetime
    interviewer_ids: list[int]


class CsvRowError(BaseModel):
    row: int
    error: str


class CsvResult(BaseModel):
    created: int
    errors: list[CsvRowError]


class CandidateRow(BaseModel):
    """Board row: masked phone, no email."""

    id: int
    round_id: int
    name: str
    phone_masked: str
    channel: str
    status: str
    booked_start: datetime | None
    interviewer_id: int | None
    needs_attention: bool
    bot_paused: bool
    last_message_at: datetime | None


class MessageOut(BaseModel):
    direction: str
    sender: str
    text: str
    intent: str | None
    at: datetime


class CandidateDetail(CandidateRow):
    messages: list[MessageOut]


class InviteOut(BaseModel):
    channel: str
    sent: bool
    telegram_link: str | None = None


class ReplyIn(BaseModel):
    model_config = Strict
    text: str = Field(min_length=1, max_length=1000)


class OutcomeIn(BaseModel):
    model_config = Strict
    outcome: Literal["attended", "no_show"]


class Kpis(BaseModel):
    invited: int
    booked: int
    zero_touch_pct: float
    reminders_sent: int
    no_shows_7d: int
    needs_attention: int


class ChannelIn(BaseModel):
    model_config = Strict
    kind: Literal["whatsapp", "telegram"]
    # WhatsApp
    phone_number_id: str | None = Field(default=None, max_length=64)
    access_token: str | None = Field(default=None, max_length=1000)
    app_secret: str | None = Field(default=None, max_length=200)
    verify_token: str | None = Field(default=None, max_length=200)
    invite_template: str | None = Field(default="interview_invite", max_length=100)
    # Telegram
    bot_token: str | None = Field(default=None, max_length=200)
    bot_username: str | None = Field(default=None, max_length=100)


class ChannelOut(BaseModel):
    kind: str
    configured: bool
    webhook_path: str | None = None
    webhook_secret: str | None = None  # shown once for Telegram setWebhook


class PauseIn(BaseModel):
    model_config = Strict
    paused: bool


class AuditOut(BaseModel):
    at: datetime
    actor_type: str
    actor_id: int | None
    action: str
    record_type: str | None
    record_id: int | None
    result: str


class HealthOut(BaseModel):
    database: bool
    channels: dict[str, bool]
    llm_configured: bool
    messaging_paused: bool
    candidates_without_consent: int
