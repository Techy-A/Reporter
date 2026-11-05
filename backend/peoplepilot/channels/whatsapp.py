"""WhatsApp Business Cloud API adapter.

- Business-initiated first contact must be an approved *template* (the invite). The template
  should have one quick-reply button such as "See slots"; when tapped, the 24h customer-service
  window opens and we can send interactive slot buttons.
- Up to 3 options -> reply buttons; more -> interactive list (max 10 rows).
- Webhook payloads are verified with X-Hub-Signature-256 (HMAC-SHA256 of the raw body using
  the Meta app secret) before anything is parsed.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from .base import Outbound

log = logging.getLogger("peoplepilot.whatsapp")
GRAPH = "https://graph.facebook.com/v21.0"


def verify_signature(app_secret: str, raw_body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


class WhatsAppChannel:
    kind = "whatsapp"

    def __init__(self, phone_number_id: str, access_token: str, invite_template: str = "interview_invite") -> None:
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.invite_template = invite_template

    def _payload(self, msg: Outbound) -> dict:
        base = {"messaging_product": "whatsapp", "to": msg.to}
        if msg.template:
            return {
                **base,
                "type": "template",
                "template": {
                    "name": msg.template,
                    "language": {"code": "en"},
                    "components": [
                        {"type": "body", "parameters": [{"type": "text", "text": p} for p in msg.template_params]},
                        *(
                            [{"type": "button", "sub_type": "quick_reply", "index": "0",
                              "parameters": [{"type": "payload", "payload": msg.buttons[0].token}]}]
                            if msg.buttons else []
                        ),
                    ],
                },
            }
        if not msg.buttons:
            return {**base, "type": "text", "text": {"body": msg.text[:4096]}}
        if len(msg.buttons) <= 3:
            return {
                **base,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": msg.text[:1024]},
                    "action": {"buttons": [
                        {"type": "reply", "reply": {"id": b.token, "title": b.label[:20]}} for b in msg.buttons
                    ]},
                },
            }
        return {
            **base,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": msg.text[:1024]},
                "action": {
                    "button": "Choose",
                    "sections": [{"title": "Options", "rows": [
                        {"id": b.token, "title": b.label[:24]} for b in msg.buttons[:10]
                    ]}],
                },
            },
        }

    def send(self, msg: Outbound) -> None:
        resp = httpx.post(
            f"{GRAPH}/{self.phone_number_id}/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=self._payload(msg),
            timeout=20,
        )
        if resp.status_code >= 400:
            log.warning("WhatsApp send failed with status %s", resp.status_code)
            resp.raise_for_status()


def parse_inbound(payload: dict) -> list[dict]:
    """Extract {phone_number_id, from, text, button_token} items from a webhook payload."""
    out: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            pnid = value.get("metadata", {}).get("phone_number_id")
            for m in value.get("messages", []):
                item = {"phone_number_id": pnid, "from": m.get("from"), "text": None, "button_token": None}
                t = m.get("type")
                if t == "text":
                    item["text"] = m.get("text", {}).get("body", "")
                elif t == "interactive":
                    inter = m.get("interactive", {})
                    reply = inter.get("button_reply") or inter.get("list_reply") or {}
                    item["button_token"] = reply.get("id")
                elif t == "button":  # template quick reply
                    item["button_token"] = m.get("button", {}).get("payload")
                else:
                    item["text"] = ""  # media etc. -> handled as unknown
                out.append(item)
    return out
