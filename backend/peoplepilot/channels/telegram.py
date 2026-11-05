"""Telegram Bot API adapter (free; the fallback while Meta WhatsApp verification is pending).

A bot cannot message someone first. The recruiter shares a deep link
https://t.me/<bot>?start=<invite token>; the /start payload binds the chat to the candidate.
Webhooks are authenticated with the X-Telegram-Bot-Api-Secret-Token header set via setWebhook.
"""
from __future__ import annotations

import logging

import httpx

from .base import Outbound

log = logging.getLogger("peoplepilot.telegram")


class TelegramChannel:
    kind = "telegram"

    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token

    def send(self, msg: Outbound) -> None:
        body: dict = {"chat_id": msg.to, "text": msg.text[:4096]}
        if msg.buttons:
            body["reply_markup"] = {
                "inline_keyboard": [[{"text": b.label[:40], "callback_data": b.token[:64]}] for b in msg.buttons]
            }
        resp = httpx.post(f"https://api.telegram.org/bot{self.bot_token}/sendMessage", json=body, timeout=20)
        if resp.status_code >= 400:
            log.warning("Telegram send failed with status %s", resp.status_code)
            resp.raise_for_status()


def parse_update(update: dict) -> dict | None:
    """Return {chat_id, text, button_token, start_token} or None."""
    if "callback_query" in update:
        cq = update["callback_query"]
        return {"chat_id": str(cq["message"]["chat"]["id"]), "text": None, "button_token": cq.get("data"),
                "start_token": None}
    msg = update.get("message")
    if not msg:
        return None
    text = msg.get("text", "") or ""
    start = None
    if text.startswith("/start "):
        start, text = text.split(" ", 1)[1].strip(), None
    return {"chat_id": str(msg["chat"]["id"]), "text": text, "button_token": None, "start_token": start}
