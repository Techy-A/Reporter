"""Pure-function tests: slots, intent, redaction, portal OTP rules."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from peoplepilot.apps.portal.main import _dev_outbox
from peoplepilot.scheduling.intent import classify_rules, is_sensitive
from peoplepilot.scheduling.slots import Preference, find_slots
from peoplepilot.security.redact import redact

from .conftest import H, make_round, setup_tenant

MON = datetime(2026, 11, 9, 0, 0)  # a Monday, 05:30 IST


def _slots(**kw):
    base = dict(window_start=MON, window_end=MON + timedelta(days=5), day_start_hour=10, day_end_hour=18,
                duration=timedelta(minutes=30), buffer=timedelta(minutes=10), interviewer_ids=[1], busy={},
                tz_name="Asia/Kolkata", now=MON - timedelta(days=1), limit=3)
    base.update(kw)
    return find_slots(**base)


def test_slots_spread_across_days_within_hours():
    s = _slots()
    assert len(s) == 3 and len({x.start.date() for x in s}) == 3
    for x in s:
        local_h = (x.start + timedelta(hours=5, minutes=30)).hour
        assert 10 <= local_h < 18


def test_slots_respect_bookings_and_buffer():
    first = _slots(limit=1)[0]
    s = _slots(limit=40, busy={1: [(first.start, timedelta(minutes=30))]})
    for x in s:
        assert abs((x.start - first.start).total_seconds()) >= 40 * 60


def test_slots_use_second_interviewer_when_first_busy():
    first = _slots(limit=1)[0]
    s = _slots(limit=40, interviewer_ids=[1, 2], busy={1: [(first.start, timedelta(minutes=30))]})
    assert any(x.start == first.start and x.interviewer_id == 2 for x in s)


def test_slots_preference_after_hour():
    s = _slots(limit=10, preference=Preference(after_hour=15))
    assert s and all((x.start + timedelta(hours=5, minutes=30)).hour >= 15 for x in s)


def test_slots_skip_sunday_and_min_notice():
    s = _slots(limit=50, now=MON + timedelta(hours=6))  # 11:30 IST Monday
    assert all(x.start >= MON + timedelta(hours=9) for x in s)  # >= 3h notice
    assert all(x.start.weekday() != 6 for x in s)


def test_intent_rules():
    assert classify_rules("can't make it").name == "cancel"
    assert classify_rules("None of these work").name == "reschedule"
    it = classify_rules("kal subah")
    assert it.name == "time_preference" and it.tomorrow and it.before_hour == 12
    assert classify_rules("after 2").after_hour == 14
    assert classify_rules("after 11 am").after_hour == 11
    assert classify_rules("haan").name == "confirm"
    assert classify_rules("what's the salary?") is None


def test_sensitive_detection():
    for t in ("he harassed me", "I will send a legal notice", "mujhe dhamki di", "I want to kill myself"):
        assert is_sensitive(t), t
    assert not is_sensitive("I have fever, can we move it?")


def test_redaction():
    out = redact("Call 98765 43210 or +91-9876543210, mail a.b@x.com, PAN ABCDE1234F, "
                 "Aadhaar 1234 5678 9012, UAN 100123456789, IFSC HDFC0001234")
    for leaked in ("98765", "a.b@x.com", "ABCDE1234F", "5678", "100123456789", "HDFC0001234"):
        assert leaked not in out, leaked


def test_portal_otp_rules(admin_app, portal_app):
    admin, _ = setup_tenant(admin_app)
    make_round(admin)
    p = TestClient(portal_app, base_url="https://me.test")
    known = p.post("/api/auth/code", headers=H, json={"email": "iv@acme.co.in"})
    unknown = p.post("/api/auth/code", headers=H, json={"email": "ghost@acme.co.in"})
    assert known.json() == unknown.json()  # no enumeration
    code = _dev_outbox[-1][1]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert p.post("/api/auth/verify", headers=H, json={"email": "iv@acme.co.in", "code": wrong}).status_code == 401
    # Locked after 5 wrong attempts: even the right code fails now.
    assert p.post("/api/auth/verify", headers=H, json={"email": "iv@acme.co.in", "code": code}).status_code == 401


def test_portal_code_single_use(admin_app, portal_app):
    admin, _ = setup_tenant(admin_app)
    make_round(admin)
    p = TestClient(portal_app, base_url="https://me.test")
    p.post("/api/auth/code", headers=H, json={"email": "iv@acme.co.in"})
    code = _dev_outbox[-1][1]
    assert p.post("/api/auth/verify", headers=H, json={"email": "iv@acme.co.in", "code": code}).status_code == 204
    p2 = TestClient(portal_app, base_url="https://me.test")
    assert p2.post("/api/auth/verify", headers=H, json={"email": "iv@acme.co.in", "code": code}).status_code == 401
