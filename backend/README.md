# Reporter: backend (Phase 1 interview scheduling + Phase 2 Ask HR)

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
tests/              64 tests: portal separation, tenant isolation, MFA, lockout, OTP, booking flow,
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

## Phase 2: Ask HR (employee help desk)

Employees ask HR questions in the employee portal (English or Hinglish). HR manages what it knows on the admin portal under **Answers & policies** and replies to anything it can't answer under **Help desk**.

How a question is answered, safest and cheapest first ([`assist/answer.py`](peoplepilot/assist/answer.py)):
1. **Sensitive-topic gate:** POSH, self-harm and legal language stops the bot before any AI call and shows the Internal Committee / HR contacts plus free helplines. Nothing typed there is stored.
2. **HR's FAQ answers** win, word for word.
3. **Leave balance** is read from the CSV HR uploads. No model ever computes a number.
4. **AI (optional)**: an agent with tools, or plain RAG, and every answer is checked (below).
5. **No AI, or the check fails**: the matching policy sections are quoted verbatim, or the employee is offered "Ask HR".

### The 9 ideas behind it, and where each lives

| # | Idea | In Reporter | Code |
|---|---|---|---|
| 1 | Tokens | Context is budgeted in tokens before each call (`PP_LLM_CONTEXT_TOKENS`); real token usage per question is recorded and shown on the Help desk page. | `assist/llm.py` `approx_tokens`, `AskEvent.tokens_in/out` |
| 2 | Embeddings | Optional meaning-based search: clause vectors from a free local model, fused with keyword search. Off = keyword search only. | `assist/embed.py`, `retrieve.search` |
| 3 | Next token | `temperature=0` (always the most likely next token, so the same question gets the same answer), `max_tokens` cap, and a fixed JSON reply shape. | `assist/llm.py` `chat` |
| 4 | Context window | Only the best policy sections are packed in, labelled `[C1]…`, and trimmed to the budget. | `llm.pack_context` |
| 5 | RAG | Retrieval is filtered by organisation, active version, effective date and the employee's location/grade/type, then ranked with BM25 (+ embeddings). Answers must cite `[C#]` labels they were shown; every number must appear in the cited text; PII is redacted from the output. | `assist/retrieve.py`, `answer.check_answer` |
| 6 | Tool calling | Four allow-listed tools: `search_policies`, `get_my_leave_balance`, `list_my_hr_requests`, `draft_hr_ticket`. They're bound to the signed-in employee, so the model can't pass someone else's id. | `answer._Toolbox` |
| 7 | Agents | A bounded loop (max `PP_LLM_MAX_STEPS`, ≤3 tool calls per step; tools removed on the last step). It can't change anything: the only "write" is a draft the employee reviews and sends. | `answer._agent` |
| 8 | MCP | Optional read-only MCP server for HR's own AI app (Claude Desktop etc.): list/search policies, preview answers, FAQs, org-level stats, run checks. No employee personal data. Runs over stdio, nothing listens on the network. | `peoplepilot/mcp_server.py` |
| 9 | Evals | HR writes test questions with the expected outcome. **Run checks** scores the assistant; sensitive-topic routing must be 100%. Also as a CLI for CI. | `assist/evals.py` |

### Turning on the free AI pieces (optional)

Everything works without a model. To add one for free, install [Ollama](https://ollama.com) and pull a small model that supports tool calling, plus an embedding model:

```bash
ollama pull qwen2.5:3b
```

```bash
ollama pull nomic-embed-text
```

Then add to `.env`:

```
PP_LLM_BASE_URL=http://localhost:11434/v1
PP_LLM_MODEL=qwen2.5:3b
PP_EMBED_BASE_URL=http://localhost:11434/v1
PP_EMBED_MODEL=nomic-embed-text
```

Re-click **Make live** on each policy after turning on embeddings so its sections get vectors. If a model has no tool calling, set `PP_LLM_TOOLS=false` to use plain RAG.

### Sample data, checks and MCP

```bash
.venv/Scripts/python -m peoplepilot.dev_seed
```

loads `samples/` (employees, a Leave Policy, leave balances, an FAQ answer, contacts and five checks) into organisation 1. Dev only.

```bash
.venv/Scripts/python -m peoplepilot.assist.evals --tenant 1
```

runs the checks and exits non-zero if any fail.

The MCP server needs its own environment (the `mcp` package needs newer web libraries than the portals):

```bash
python -m venv .venv-mcp
```

```bash
.venv-mcp/Scripts/pip install -r requirements-mcp.txt
```

Setup for Claude Desktop is in the docstring of [`mcp_server.py`](peoplepilot/mcp_server.py).

## Migrations and backups

`python -m peoplepilot.migrate` runs Alembic (`alembic/versions`). The baseline creates any missing table; for later schema changes add a numbered file with `alembic revision -m "what changed"` (run from `backend/`). An existing Postgres database from before Phase 2 still needs its new columns added by hand once.

```bash
.venv/Scripts/python -m peoplepilot.backup
```

writes a consistent copy of the database to `./backups` (SQLite copy, or `pg_dump` on Postgres). Keep `PP_DATA_KEY` safe offline too, since backups are unreadable without it.

## Status / not yet done
- ✅ Tested here: everything in `tests/` on SQLite (64 passing, including the help-desk safety, isolation, grounding, agent and eval tests), the scheduling flow and the employee Ask HR flow in the browser, and the MCP server's tools.
- ⚠️ The AI paths are tested against a scripted fake model, not a real one (no Ollama on the dev machine). Run your checks after connecting a model.
- ⚠️ Phase 2 added columns to `tenants`, `employees` and new tables. Local SQLite files are upgraded automatically; an existing Postgres database needs those columns added by hand (fresh installs are fine).
- 💸 Everything runs for free on your own laptop: SQLite, Telegram or the built-in simulator, and no AI needed (or a free local Ollama model).
- ⚠️ **Not run yet:** the Postgres path (`migrate.py`, row-level security, per-role grants) and `docker compose` (no Docker on the dev machine). Test on a Postgres box before a pilot.
- ⚠️ WhatsApp and Telegram senders are written to the public API docs but haven't been exercised against the live services.
- ⏭️ Next: Google/Microsoft calendar free/busy + invites (today availability comes only from bookings in Reporter, and interviewers add the `.ics`), and a free GitHub Actions CI workflow.
