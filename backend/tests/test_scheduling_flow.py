"""End-to-end: recruiter invites, candidate books over WhatsApp via signed webhooks."""
from datetime import timedelta

from fastapi.testclient import TestClient

from peoplepilot import db
from peoplepilot.apps.portal.main import _dev_outbox
from peoplepilot.models import Candidate, Message
from peoplepilot.scheduling.engine import due_reminders

from .conftest import H, configure_whatsapp, make_round, setup_tenant, upload, wa_msg, wa_post


def _ready(admin_app, fake):
    c, _ = setup_tenant(admin_app)
    configure_whatsapp(c)
    rnd, emp = make_round(c)
    upload(c, rnd["id"])
    cand_id = c.get("/api/candidates").json()[0]["id"]
    r = c.post(f"/api/candidates/{cand_id}/invite", headers=H)
    assert r.status_code == 200 and r.json()["sent"] is True
    return c, cand_id, emp


def test_full_booking_flow(admin_app, webhook_app, fake):
    c, cand_id, _ = _ready(admin_app, fake)
    invite = fake.sent[-1]
    assert invite.template == "interview_invite" and invite.to == "919876543210"
    w = TestClient(webhook_app, base_url="https://hooks.test")

    # Candidate taps "See slots" on the template.
    assert wa_post(w, wa_msg(button=invite.buttons[0].token)).status_code == 200
    offer = fake.sent[-1]
    assert len(offer.buttons) == 4 and offer.buttons[-1].label == "None of these work"

    # Candidate picks the first slot.
    assert wa_post(w, wa_msg(button=offer.buttons[0].token)).status_code == 200
    assert "You're booked" in fake.sent[-1].text
    row = c.get(f"/api/candidates/{cand_id}").json()
    assert row["status"] == "booked" and row["booked_start"]

    kpis = c.get("/api/kpis").json()
    assert kpis["booked"] == 1 and kpis["zero_touch_pct"] == 100.0


def test_replayed_and_foreign_buttons_do_nothing(admin_app, webhook_app, fake):
    c, cand_id, _ = _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(button=fake.sent[-1].buttons[0].token))
    offer = fake.sent[-1]
    wa_post(w, wa_msg(button=offer.buttons[0].token))
    booked_at = c.get(f"/api/candidates/{cand_id}").json()["booked_start"]

    # Replay an old slot button -> rejected, booking unchanged.
    wa_post(w, wa_msg(button=offer.buttons[1].token))
    assert c.get(f"/api/candidates/{cand_id}").json()["booked_start"] == booked_at
    # Forged token -> rejected.
    wa_post(w, wa_msg(button="forged-token-xyz"))
    assert c.get(f"/api/candidates/{cand_id}").json()["booked_start"] == booked_at
    audit = [a["action"] for a in c.get("/api/audit").json()]
    assert audit.count("stale_or_invalid_button") >= 2


def test_unknown_sender_gets_nothing(admin_app, webhook_app, fake):
    _ready(admin_app, fake)
    n = len(fake.sent)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    assert wa_post(w, wa_msg(frm="919000000000", text="hi, what slots do you have?")).status_code == 200
    assert len(fake.sent) == n


def test_bad_signature_rejected(admin_app, webhook_app, fake):
    _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    assert wa_post(w, wa_msg(text="hi"), secret="not-the-secret").status_code == 403
    assert w.post("/webhooks/whatsapp", json=wa_msg(text="hi")).status_code == 403  # unsigned


def test_hinglish_time_preference(admin_app, webhook_app, fake):
    _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(text="bhaiya 3 baje ke baad ho sakta hai?"))
    offer = fake.sent[-1]
    hours = [int(b.label.split(", ")[1].split(":")[0]) for b in offer.buttons[:-1]]
    assert hours and all(h >= 15 for h in hours)


def test_unknown_text_hands_off_to_recruiter(admin_app, webhook_app, fake):
    c, cand_id, _ = _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(text="What is the salary for this role?"))
    row = c.get(f"/api/candidates/{cand_id}").json()
    assert row["needs_attention"] is True and row["status"] == "needs_recruiter"


def test_sensitive_message_not_stored_and_handed_off(admin_app, webhook_app, fake, monkeypatch):
    called = []
    monkeypatch.setattr("peoplepilot.scheduling.intent.classify_llm", lambda t: called.append(t))
    c, cand_id, _ = _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(text="the last interviewer harassed me"))
    assert called == []  # never reached the LLM
    s = db.session_scope()
    texts = [m.text_redacted for m in s.query(Message).filter_by(candidate_id=cand_id)]
    s.close()
    assert not any("harassed" in t for t in texts)
    assert c.get(f"/api/candidates/{cand_id}").json()["needs_attention"] is True


def test_kill_switch_stops_messages(admin_app, webhook_app, fake):
    c, cand_id, _ = _ready(admin_app, fake)
    assert c.post("/api/settings/pause", headers=H, json={"paused": True}).status_code == 204
    n = len(fake.sent)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(text="hello"))
    assert len(fake.sent) == n


def test_recruiter_takeover_pauses_bot(admin_app, webhook_app, fake):
    c, cand_id, _ = _ready(admin_app, fake)
    assert c.post(f"/api/candidates/{cand_id}/reply", headers=H, json={"text": "Hi Riya, call me?"}).status_code == 204
    n = len(fake.sent)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(text="ok after 4"))
    assert len(fake.sent) == n  # bot stays quiet while a human handles it
    assert c.get("/api/kpis").json()["needs_attention"] == 1


def test_reminders_are_idempotent(admin_app, webhook_app, fake):
    c, cand_id, _ = _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(button=fake.sent[-1].buttons[0].token))
    wa_post(w, wa_msg(button=fake.sent[-1].buttons[0].token))
    s = db.session_scope()
    cand = s.get(Candidate, cand_id)
    now = cand.booked_start - timedelta(hours=20)
    assert due_reminders(s, now) == 1
    assert due_reminders(s, now) == 0
    assert due_reminders(s, cand.booked_start - timedelta(hours=1)) == 1
    s.commit()
    s.close()


def test_interviewer_sees_only_own_interviews_without_contact_data(admin_app, webhook_app, portal_app, fake):
    c, cand_id, emp = _ready(admin_app, fake)
    w = TestClient(webhook_app, base_url="https://hooks.test")
    wa_post(w, wa_msg(button=fake.sent[-1].buttons[0].token))
    wa_post(w, wa_msg(button=fake.sent[-1].buttons[0].token))
    c.post("/api/employees", headers=H, json={"name": "Other Interviewer", "email": "other@acme.co.in"})

    def login(email):
        p = TestClient(portal_app, base_url="https://me.test")
        _dev_outbox.clear()
        p.post("/api/auth/code", headers=H, json={"email": email})
        p.post("/api/auth/verify", headers=H, json={"email": email, "code": _dev_outbox[-1][1]})
        return p

    mine = login("iv@acme.co.in").get("/api/me/interviews").json()
    assert len(mine) == 1
    assert mine[0]["candidate_first_name"] == "Riya"
    blob = str(mine)
    assert "Verma" not in blob and "9876543210" not in blob and "3210" not in blob and "@" not in blob

    other = login("other@acme.co.in")
    assert other.get("/api/me/interviews").json() == []
    assert other.get(f"/api/me/interviews/{cand_id}.ics").status_code == 404
    assert other.post(f"/api/me/interviews/{cand_id}/outcome", headers=H,
                      json={"outcome": "no_show"}).status_code == 404
