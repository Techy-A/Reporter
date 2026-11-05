"""Admin portal: setup, MFA, lockout, tenant isolation, CSRF, headers, data minimisation."""
from fastapi.testclient import TestClient

from peoplepilot import db
from peoplepilot.models import AdminUser, Candidate, Tenant
from peoplepilot.security.crypto import encrypt, hash_password, lookup_hash

from .conftest import H, make_round, new_admin_client, setup_tenant, upload


def test_setup_requires_token_and_runs_once(admin_app):
    c = new_admin_client(admin_app)
    body = {"setup_token": "wrong-token-123456", "org_name": "Acme", "org_kind": "company",
            "email": "o@acme.co.in", "password": "correct horse battery staple"}
    assert c.post("/api/setup", headers=H, json=body).status_code == 403
    setup_tenant(admin_app)
    body["setup_token"] = "setup-token-for-tests"
    assert new_admin_client(admin_app).post("/api/setup", headers=H, json=body).status_code == 409


def test_mfa_required_before_data_access(admin_app):
    c = new_admin_client(admin_app)
    c.post("/api/setup", headers=H, json={"setup_token": "setup-token-for-tests", "org_name": "Acme",
                                          "org_kind": "company", "email": "o@acme.co.in",
                                          "password": "correct horse battery staple"})
    assert c.get("/api/candidates").status_code == 403
    assert c.get("/api/rounds").status_code == 403


def test_login_needs_totp_and_locks_out(admin_app):
    _, totp = setup_tenant(admin_app)
    c = new_admin_client(admin_app)
    creds = {"email": "owner@acme.co.in", "password": "correct horse battery staple"}
    assert c.post("/api/auth/login", headers=H, json=creds).json() == {"mfa_required": True,
                                                                       "mfa_setup_required": False}
    assert c.get("/api/candidates").status_code == 401  # no session yet
    assert c.post("/api/auth/login", headers=H, json={**creds, "totp": totp.now()}).status_code == 200
    assert c.get("/api/candidates").status_code == 200

    bad = new_admin_client(admin_app)
    for _ in range(5):
        assert bad.post("/api/auth/login", headers=H,
                        json={**creds, "password": "wrong password!!"}).status_code == 401
    # Locked now, even with the right password + code.
    assert bad.post("/api/auth/login", headers=H, json={**creds, "totp": totp.now()}).status_code == 401


def test_unknown_email_same_error(admin_app):
    setup_tenant(admin_app)
    c = new_admin_client(admin_app)
    a = c.post("/api/auth/login", headers=H, json={"email": "nobody@acme.co.in", "password": "x" * 12})
    b = c.post("/api/auth/login", headers=H, json={"email": "owner@acme.co.in", "password": "x" * 12})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_tenant_isolation(admin_app):
    c1, _ = setup_tenant(admin_app)
    rnd, _ = make_round(c1)
    upload(c1, rnd["id"])
    cand_id = c1.get("/api/candidates").json()[0]["id"]

    # A second organisation on the same install (created directly; setup only runs once).
    s = db.session_scope()
    t2 = Tenant(name="Other", kind="company")
    s.add(t2)
    s.flush()
    s.add(AdminUser(tenant_id=t2.id, email="o2@other.co.in", password_hash=hash_password("another long password"),
                    role="owner"))
    s.add(Candidate(tenant_id=t2.id, round_id=rnd["id"], name="Secret Person", phone_enc=encrypt("+919999999999"),
                    phone_hash=lookup_hash("+919999999999"), phone_last4="9999", consent=True))
    s.commit()
    s.close()

    c2 = new_admin_client(admin_app)
    c2.post("/api/auth/login", headers=H, json={"email": "o2@other.co.in", "password": "another long password"})
    import pyotp, re  # noqa: E401
    uri = c2.post("/api/auth/mfa/setup", headers=H).json()["otpauth_uri"]
    code = pyotp.TOTP(re.search(r"secret=([A-Z2-7]+)", uri).group(1)).now()
    assert c2.post("/api/auth/mfa/confirm", headers=H, json={"code": code}).status_code == 204

    names2 = [x["name"] for x in c2.get("/api/candidates").json()]
    assert "Riya Verma" not in names2 and names2 == ["Secret Person"]
    assert c2.get(f"/api/candidates/{cand_id}").status_code == 404
    assert c2.post(f"/api/candidates/{cand_id}/invite", headers=H).status_code == 404
    assert c2.get("/api/rounds").json() == []
    assert "Secret Person" not in [x["name"] for x in c1.get("/api/candidates").json()]


