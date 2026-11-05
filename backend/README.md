# PeoplePilot AI: backend (Phase 1: Interview Scheduling Agent)

A free, open-source, self-hosted agent that books interviews over **WhatsApp** (or **Telegram**), sends reminders, and hands anything unusual to a recruiter. Your data stays on your server.

## Architecture: three separate apps

| Process | Who uses it | Port | Exposure | Login |
|---|---|---|---|---|
| `peoplepilot.apps.admin.main:app` | HR / recruiters (**Admin portal**) | 8001 | Office network / VPN only (IP allow-list) | Password + mandatory TOTP MFA |
| `peoplepilot.apps.portal.main:app` | Employees / interviewers (**Employee portal**) | 8002 | Public, via HTTPS proxy | One-time email code |
| `peoplepilot.apps.webhooks.main:app` | WhatsApp / Telegram servers | 8003 | Public, via HTTPS proxy | Platform signature / secret |
| `python -m peoplepilot.worker` | — | — | none | — |

The two portals use **different signing keys, audiences, cookies and database roles**, so a session from one is useless on the other. See [SECURITY.md](SECURITY.md).

```
peoplepilot/
  apps/admin/       admin portal API (rounds, CSV upload, board, takeover, settings, audit)
  apps/portal/      employee portal API (my interviews, .ics, outcome)
  apps/webhooks/    WhatsApp + Telegram receivers
  apps/common.py    security headers, CSRF, CORS, IP allow-list, safe errors
  scheduling/       slots.py (free-slot finder), intent.py (rules + optional LLM),
                    engine.py (button-first state machine), ics.py
  channels/         whatsapp.py, telegram.py, base.py (fake channel for dev/tests)
  security/         crypto (Fernet/Argon2/HMAC), tokens (JWT realms), nonce (single-use buttons),
                    redact (PII), ratelimit
  worker.py         reminders (T-24h, T-2h) + retention purge
  migrate.py        tables + Postgres roles + row-level security
migrations/postgres_rls.sql
tests/              40 tests: portal separation, tenant isolation, MFA, lockout, OTP, booking flow,
                    button replay, webhook signatures, redaction, data minimisation
```

## Run the tests (no Docker needed)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt     # Windows (use .venv/bin/python on Linux/macOS)
.venv/Scripts/python -m pytest -q
```

## Run locally (dev, SQLite)

Create `.env` with dev secrets (see `.env.example`; `PP_ENV=dev`, leave `PP_DATABASE_URL` unset for SQLite), then start each app in its own terminal:

```bash
.venv/Scripts/uvicorn peoplepilot.apps.admin.main:app --port 8001
```

```bash
.venv/Scripts/uvicorn peoplepilot.apps.portal.main:app --port 8002
```

```bash
.venv/Scripts/uvicorn peoplepilot.apps.webhooks.main:app --port 8003
```

```bash
.venv/Scripts/python -m peoplepilot.worker
```

Every write request must send the header `x-pp-request: 1` (CSRF protection). Session cookies are `Secure`, so browsers send them only over HTTPS (or `localhost`).

## First-run (admin portal)
1. `POST /api/setup` with `PP_SETUP_TOKEN`, org name and owner email/password.
2. `POST /api/auth/mfa/setup` → scan the `otpauth://` URI in an authenticator app → `POST /api/auth/mfa/confirm`.
3. `PUT /api/settings/channel` with WhatsApp (phone_number_id, access_token, app_secret, verify_token) or Telegram (bot_token, bot_username). For Telegram, call `setWebhook` with the returned path and `secret_token`.
4. `POST /api/employees` (interviewers) → `POST /api/rounds` → `POST /api/rounds/{id}/candidates/csv` (columns `name, phone, consent`, optional `email, channel`).
5. `POST /api/candidates/{id}/invite`. WhatsApp sends the approved `interview_invite` template. Telegram returns a `t.me` link to share.

### WhatsApp template
Create a **Utility** template named `interview_invite` with body
`Hi {{1}}, you're shortlisted for {{2}} at {{3}}. Tap below to pick an interview slot.`
and one **quick-reply** button `See slots`. Start Meta business verification early: it takes 2–6 weeks.

## Production (Docker)
```bash
cp .env.example .env
```

Fill every secret, then:

```bash
docker compose up -d
```

`migrate` runs first as the DB owner and creates the per-process roles (`pp_admin`, `pp_portal`, `pp_bot`, `pp_worker`) and RLS policies. Put Caddy or nginx with HTTPS in front of `portal` (8002) and `webhooks` (8003). Keep `admin` (8001) on localhost / VPN.

## Status / not yet done
- ✅ Tested here: everything in `tests/` on SQLite (41 passing), and the full flow clicked through in the browser with the front end (`../frontend`) and the simulator.
- 💸 Everything runs for free on your own laptop: SQLite, Telegram or the built-in simulator, and no AI needed (or a free local Ollama model).
- ⚠️ **Not run yet:** the Postgres path (`migrate.py`, row-level security, per-role grants) and `docker compose` (no Docker on the dev machine). Test on a Postgres box before a pilot.
- ⚠️ WhatsApp and Telegram senders are written to the public API docs but haven't been exercised against the live services.
- ⏭️ Next: Google/Microsoft calendar free/busy + invites (today availability comes only from bookings in PeoplePilot, and interviewers add the `.ics`), and a free GitHub Actions CI workflow.
