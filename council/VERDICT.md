# Council verdict — PeoplePilot AI (free & open-source edition)

Council seats: 1 Security red-team · 2 AI systems engineer · 3 Skeptical founder · 4 HR Head (buyer/user)
Full critiques: `1_security.md`, `2_engineering.md`, `3_strategy.md`, `4_hr_buyer.md`. Chair synthesis below.

---

## 1. Where the council agreed (unanimous or 3–1)

1. **The plan is too big.** Every seat said the 10-week, 11-component MVP is a 6–9 person-month build. Cut ~80%.
2. **Policy Q&A alone is not the product.** It is table stakes, and greytHR NAVOS, Kredily KAI and Zimyo already give it away free inside the HRMS. Value comes from **getting work done**: scheduling, regularisation, letters, cab/shift changes.
3. **Free + open-source + self-hosted is the real advantage.** The company runs it on its own server with its own keys, so employee data never reaches you. This removes most of the compliance burden (DPA, ISO, residency) that the HR buyer said would otherwise kill the deal. **No free hosted multi-tenant service**: the founder never pays for other people's usage. The company brings its own LLM key and its own WhatsApp number.
4. **A deterministic button state machine owns the conversation**, which is your brother's "bank-style chatbot". The LLM only classifies free text and explains policy. It can never trigger a write. Writes need a button tap on a server-rendered diff.
5. **On a free budget, use retrieval by default, not "stuff the whole handbook".** Clause-level chunks, BM25 + BGE-M3 hybrid, hard filters on version and scope, cite or abstain. Full-handbook prompting only when a company brings a paid key.
6. **Numbers come from code, never the LLM.** Leave clubbing, carry-forward, buyout and overtime go in a rules engine with property tests.
7. **Drop the productivity tracker.** Shift workers will call it surveillance.

## 2. The disagreement and the chair's ruling

| | Seat 3 (founder) | Seat 4 (HR Head) |
|---|---|---|
| First workflow | Interview scheduling + no-show reduction on WhatsApp. No HRMS needed, no policy liability, targets placement cells and staffing agencies | Attendance regularisation + letters written into Keka. "Interview scheduling is nice-to-have, TA uses Keka Hire" |

**Ruling: start with interview scheduling, and use Week 1 to unblock Keka.**
- Your brother, the only *real* HR voice so far, named interview scheduling and coordination as his **#1 time sink** and as automatable. Seat 4 is a hypothetical persona.
- It needs no HRMS connector. Keka's write API is still **unconfirmed**, so building on it first is the biggest technical risk.
- In Week 1, email Keka about API write access (leave and attendance regularisation). If confirmed, **regularisation + letters becomes Phase 2's hero**, as Seat 4 demands. If not, pivot Phase 2 to greytHR/Zoho, which have documented APIs.

## 3. Security: re-ordered priorities (Seat 1, adopted in full)

The year-one breach won't be a clever prompt. It will be **a phone number that now belongs to someone else**, or **an org-wide HRMS token behind a buggy tool**. Identity and connector blast radius go above the 8 nets.

### Revised safety nets (v2)

| # | Net | Day-one implementation (all free/OSS) |
|---|---|---|
| 0 | **Identity binding** *(new, top priority)* | WhatsApp/Telegram ID bound to the employee via magic-link or email OTP. Re-verify every 60–90 days. Step-up PIN before payslip, PF or bank data. Payslips as single-use 10-minute links, never attachments. Access revoked automatically on exit sync |
| 1 | Access control & isolation | Postgres RLS on `tenant_id`. **Document-level ACLs** on policies (filters ≠ access control). Per-tenant encrypted connector secrets. MFA for HR admins |
| 2 | Sensitive-topic routing *(moved up)* | Local keyword/regex + small classifier **before any LLM call and before any trace is written**. Covers POSH, self-harm and legal only; "I have fever" must NOT trigger it |
| 3 | Scoped tools / confused-deputy isolation | Narrow typed tools that ignore the model's `employee_id`. Employee text never reaches a higher-privileged HR/manager agent. AI drafts are treated as untrusted |
| 4 | PII redaction | Presidio + custom UAN/IFSC recognisers (fix: PAN is 10 chars) |
| 5 | Human approval | Single-use nonce bound to a diff hash, with expiry. Approver re-checked server-side (anyone in a Slack channel can click a button) |
| 6 | Output DLP | Block names, IDs and amounts not in this turn's tool results. Strip URLs/markdown. Allow-list deep-link domains |
| 7 | Grounding *(quality net)* | Cite `[clause_id]`, validated against retrieved set; regenerate once, then abstain → HR |
| 8 | Audit vs traces | Audit = metadata only, kept ≥1 year (DPDP Rule 6). Content traces ≤30 days. **No real employee text in golden sets/CI** |
| — | Telemetry only | Prompt Guard 2 (22M) — weak on Hinglish, so it's a signal, not a net |

