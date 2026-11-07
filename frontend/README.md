# Reporter front end

Two **separate** apps, one per portal, sharing only design tokens and a tiny API client:

| App | For | Dev URL | Talks only to |
|---|---|---|---|
| `admin/` | HR / recruiters | http://localhost:5171 | admin API on :8001 |
| `portal/` | Employees / interviewers | http://localhost:5172 | employee API on :8002 |
| `shared/` | tokens.css, api client, time helpers, error boundary | — | — |

Everything is free and runs on your laptop: React, Vite, fonts bundled locally (no Google Fonts calls).

## Run it (4 terminals)

Backend first: create `backend/.env` from `backend/.env.example` with `PP_ENV=dev` and `PP_SIMULATOR=true`.

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

Then open http://localhost:5171, enter the `PP_SETUP_TOKEN` from `.env`, and scan the QR code with any free authenticator app.

## Simulator (no WhatsApp/Telegram needed)
With `PP_SIMULATOR=true`, no real messages are sent. Open any candidate on the board and use **Candidate's phone (simulator)** to tap slot buttons or type replies like "3 baje ke baad ho sakta hai?". In dev the employee portal also shows the sign-in code on screen instead of emailing it.

## Screens
- **Admin:** setup → two-factor → scheduling board (week slot rail + candidate table + candidate drawer with chat, takeover, cancel, outcome) · interview rounds (create, CSV upload) · interviewers & team · settings (status, emergency stop, Telegram, WhatsApp) · activity log (owners).
- **Employee portal (mobile-first):** sign in with an email code → my interviews (ticket cards, add to calendar, mark attended / no-show) → my data.
