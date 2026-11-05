"""Candidate conversation state machine (the "bank-style" button flow).

The state machine owns every transition. Free text is only classified (intent.py); the
result can trigger *offering* slots or a handoff, never a booking. Bookings happen only
when the candidate taps a server-minted, single-use button.

States: new -> invited -> choosing -> booked -> confirmed
        any -> needs_recruiter | cancelled ; booked/confirmed -> done (attended / no_show)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import audit
from ..channels.base import Button, Outbound, get_channel
from ..db import utcnow
from ..models import Candidate, Employee, Message, Round, RoundInterviewer, Tenant
from ..security import nonce
from ..security.crypto import decrypt, new_token, sha256
from ..security.redact import redact
from .intent import Intent, classify
from .slots import Preference, find_slots, format_slot

log = logging.getLogger("peoplepilot.engine")

HANDOFF_TEXT = "Thanks! I've passed your message to the recruiter. They'll reply to you here soon."
SENSITIVE_TEXT = ("Thank you for telling us. A member of our hiring team will contact you personally. "
                  "This conversation is no longer handled by the automated assistant.")
ACTIVE_STATES = {"invited", "choosing", "booked", "confirmed"}


# ------------------------------------------------------------------ helpers
def _tenant(session: Session, cand: Candidate) -> Tenant:
    return session.get(Tenant, cand.tenant_id)  # type: ignore[return-value]


def _round(session: Session, cand: Candidate) -> Round:
    return session.get(Round, cand.round_id)  # type: ignore[return-value]


def _first_name(cand: Candidate) -> str:
    return (cand.name.split() or ["there"])[0]


def channel_address(cand: Candidate) -> str:
    if cand.channel_user_id_enc:
        return decrypt(cand.channel_user_id_enc)
    return decrypt(cand.phone_enc).lstrip("+")


def log_message(session: Session, cand: Candidate, direction: str, sender: str, text: str,
                intent: str | None = None) -> None:
    session.add(Message(tenant_id=cand.tenant_id, candidate_id=cand.id, direction=direction, sender=sender,
                        text_redacted=redact(text)[:2000], intent=intent))
    cand.last_message_at = utcnow()


def send(session: Session, cand: Candidate, text: str, buttons: list[Button] | None = None, *,
         sender: str = "bot", template: str | None = None, template_params: list[str] | None = None) -> bool:
    tenant = _tenant(session, cand)
    if tenant.messaging_paused:
        audit(session, tenant_id=cand.tenant_id, actor_type="system", actor_id=None, action="send_blocked_paused",
              record_type="candidate", record_id=cand.id, result="blocked")
        return False
    channel = get_channel(session, cand.tenant_id, cand.channel)
    channel.send(Outbound(to=channel_address(cand), text=text, buttons=buttons or [], template=template,
                          template_params=template_params or []))
    shown = text + ("".join(f"\n[{b.label}]" for b in buttons) if buttons else "")
    log_message(session, cand, "out", sender, shown)
    return True


def _busy_for(session: Session, tenant_id: int, interviewer_ids: list[int], exclude_candidate: int | None):
    busy: dict[int, list[tuple[datetime, timedelta]]] = {i: [] for i in interviewer_ids}
    rows = session.execute(
        select(Candidate.id, Candidate.interviewer_id, Candidate.booked_start, Round.duration_min)
        .join(Round, Round.id == Candidate.round_id)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.interviewer_id.in_(interviewer_ids),
            Candidate.booked_start.is_not(None),
            Candidate.fsm_state.in_(["booked", "confirmed"]),
        )
    ).all()
    for cid, iid, start, dur in rows:
        if cid != exclude_candidate:
            busy[iid].append((start, timedelta(minutes=dur)))
    return busy


def _interviewers(session: Session, rnd: Round) -> list[int]:
    return list(session.scalars(
        select(RoundInterviewer.employee_id)
        .join(Employee, Employee.id == RoundInterviewer.employee_id)
        .where(RoundInterviewer.round_id == rnd.id, RoundInterviewer.tenant_id == rnd.tenant_id,
               Employee.active.is_(True))
        .order_by(RoundInterviewer.id)
    ))


def available_slots(session: Session, cand: Candidate, pref: Preference | None = None):
    rnd = _round(session, cand)
    tenant = _tenant(session, cand)
    ids = _interviewers(session, rnd)
    return find_slots(
        window_start=rnd.window_start, window_end=rnd.window_end,
        day_start_hour=rnd.day_start_hour, day_end_hour=rnd.day_end_hour,
        duration=timedelta(minutes=rnd.duration_min), buffer=timedelta(minutes=rnd.buffer_min),
        interviewer_ids=ids, busy=_busy_for(session, cand.tenant_id, ids, cand.id),
        tz_name=tenant.timezone, now=utcnow(), limit=rnd.max_slots_offered, preference=pref,
        exclude={cand.booked_start} if cand.booked_start else None,
    )


# ------------------------------------------------------------------ transitions
def handoff(session: Session, cand: Candidate, reason: str, text: str = HANDOFF_TEXT) -> None:
    nonce.invalidate_all(session, tenant_id=cand.tenant_id, candidate_id=cand.id)
    cand.needs_attention = True
    cand.fsm_state = "needs_recruiter"
    cand.status = "needs_recruiter"
    audit(session, tenant_id=cand.tenant_id, actor_type="system", actor_id=None, action=f"handoff:{reason}",
          record_type="candidate", record_id=cand.id)
    send(session, cand, text)


def invite(session: Session, cand: Candidate, *, admin_id: int) -> dict:
    """Send (WhatsApp) or prepare (Telegram) the first invitation."""
    if not cand.consent:
        raise PermissionError("Candidate has not consented to messages")
    tenant = _tenant(session, cand)
    rnd = _round(session, cand)
    result: dict = {"channel": cand.channel}
    if cand.channel == "whatsapp":
        token = nonce.mint(session, tenant_id=cand.tenant_id, candidate_id=cand.id, action="see_slots", payload={})
        ok = send(session, cand,
                  f"Hi {_first_name(cand)}, you're shortlisted for {rnd.role_title} at {tenant.name}. "
                  "Tap below to pick an interview slot.",
                  [Button("See slots", token)], template="interview_invite",
                  template_params=[_first_name(cand), rnd.role_title, tenant.name])
        result["sent"] = ok
    else:
        raw = new_token(16)
        cand.invite_token_hash = sha256(raw)
        result["start_token"] = raw  # recruiter shares t.me/<bot>?start=<token>
        result["sent"] = False
    cand.fsm_state = "invited"
    cand.status = "invited"
    audit(session, tenant_id=cand.tenant_id, actor_type="admin", actor_id=admin_id, action="candidate_invited",
          record_type="candidate", record_id=cand.id)
    return result


def offer_slots(session: Session, cand: Candidate, pref: Preference | None = None, intro: str | None = None) -> None:
    slots = available_slots(session, cand, pref)
    if not slots and pref is not None:
        intro = "I couldn't find a slot matching that. Here are the nearest available options:"
        slots = available_slots(session, cand, None)
    if not slots:
        handoff(session, cand, "no_slots",
                "All slots are currently full. The recruiter will contact you with more options.")
        return
    tz = _tenant(session, cand).timezone
    nonce.invalidate_all(session, tenant_id=cand.tenant_id, candidate_id=cand.id)
    buttons = [
        Button(format_slot(s.start, tz), nonce.mint(session, tenant_id=cand.tenant_id, candidate_id=cand.id,
                                                   action="book",
                                                   payload={"start": s.start.isoformat(), "iid": s.interviewer_id}))
        for s in slots
    ]
    buttons.append(Button("None of these work", nonce.mint(session, tenant_id=cand.tenant_id, candidate_id=cand.id,
                                                           action="none", payload={})))
    rnd = _round(session, cand)
    send(session, cand, (intro or f"Please pick a slot for your {rnd.round_name} interview "
                                  f"({rnd.duration_min} min):"), buttons)
    cand.fsm_state = "choosing"
    if cand.status not in ("booked", "rescheduled", "confirmed"):
        cand.status = "choosing"


def _details(session: Session, cand: Candidate) -> str:
    rnd = _round(session, cand)
    tz = _tenant(session, cand).timezone
    where = f"Address: {rnd.location}" if rnd.mode == "in_person" else f"Video link: {rnd.location}"
    interviewer = session.get(Employee, cand.interviewer_id) if cand.interviewer_id else None
    who = f"\nInterviewer: {interviewer.name}" if interviewer else ""
    return f"{rnd.role_title} – {rnd.round_name}\nWhen: {format_slot(cand.booked_start, tz)}\n{where}{who}"


def _manage_buttons(session: Session, cand: Candidate, with_confirm: bool = False) -> list[Button]:
    mint = lambda action: nonce.mint(session, tenant_id=cand.tenant_id, candidate_id=cand.id,  # noqa: E731
                                     action=action, payload={})
    buttons = [Button("Confirm", mint("confirm"))] if with_confirm else []
    return buttons + [Button("Reschedule", mint("reschedule")), Button("Can't make it", mint("cancel"))]


def book(session: Session, cand: Candidate, payload: dict) -> None:
    start = datetime.fromisoformat(payload["start"])
    iid = int(payload["iid"])
    rnd = _round(session, cand)
    if iid not in _interviewers(session, rnd):
        offer_slots(session, cand, intro="That slot is no longer available. Here are the latest options:")
        return
    busy = _busy_for(session, cand.tenant_id, [iid], cand.id)[iid]
    dur, buf = timedelta(minutes=rnd.duration_min), timedelta(minutes=rnd.buffer_min)
    from .slots import overlaps

    if start < utcnow() or any(overlaps(start - buf, dur + 2 * buf, b, bl) for b, bl in busy):
        offer_slots(session, cand, intro="Sorry, that slot was just taken. Here are the latest options:")
        return
    was_booked = cand.booked_start is not None
    cand.booked_start, cand.interviewer_id = start, iid
    cand.fsm_state = "booked"
    cand.status = "rescheduled" if was_booked else "booked"
    cand.needs_attention = False
    nonce.invalidate_all(session, tenant_id=cand.tenant_id, candidate_id=cand.id)
    audit(session, tenant_id=cand.tenant_id, actor_type="candidate", actor_id=cand.id, action="slot_booked",
          record_type="candidate", record_id=cand.id)
    send(session, cand, "You're booked! ✅\n" + _details(session, cand), _manage_buttons(session, cand))


def cancel(session: Session, cand: Candidate, *, by: str = "candidate", actor_id: int | None = None) -> None:
    nonce.invalidate_all(session, tenant_id=cand.tenant_id, candidate_id=cand.id)
    cand.fsm_state = "cancelled"
    cand.status = "cant_make_it" if by == "candidate" else "cancelled"
    cand.booked_start = None
    cand.interviewer_id = None
    audit(session, tenant_id=cand.tenant_id, actor_type=by, actor_id=actor_id, action="booking_cancelled",
          record_type="candidate", record_id=cand.id)
    if by == "candidate":
        send(session, cand, "No problem, we've cancelled your interview. The recruiter has been informed.")


# ------------------------------------------------------------------ inbound
def handle_button(session: Session, cand: Candidate, token: str) -> None:
    log_message(session, cand, "in", "candidate", "[button]")
    if cand.bot_paused or cand.fsm_state in ("needs_recruiter", "cancelled", "done"):
        cand.needs_attention = cand.fsm_state != "done"
        return
    row = nonce.redeem(session, token=token, tenant_id=cand.tenant_id, candidate_id=cand.id)
    if row is None:
        audit(session, tenant_id=cand.tenant_id, actor_type="candidate", actor_id=cand.id,
              action="stale_or_invalid_button", record_type="candidate", record_id=cand.id, result="rejected")
        if cand.fsm_state in ("invited", "choosing"):
            offer_slots(session, cand, intro="That option has expired. Here are the latest options:")
        else:
            send(session, cand, "That button has expired. Please use the latest message.")
        return
    if row.action in ("see_slots", "reschedule"):
        offer_slots(session, cand)
    elif row.action == "book":
        book(session, cand, row.payload)
    elif row.action == "none":
        send(session, cand, "No worries. Tell me what suits you, e.g. \"after 3 pm\" or \"tomorrow morning\".")
        cand.fsm_state = "choosing"
    elif row.action == "confirm":
        cand.fsm_state = cand.status = "confirmed"
        send(session, cand, "Thanks for confirming. See you then!")
    elif row.action == "cancel":
        cancel(session, cand)


def _pref_from_intent(session: Session, cand: Candidate, it: Intent) -> Preference:
    on_date = None
    if it.tomorrow:
        from zoneinfo import ZoneInfo
        from datetime import timezone as _tz

        tz = ZoneInfo(_tenant(session, cand).timezone)
        on_date = (datetime.now(_tz.utc).astimezone(tz) + timedelta(days=1)).date()
    return Preference(after_hour=it.after_hour, before_hour=it.before_hour, on_date=on_date)


def handle_text(session: Session, cand: Candidate, text: str) -> Intent | None:
    if cand.bot_paused or cand.fsm_state in ("needs_recruiter",):
        log_message(session, cand, "in", "candidate", text)
        cand.needs_attention = True
        return None
    it = classify(text)
    # Sensitive messages: stored only as a marker, never the content.
    log_message(session, cand, "in", "candidate", "[sensitive message withheld]" if it.sensitive else text, it.name)
    if it.sensitive:
        handoff(session, cand, "sensitive", SENSITIVE_TEXT)
        return it
    if cand.fsm_state in ("cancelled", "done", "new"):
        handoff(session, cand, f"message_in_{cand.fsm_state}")
        return it
    if it.name == "cancel":
        cancel(session, cand)
    elif it.name in ("reschedule", "time_preference"):
        offer_slots(session, cand, _pref_from_intent(session, cand, it) if it.name == "time_preference" else None)
    elif it.name == "confirm" and cand.fsm_state == "booked":
        cand.fsm_state = cand.status = "confirmed"
        send(session, cand, "Thanks for confirming. See you then!")
    elif it.name in ("greeting", "confirm") and cand.fsm_state in ("invited", "choosing"):
        offer_slots(session, cand)
    else:
        handoff(session, cand, "unknown_text")
    return it


def handle_inbound(session: Session, cand: Candidate, *, text: str | None, button_token: str | None) -> None:
    if button_token:
        handle_button(session, cand, button_token)
    elif text is not None:
        handle_text(session, cand, text)


# ------------------------------------------------------------------ recruiter actions
def recruiter_reply(session: Session, cand: Candidate, text: str, admin_id: int) -> None:
    cand.bot_paused = True
    cand.recruiter_touches += 1
    send(session, cand, text, sender="recruiter")
    audit(session, tenant_id=cand.tenant_id, actor_type="admin", actor_id=admin_id, action="recruiter_reply",
          record_type="candidate", record_id=cand.id)


def resume_bot(session: Session, cand: Candidate, admin_id: int) -> None:
    cand.bot_paused = False
    cand.needs_attention = False
    audit(session, tenant_id=cand.tenant_id, actor_type="admin", actor_id=admin_id, action="bot_resumed",
          record_type="candidate", record_id=cand.id)
    if cand.booked_start:
        cand.fsm_state = cand.status = "booked"
    else:
        offer_slots(session, cand)


# ------------------------------------------------------------------ reminders
def due_reminders(session: Session, now: datetime | None = None) -> int:
    """Send T-24h and T-2h reminders. Idempotent: each (candidate, kind, slot) is sent once."""
    from ..models import ReminderSent

    now = now or utcnow()
    sent = 0
    rows = session.scalars(
        select(Candidate).where(Candidate.fsm_state.in_(["booked", "confirmed"]), Candidate.booked_start > now,
                                Candidate.booked_start <= now + timedelta(hours=24))
    ).all()
    for cand in rows:
        kind = "t2" if cand.booked_start - now <= timedelta(hours=2) else "t24"
        exists = session.scalars(select(ReminderSent).where(
            ReminderSent.candidate_id == cand.id, ReminderSent.kind == kind,
            ReminderSent.slot_start == cand.booked_start)).first()
        if exists or cand.bot_paused:
            continue
        session.add(ReminderSent(tenant_id=cand.tenant_id, candidate_id=cand.id, kind=kind,
                                 slot_start=cand.booked_start))
        if kind == "t24":
            ok = send(session, cand, "Reminder: your interview is tomorrow.\n" + _details(session, cand),
                      _manage_buttons(session, cand, with_confirm=cand.fsm_state == "booked"))
        else:
            ok = send(session, cand, "Your interview starts in about 2 hours.\n" + _details(session, cand))
        sent += int(ok)
    return sent