### Analytics changes
- Team leave patterns and per-team query topics move **green → amber**. Leave type in a 4-person team reveals maternity or medical leave.
- Show "away" on calendars, never the leave type.
- **Under ~150 employees: no amber analytics at all.** Ship org-level operational metrics only.
- Red stays red: no individual attrition or burnout scores, no emotion inference.

## 4. Revised MVP — 10 weeks, one developer, ₹0 running cost

**Phase 0 (Week 1) — validate + unblock**
- 20 conversations with HR, TA and placement-cell people: does scheduling/no-shows rank top-3?
- Ask Keka about write access.
- **Start Meta WhatsApp business verification now**: it takes 2–6 weeks.

**Phase 1 (Weeks 2–7) — Interview Scheduling Agent (open source, `docker compose up`)**
- Recruiter uploads a candidate CSV and links Google/M365 calendar.
- WhatsApp utility template → 3 slot buttons → booked + calendar invite.
- Reminders at T-24h and T-2h with *Reschedule* / *Can't make it* buttons.
- Status board for the recruiter. LLM only classifies free-text replies; anything unclear goes to the recruiter.
- Day-one safety: tenant isolation, nets 0–2 & 8, PII-redacted logs, append-only audit table.
- Telegram fallback while Meta verification is pending.

**Phase 1 pilot (Weeks 8–10) at your brother's company + 1 placement cell**
- Baseline: 2 weeks of manual scheduling.
- Success: ≥60% interviews booked with zero recruiter touch · no-shows ↓ ≥25% · they keep using it without you.

**Phase 2 — Employee assistant on the same core**
- Hero flows: **attendance regularisation + letter requests** written to Keka (or greytHR).
- Then leave balance/apply, payroll/Form 16/F&F FAQ.
- Policy Q&A with retrieval + citations + an **FAQ override editor**.
- Channels: Teams for office staff, WhatsApp for shift staff (company-funded).

**Phase 3**
- Cab/roster and shift swaps, broadcasts, location/process holiday calendars, onboarding checklist.
- Amber analytics only for companies ≥150 employees.

### Kill criteria (adoption, not revenue)
| Week | Pivot if… |
|---|---|
| 3 | Fewer than 5 of 20 people rank scheduling top-3, or fewer than 3 commit to a pilot |
| 6 | An adopter can't reach their first scheduled interview in under 1 day of their own effort (Meta verification excluded) |
| 8 | Zero-touch scheduling below 40%, or recruiters route around the bot |
| 12 | Fewer than 3 organisations still active 4 weeks after setup without help, or none from outside your network |

GitHub stars don't count.

## 5. Zero-cost stack (Seat 2)

| Layer | Choice |
|---|---|
| Backend | FastAPI + Pydantic AI (multi-provider), or a ~200-line tool loop. **Not LangGraph** for this scope |
| Conversation | YAML-defined FSM flows; LLM only for intent + policy QA |
| DB | Postgres + pgvector (self-hosted in compose; Neon/Supabase free for demo) |
| Embeddings | BGE-M3 local (Hindi-capable) |
| LLM | Company's own key (Claude Haiku/Sonnet, etc.) or local Qwen2.5-7B/Llama-3.1-8B via Ollama (10–25 s answers). **Gemini free tier: dev/evals only**, because it may train on data |
| Jobs | Postgres `SKIP LOCKED` queue |
| Hosting (your demo) | Oracle Always Free ARM (no cold starts). Avoid Render free: cold starts break webhooks |
| Evals | pytest + Hypothesis (rules 100%), VCR connector contracts, YAML golden set, promptfoo red-team, GitHub Actions |
| Funding your own costs | AWS Activate / Google / Microsoft for Startups credits, GitHub Sponsors, FOSS United grants, college incubator |

