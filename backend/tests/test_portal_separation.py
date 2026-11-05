"""The admin portal and the employee portal must never accept each other's sessions."""
from fastapi.testclient import TestClient

from peoplepilot.apps.portal.main import _dev_outbox
from peoplepilot.security import tokens

from .conftest import H, make_round, setup_tenant


def _portal_login(portal_app, email):
    p = TestClient(portal_app, base_url="https://me.test")
    _dev_outbox.clear()
    assert p.post("/api/auth/code", headers=H, json={"email": email}).status_code == 200
    code = _dev_outbox[-1][1]
    assert p.post("/api/auth/verify", headers=H, json={"email": email, "code": code}).status_code == 204
    return p


def test_cookie_names_differ():
    assert tokens.COOKIE_NAMES["admin"] != tokens.COOKIE_NAMES["portal"]
    assert all(n.startswith("__Host-") for n in tokens.COOKIE_NAMES.values())


def test_portal_token_rejected_by_admin(admin_app, portal_app):
    admin, _ = setup_tenant(admin_app)
    make_round(admin)
    p = _portal_login(portal_app, "iv@acme.co.in")
    portal_token = p.cookies.get(tokens.COOKIE_NAMES["portal"])
    assert portal_token

    attacker = TestClient(admin_app, base_url="https://admin.test")
    # Same token value placed in the admin cookie name: wrong key + wrong audience.
    attacker.cookies.set(tokens.COOKIE_NAMES["admin"], portal_token)
    assert attacker.get("/api/candidates").status_code == 401
    assert attacker.get("/api/auth/me").status_code == 401


def test_admin_token_rejected_by_portal(admin_app, portal_app):
    admin, _ = setup_tenant(admin_app)
    admin_token = admin.cookies.get(tokens.COOKIE_NAMES["admin"])
    p = TestClient(portal_app, base_url="https://me.test")
    p.cookies.set(tokens.COOKIE_NAMES["portal"], admin_token)
    assert p.get("/api/me").status_code == 401
    assert p.get("/api/me/interviews").status_code == 401


def test_portal_has_no_admin_routes(portal_app):
    p = TestClient(portal_app, base_url="https://me.test")
    for path in ("/api/candidates", "/api/rounds", "/api/audit", "/api/kpis", "/api/setup"):
        assert p.get(path).status_code in (404, 405)


def test_admin_portal_blocks_outside_network(admin_app):
    outsider = TestClient(admin_app, base_url="https://admin.test", client=("203.0.113.9", 5000))
    assert outsider.post("/api/auth/login", headers=H, json={"email": "x@y.co.in", "password": "p"}).status_code == 404
    insider = TestClient(admin_app, base_url="https://admin.test", client=("10.1.2.3", 5000))
    assert insider.post("/api/auth/login", headers=H, json={"email": "x@y.co.in", "password": "p"}).status_code == 401


def test_portal_is_public(portal_app):
    outsider = TestClient(portal_app, base_url="https://me.test", client=("203.0.113.9", 5000))
    assert outsider.post("/api/auth/code", headers=H, json={"email": "nobody@x.co.in"}).status_code == 200


def test_session_revoked_when_employee_deactivated(admin_app, portal_app):
    admin, _ = setup_tenant(admin_app)
    _, emp = make_round(admin)
    p = _portal_login(portal_app, "iv@acme.co.in")
    assert p.get("/api/me").status_code == 200
    assert admin.post(f"/api/employees/{emp['id']}/deactivate", headers=H).status_code == 204
    assert p.get("/api/me").status_code == 401
