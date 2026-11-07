"""PUBLIC WEBHOOK RECEIVER — WhatsApp & Telegram only. No sessions, no portal data.

Runs as its own process:  uvicorn peoplepilot.apps.webhooks.main:app --port 8003
Every request is authenticated by the platform's signature/secret BEFORE parsing.
Responses never reveal whether a phone number or candidate exists.
"""
from __future__ import annotations

import json
import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_session, init_db, set_tenant
from ...models import Candidate, ChannelConfig
from ...scheduling import engine
from ...security.crypto import constant_time_eq, decrypt_json, encrypt, lookup_hash, sha256
from ...security.ratelimit import webhook_limiter
from ...channels import telegram as tg
from ...channels import whatsapp as wa
from ..common import lifespan, harden

log = logging.getLogger("peoplepilot.webhooks")
MAX_BODY = 256_000

app = FastAPI(title="Reporter Webhooks", docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=lifespan)
harden(app, origin=None, csrf_exempt=("/webhooks/",))



async def _body(request: Request) -> bytes:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Too large")
    return raw


# ------------------------------------------------------------------ WhatsApp
@app.get("/webhooks/whatsapp")
def wa_verify(request: Request, session: Session = Depends(get_session)):
    """Meta's one-time subscription handshake."""
    p = request.query_params
    if p.get("hub.mode") != "subscribe" or not p.get("hub.verify_token"):
        raise HTTPException(403, "Forbidden")
    for cfg in session.scalars(select(ChannelConfig).where(ChannelConfig.kind == "whatsapp")):
        if constant_time_eq(decrypt_json(cfg.config_enc).get("verify_token", ""), p["hub.verify_token"]):
            return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(403, "Forbidden")


@app.post("/webhooks/whatsapp")
async def wa_inbound(request: Request, session: Session = Depends(get_session)):
    raw = await _body(request)
    try:
        payload = json.loads(raw)
        pnid = payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(403, "Forbidden")
    cfg = session.scalars(select(ChannelConfig).where(ChannelConfig.kind == "whatsapp",
                                                      ChannelConfig.lookup_key == str(pnid))).first()
    if cfg is None or not wa.verify_signature(decrypt_json(cfg.config_enc)["app_secret"], raw,
                                              request.headers.get("x-hub-signature-256")):
        raise HTTPException(403, "Forbidden")
    if not webhook_limiter.allow(f"wa:{cfg.tenant_id}"):
        raise HTTPException(429, "Slow down")
    set_tenant(session, cfg.tenant_id)
    for item in wa.parse_inbound(payload):
        if not item["from"]:
            continue
        phone_hash = lookup_hash("+" + item["from"].lstrip("+"))
        # Most recent active conversation for this number in this tenant.
        cand = session.scalars(select(Candidate).where(
            Candidate.tenant_id == cfg.tenant_id, Candidate.phone_hash == phone_hash,
            Candidate.channel == "whatsapp", Candidate.fsm_state != "new").order_by(Candidate.id.desc())).first()
        if cand is None:
            continue  # unknown sender: ignore silently
        engine.handle_inbound(session, cand, text=item["text"], button_token=item["button_token"])
    return {"ok": True}


# ------------------------------------------------------------------ Telegram
@app.post("/webhooks/telegram/{tenant_id}")
async def tg_inbound(tenant_id: int, request: Request, session: Session = Depends(get_session)):
    secret = request.headers.get("x-telegram-bot-api-secret-token", "")
    cfg = session.scalars(select(ChannelConfig).where(ChannelConfig.tenant_id == tenant_id,
                                                      ChannelConfig.kind == "telegram")).first()
    if cfg is None or not secret or not constant_time_eq(cfg.lookup_key, sha256(secret)):
        raise HTTPException(403, "Forbidden")
    if not webhook_limiter.allow(f"tg:{tenant_id}"):
        raise HTTPException(429, "Slow down")
    raw = await _body(request)
    try:
        update = tg.parse_update(json.loads(raw))
    except (ValueError, KeyError, TypeError):
        return {"ok": True}
    if not update:
        return {"ok": True}
    set_tenant(session, tenant_id)
    chat_hash = lookup_hash("tg:" + update["chat_id"])
    if update["start_token"]:
        cand = session.scalars(select(Candidate).where(
            Candidate.tenant_id == tenant_id, Candidate.invite_token_hash == sha256(update["start_token"]))).first()
        if cand is None:
            return {"ok": True}
        cand.invite_token_hash = None  # single use
        cand.channel_user_id_enc = encrypt(update["chat_id"])
        cand.channel_user_hash = chat_hash
        engine.offer_slots(session, cand)
        return {"ok": True}
    cand = session.scalars(select(Candidate).where(Candidate.tenant_id == tenant_id,
                                                   Candidate.channel_user_hash == chat_hash)
                           .order_by(Candidate.id.desc())).first()
    if cand is not None:
        engine.handle_inbound(session, cand, text=update["text"], button_token=update["button_token"])
    return {"ok": True}