Repo layout and tables: see `2_engineering.md` §5.

## 6. Screen changes (from Seat 4)
- **Cut/defer:** workflow builder (ship preset toggles), live safety centre (make it a downloadable trust pack), landing page, manager inbox (approve inside Keka or via a Teams/WhatsApp card), left-side chat history on mobile.
- **Add:** identity/sync health (unmapped numbers, opt-in %, last sync), recruiter scheduling board (Phase 1), letter request queue, FAQ override editor, broadcast composer, HR workload view.
- **Replace** "hours saved (estimate)" with tickets deflected × minutes-per-ticket that HR configures.

## 7. Two separate portals + data-leak controls (added at owner's request)

The **Admin portal** (HR/recruiters) and the **Employee portal** (employees/interviewers) are separate applications, not one app with a role toggle.

| Separation layer | Admin portal | Employee portal |
|---|---|---|
| Process | `peoplepilot.apps.admin.main:app` (own uvicorn process, port 8001) | `peoplepilot.apps.portal.main:app` (own process, port 8002) |
| Origin / domain | `admin.<company>` (should be internal network / VPN only) | `me.<company>` |
| Network | IP allow-list middleware (`ADMIN_ALLOWED_CIDRS`, default private ranges only) | Public |
| Login | Email + password (Argon2) + **mandatory TOTP MFA** | Email one-time code (no passwords to leak) |
| Session token | JWT, `aud=admin`, signed with `ADMIN_JWT_KEY`, cookie `__Host-pp_admin` | JWT, `aud=portal`, signed with **a different key** `PORTAL_JWT_KEY`, cookie `__Host-pp_portal` |
| Result | An employee token is cryptographically invalid on the admin API, and vice versa | Employee identity always comes from the session, never from the request |
| DB role (Postgres) | `pp_admin` | `pp_portal`, which only has SELECT on minimal views (no phone/email of others) |

The third process is the **public webhook receiver** (`apps/webhooks`, port 8003). It has no sessions, only signature verification (WhatsApp `X-Hub-Signature-256`, Telegram secret token).

**Data-leak controls (all in Phase 1 code):**
1. **Explicit response schemas per portal.** No ORM objects are ever serialised, and portal schemas never contain another person's phone or email.
2. **Tenant-scoped data access.** Every query goes through `scoped()`, and Postgres RLS is the second wall (`migrations/postgres_rls.sql`).
3. **Encryption at rest** (Fernet) for candidate phone numbers and channel tokens. Lookups use an HMAC hash, so the database alone reveals no phone numbers.
4. **Data minimisation.** Admin board shows masked phones (`+91•••••43210`). Interviewers see only the candidate's first name, role and time.
5. **Security headers** on every response: strict CSP, `X-Frame-Options: DENY`, HSTS, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`. CORS is locked to each portal's own origin.
6. **CSRF.** SameSite=Strict cookies, plus a required custom header on every write.
7. **No user enumeration.** Uniform login responses. Rate limits and lockouts on login and OTP.
8. **Log redaction filter.** Phones, emails, PAN, Aadhaar and UAN are masked before any log line is written. Generic errors with no stack traces leave the server.
9. **Single-use, expiring, candidate-bound button nonces.** Replayed or forged buttons do nothing.
10. **Metadata-only audit log** (1 year). Message logs are purged after 30 days. Kill switch pauses all outbound messages.
11. **First-run setup needs a `SETUP_TOKEN`** from the server's env, so nobody can claim a fresh install.

## 8. The one-line verdict
> Build an **open-source, self-hosted, button-first HR agent**. Prove it on **interview scheduling** at your brother's company, nail **identity binding** before anything else, and only then grow into **Keka regularisation + letters**. Policy Q&A comes along as a feature, not the pitch.