def test_board_masks_phone_and_hides_email(admin_app):
    c, _ = setup_tenant(admin_app)
    rnd, _ = make_round(c)
    upload(c, rnd["id"], "name,phone,email,consent\nRiya Verma,9876543210,riya@mail.co.in,yes\n")
    row = c.get("/api/candidates").json()[0]
    raw = str(row)
    assert "9876543210" not in raw and "riya@mail.co.in" not in raw
    assert row["phone_masked"].endswith("3210")


def test_phone_encrypted_at_rest(admin_app):
    c, _ = setup_tenant(admin_app)
    rnd, _ = make_round(c)
    upload(c, rnd["id"])
    s = db.session_scope()
    cand = s.query(Candidate).first()
    assert "9876543210" not in cand.phone_enc and "9876543210" not in cand.phone_hash
    s.close()


def test_csv_validation(admin_app):
    c, _ = setup_tenant(admin_app)
    rnd, _ = make_round(c)
    res = upload(c, rnd["id"], "name,phone,consent\n"
                               "Ok Person,9876543210,yes\n"
                               "No Consent,9876543211,no\n"
                               "Bad Phone,12345,yes\n"
                               "Dup Person,+91 98765 43210,yes\n"
                               "=HYPERLINK(evil),9876543212,yes\n")
    assert res["created"] == 2
    assert [e["row"] for e in res["errors"]] == [3, 4, 5]
    names = [x["name"] for x in c.get("/api/candidates").json()]
    assert all(not n.startswith("=") for n in names)


def test_csrf_header_required(admin_app):
    c, _ = setup_tenant(admin_app)
    r = c.post("/api/employees", json={"name": "X", "email": "x@acme.co.in"})
    assert r.status_code == 403


def test_security_headers_and_no_stack_traces(admin_app):
    c, _ = setup_tenant(admin_app)
    r = c.get("/api/kpis")
    for h in ("content-security-policy", "x-frame-options", "strict-transport-security", "cache-control"):
        assert h in r.headers
    assert r.headers["cache-control"] == "no-store"
    bad = c.post("/api/rounds", headers=H, json={"role_title": "x"})
    assert bad.status_code == 422
    assert "x" not in str(bad.json().get("fields"))  # values are not echoed
    assert "Traceback" not in bad.text


def test_recruiter_cannot_use_owner_settings(admin_app):
    c, _ = setup_tenant(admin_app)
    assert c.post("/api/admin-users", headers=H, json={"email": "rec@acme.co.in", "password": "recruiter password1",
                                                       "role": "recruiter"}).status_code == 201
    r = new_admin_client(admin_app)
    r.post("/api/auth/login", headers=H, json={"email": "rec@acme.co.in", "password": "recruiter password1"})
    import pyotp, re  # noqa: E401
    uri = r.post("/api/auth/mfa/setup", headers=H).json()["otpauth_uri"]
    r.post("/api/auth/mfa/confirm", headers=H,
           json={"code": pyotp.TOTP(re.search(r"secret=([A-Z2-7]+)", uri).group(1)).now()})
    assert r.get("/api/candidates").status_code == 200
    assert r.get("/api/audit").status_code == 403
    assert r.post("/api/settings/pause", headers=H, json={"paused": True}).status_code == 403


def test_logout_revokes_session(admin_app):
    c, _ = setup_tenant(admin_app)
    from peoplepilot.security import tokens
    stolen = c.cookies.get(tokens.COOKIE_NAMES["admin"])
    assert c.post("/api/auth/logout", headers=H).status_code == 204
    replay = TestClient(admin_app, base_url="https://admin.test")
    replay.cookies.set(tokens.COOKIE_NAMES["admin"], stolen)
    assert replay.get("/api/candidates").status_code == 401


def test_simulator_routes_absent_unless_enabled(admin_app):
    c, _ = setup_tenant(admin_app)
    assert c.get("/api/dev/sim/1").status_code == 404
    assert c.get("/api/health").json()["simulator"] is False
