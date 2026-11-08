# Reporter

A free, self-hosted HR assistant for Indian organisations. It books interviews for HR and answers
employees' routine questions from HR's own policies, so HR spends its time on the cases that need a person.

Everything runs at zero cost: SQLite, Telegram or the built-in simulator, local fonts, and an optional
local AI model through Ollama. Your data stays on your server.

## What it does

**Phase 1: Interview scheduling.** Candidates pick a slot over WhatsApp or Telegram (or the dev simulator).
Reminders go out 24 hours and 2 hours before. Anything unusual is handed to a recruiter. Interviewers see
their interviews in the employee portal and add them to their calendar.

**Phase 2: Ask HR.** Employees ask questions in English or Hinglish. Answers come from the policies HR
uploads, always with the exact policy section quoted. Leave balances come from an HR-uploaded CSV. Sensitive
topics (POSH, self-harm, legal) skip the AI and go straight to the right contacts. Anything unanswered
becomes a ticket for HR to reply to.

## Two separate portals

| App | Who | Dev URL | API port |
|---|---|---|---|
| Admin portal | HR and recruiters | http://localhost:5171 | 8001 |
| Employee portal | Employees and interviewers, mostly on phones | http://localhost:5172 | 8002 |
| Webhooks | WhatsApp and Telegram servers | none | 8003 |

The portals use different signing keys, cookies and database roles, so a session from one is useless on the
other. Admin sign-in needs a password plus an authenticator code; the employee portal uses an emailed
one-time code. Details are in [backend/SECURITY.md](backend/SECURITY.md).

## How Ask HR answers

Safest and cheapest steps come first:

1. Sensitive-topic check, before any AI is called.
2. HR's own FAQ answers, word for word.
3. Leave balance from the uploaded CSV. No model ever computes a number.
4. Optional AI (an agent with tools, or plain retrieval), and every answer is checked: citations must be
   real and every number must appear in the cited text.
5. Otherwise, the matching policy section is quoted, or the employee is offered "Ask HR".

The nine AI building blocks (tokens, embeddings, next token, context window, RAG, tool calling, agents, MCP,
evals) and where each one lives in the code are in [backend/README.md](backend/README.md#phase-2-ask-hr-employee-help-desk).

## Quick start (development)

You need Python 3.11+ and Node 20+.

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest -q
```

On Linux or macOS use `.venv/bin/python`. Next, create `backend/.env` from `backend/.env.example` with
`PP_ENV=dev`, `PP_SIMULATOR=true` and your own random secrets (the file lists the commands to generate them).
Then start the four processes, each in its own terminal:

```bash
cd backend && .venv/Scripts/uvicorn peoplepilot.apps.admin.main:app --env-file .env --port 8001
```

```bash
cd backend && .venv/Scripts/uvicorn peoplepilot.apps.portal.main:app --env-file .env --port 8002
```

```bash
cd frontend && npm install && npm run dev:admin
```

```bash
cd frontend && npm run dev:portal
```

Open http://localhost:5171, enter the `PP_SETUP_TOKEN` from your `.env`, and scan the QR code with any
authenticator app. To load sample employees, a leave policy and test questions:

```bash
cd backend && .venv/Scripts/python -m peoplepilot.dev_seed
```

In dev mode the employee portal shows the sign-in code on screen instead of emailing it. Sample employees
are `neha@acme.co.in` (employee) and `priya@acme.co.in` (interviewer).

Lost your admin password or authenticator? Run `python -m peoplepilot.reset_admin` from `backend/`.

## Optional: a free local AI model

Everything works without one. To add one, install [Ollama](https://ollama.com), then:

```bash
ollama pull qwen2.5:3b
```

```bash
ollama pull nomic-embed-text
```

Add the `PP_LLM_*` and `PP_EMBED_*` lines from [backend/README.md](backend/README.md) to `.env`, then run
**Try & check** in the admin portal to score the assistant.

## Repository layout

| Path | What is in it |
|---|---|
| `backend/` | FastAPI apps, scheduling engine, Ask HR pipeline, tests, Docker files, [SECURITY.md](backend/SECURITY.md) |
| `frontend/` | React and Vite apps: `admin`, `portal`, and `shared` (design tokens, API client) |
| `design/` | [DESIGN_RULES.md](design/DESIGN_RULES.md), the vendored UX check kit, and a screenshot harness |
| `council/`, `reports/`, `research_notes/` | Early research: security, engineering, strategy and HR-buyer reviews |

## Design checks

UI changes are checked against [design/DESIGN_RULES.md](design/DESIGN_RULES.md) using the
[ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) kit (MIT, vendored in `design/kit`):
accessibility, overflow at phone widths, tap targets and "AI-slop" tells. Run instructions are at the end of
that file.

## Status

Tested: 81 backend tests on SQLite, five of five Ask HR checks, the employee and admin flows in a browser, and
the design checks on eight screens.

Not tested yet:
- A real AI model (the AI paths ran against a scripted fake).
- Postgres, row-level security and `docker compose`.
- The live WhatsApp and Telegram APIs.

Not built yet: emailed sign-in codes in production (SMTP is wired but untried), hosting, backups, versioned
database migrations, CI, request forms, Telegram Ask HR, and calendar sync.

## Security

Never commit `.env`. It holds the signing keys and the data encryption key; losing `PP_DATA_KEY` means losing
the encrypted data, so back it up offline. Report security problems privately to the repository owner.

## Licence

No licence has been chosen yet, so all rights are reserved by default. Add a `LICENSE` file before sharing it
for reuse. The vendored `design/kit` is MIT, see `design/kit/LICENSE`.
