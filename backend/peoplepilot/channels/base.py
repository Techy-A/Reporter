"""Messaging channel interface + registry.

Buttons carry only opaque nonce tokens (see security/nonce.py), never data or actions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ChannelConfig
from ..security.crypto import decrypt_json


@dataclass
class Button:
    label: str
    token: str


@dataclass
class Outbound:
    to: str  # channel user id (WhatsApp number / Telegram chat id)
    text: str
    buttons: list[Button] = field(default_factory=list)
    template: str | None = None  # WhatsApp template name for business-initiated messages
    template_params: list[str] = field(default_factory=list)


class Channel(Protocol):
    kind: str

    def send(self, msg: Outbound) -> None: ...


class FakeChannel:
    """Records messages in memory. Used in tests and in dev before a channel is configured."""

    kind = "fake"

    def __init__(self) -> None:
        self.sent: list[Outbound] = []

    def send(self, msg: Outbound) -> None:
        self.sent.append(msg)


# Tests/dev can force a channel implementation for every tenant.
_override: Channel | None = None


def set_channel_override(channel: Channel | None) -> None:
    global _override
    _override = channel


def get_channel(session: Session, tenant_id: int, kind: str) -> Channel:
    if _override is not None:
        return _override
    cfg = session.scalars(
        select(ChannelConfig).where(ChannelConfig.tenant_id == tenant_id, ChannelConfig.kind == kind)
    ).first()
    if cfg is None:
        raise LookupError(f"{kind} channel is not configured")
    data = decrypt_json(cfg.config_enc)
    if kind == "whatsapp":
        from .whatsapp import WhatsAppChannel

        return WhatsAppChannel(phone_number_id=data["phone_number_id"], access_token=data["access_token"],
                               invite_template=data.get("invite_template", "interview_invite"))
    if kind == "telegram":
        from .telegram import TelegramChannel

        return TelegramChannel(bot_token=data["bot_token"])
    raise LookupError(kind)
