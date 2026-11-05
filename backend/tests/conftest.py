import base64
import hashlib
import hmac
import json
import os
import re
from datetime import date, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet

os.environ.update({
    "PP_ENV_FILE": "does-not-exist.env",  # never read a developer's local .env in tests
    "PP_ENV": "test",
    "PP_ADMIN_JWT_KEY": "a" * 48,
    "PP_PORTAL_JWT_KEY": "p" * 48,
    "PP_DATA_KEY": Fernet.generate_key().decode(),
    "PP_HMAC_KEY": "h" * 48,
    "PP_SETUP_TOKEN": "setup-token-for-tests",
})

from fastapi.testclient import TestClient  # noqa: E402

from peoplepilot import db  # noqa: E402
from peoplepilot.channels.base import FakeChannel, set_channel_override  # noqa: E402
from peoplepilot.config import get_settings  # noqa: E402
from peoplepilot.security import ratelimit  # noqa: E402

H = {"x-pp-request": "1"}
APP_SECRET = "wa-app-secret"


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PP_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    get_settings.cache_clear()
    db.reset_engine()
    db.init_db()
    for lim in (ratelimit.admin_login_limiter, ratelimit.portal_code_limiter, ratelimit.webhook_limiter):
        lim.reset()
    yield
    db.reset_engine()


@pytest.fixture
def fake():
    ch = FakeChannel()
    set_channel_override(ch)
    yield ch
    set_channel_override(None)


@pytest.fixture
def admin_app():
    from peoplepilot.apps.admin.main import app
    return app


@pytest.fixture
def portal_app():
    from peoplepilot.apps.portal.main import app
    return app


@pytest.fixture
def webhook_app():
    from peoplepilot.apps.webhooks.main import app
    return app


def new_admin_client(app):
    return TestClient(app, base_url="https://admin.test")


def setup_tenant(admin_app, email="owner@acme.co.in", org="Acme"):
    """Run first-run setup + MFA. Returns (client, totp)."""
    c = new_admin_client(admin_app)
    r = c.post("/api/setup", headers=H, json={
        "setup_token": "setup-token-for-tests", "org_name": org, "org_kind": "company",
        "email": email, "password": "correct horse battery staple"})
    assert r.status_code == 201, r.text
    uri = c.post("/api/auth/mfa/setup", headers=H).json()["otpauth_uri"]
    totp = pyotp.TOTP(re.search(r"secret=([A-Z2-7]+)", uri).group(1))
    assert c.post("/api/auth/mfa/confirm", headers=H, json={"code": totp.now()}).status_code == 204
    return c, totp


def make_round(c, interviewer_email="iv@acme.co.in", interviewer_name="Priya Sharma"):
    emp = c.post("/api/employees", headers=H, json={"name": interviewer_name, "email": interviewer_email}).json()
    today = date.today()
    r = c.post("/api/rounds", headers=H, json={
        "role_title": "Customer Support Associate", "round_name": "HR Round", "duration_min": 30,
        "buffer_min": 10, "mode": "video", "location": "https://meet.example/abc",
        "start_date": str(today + timedelta(days=1)), "end_date": str(today + timedelta(days=8)),
        "day_start_hour": 10, "day_end_hour": 18, "max_slots_offered": 3, "interviewer_ids": [emp["id"]]})
    assert r.status_code == 201, r.text
    return r.json(), emp


def upload(c, round_id, rows="name,phone,consent\nRiya Verma,98765 43210,yes\n"):
    r = c.post(f"/api/rounds/{round_id}/candidates/csv", headers=H,
               files={"file": ("c.csv", rows.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()


def configure_whatsapp(c, pnid="111"):
    r = c.put("/api/settings/channel", headers=H, json={
        "kind": "whatsapp", "phone_number_id": pnid, "access_token": "tok", "app_secret": APP_SECRET,
        "verify_token": "vt"})
    assert r.status_code == 200, r.text


def wa_post(client, body: dict, secret=APP_SECRET):
    raw = json.dumps(body).encode()
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/webhooks/whatsapp", content=raw,
                       headers={"x-hub-signature-256": sig, "content-type": "application/json"})


def wa_msg(frm="919876543210", pnid="111", text=None, button=None):
    m = {"from": frm}
    if button:
        m.update(type="interactive", interactive={"type": "button_reply", "button_reply": {"id": button}})
    else:
        m.update(type="text", text={"body": text})
    return {"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": pnid}, "messages": [m]}}]}]}
