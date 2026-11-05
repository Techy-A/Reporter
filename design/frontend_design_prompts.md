# PeoplePilot AI: front-end design prompts (v2, after council review)

Paste these into **Google Stitch** (fast screen exploration) or **Lovable** (working React + Tailwind + shadcn app, export to GitHub). You can also use them as a brief in **Figma** for the design system.
Flow: Stitch → pick a direction → Figma tokens/components → Lovable → wire to the FastAPI backend.

**What changed from v1 (per `council/VERDICT.md`):**
- **Phase 1 is now the Interview Scheduling Agent**, so its screens come first.
- The product is **free, open-source and self-hosted**, so screens include a setup wizard and say "your data stays on your server". No pricing.
- **Cut:** workflow builder, live safety centre, marketing landing page, manager inbox, productivity tracker, left-side chat history on mobile, "hours saved (estimate)".
- **Added:** setup wizard, recruiter scheduling board, identity & sync health, FAQ override editor, letter queue, broadcast composer, HR workload view, downloadable trust pack.
- The **sensitive-topic screen fires only for POSH, self-harm and legal topics**, never for "I have fever".

**Two separate portals (design them as two distinct apps):**
- **Admin portal** (`admin.<company>`): HR and recruiters. Screens 1–3, 5–7, 11–17. Dense desktop layout, indigo header, "Admin" badge in the top bar, MFA code step on login.
- **Employee portal** (`me.<company>`): employees and interviewers. "My interviews" (Phase 1), plus screens 8, 9, 18 (Phase 2). Mobile-first, lighter header, sign-in with a one-time email code (no password).
- They share the colour tokens but **never link to each other**, have separate login pages, and the employee portal never shows anyone else's phone or email.

> **Employee portal: Phase 1 "My interviews"** — A mobile-first page for an interviewer. Sign-in screen: email field → "We've sent a 6-digit code if this email is registered" → code field. Home: list of my upcoming interviews (candidate first name only, role, date/time, in-person address or video link, "Add to my calendar (.ics)"). After the slot: buttons "Attended" / "No-show". No candidate phone numbers or emails anywhere. Footer: "My data" link.

If you already have a design, prepend: *"Match the attached design's colours, typography and spacing."* and attach screenshots.

---

## 0. Global style prompt (paste first, in every tool)

> Design a web app called **PeoplePilot AI**: a free, open-source, self-hosted HR operations assistant for Indian companies (50–500 employees), staffing agencies and college placement cells. Tone: calm, trustworthy, practical. No AI hype, no robots, no sparkles. Light and dark mode.
>
> **Colour:** deep indigo primary, warm saffron accent used only for primary actions, neutral greys, green/amber/red only for status.
>
> **Type and layout:** Inter for UI, a humanist serif for page titles. 8px grid, 12px radius cards, subtle shadows. Dense but readable tables for HR and recruiter users.
>
> **Persistent trust cues:**
> - A small footer badge: "Self-hosted · your data stays on your server".
> - Every AI answer shows a **source chip** (policy · clause · version date).
> - Every action is a **confirmation card** showing the exact change, with Confirm / Edit / Cancel. The AI never acts silently.
>
> **Conversations are button-first** (like a bank chatbot): chips and buttons drive flows, and free text is always allowed. WCAG AA, responsive to 375px, English labels with Hinglish-friendly microcopy.

---

# Phase 1: Interview Scheduling Agent (build first)

## 1. First-run setup wizard (self-hosted)

> A 5-step setup wizard shown after `docker compose up` on first login. Progress stepper at the top.
> 1. **Organisation:** name, type (Company / Staffing agency / Placement cell), timezone (default IST).
> 2. **Admin account:** email + mandatory MFA setup (QR code for an authenticator app).
> 3. **Calendar:** "Connect Google Workspace" / "Connect Microsoft 365" buttons, with a list of exact permissions requested (read free/busy, create events).
> 4. **Messaging channel:** WhatsApp Business (fields for Phone Number ID, WABA ID and access token, plus a status line "Meta business verification: Pending / Approved" and a help link "Verification takes 2–6 weeks — use Telegram meanwhile"), or Telegram bot token.
> 5. **AI model:** "Bring your own key" (provider dropdown: Anthropic, OpenAI, Groq, OpenRouter) or "Local model (Ollama URL)". Note: "Only used to understand free-text replies. Buttons work without AI."
>
> End screen: a checklist with green ticks and a "Send test message to my phone" button.

## 2. Recruiter scheduling board (home)

> The recruiter's main screen.
> - **Top bar:** "Upload candidates (CSV)" button, a "New interview round" button, and a filter by role/round/interviewer.
> - **KPI strip:** Invited · Booked · Booked with zero recruiter touch (%) · Reminders sent · No-shows this week · Needs attention.
> - **Main table, one row per candidate:** name, role, round, interviewer, status pill (Invited, Booked, Rescheduled, Confirmed, Can't make it, No-show, Needs recruiter), slot date/time, channel icon (WhatsApp/Telegram), last message, and actions (View chat, Reschedule manually, Mark attended).
> - **"Needs attention" right panel:** candidates whose free-text reply the bot couldn't handle, with the message shown and quick replies.
>
> No AI-generated scores of candidates anywhere.

## 3. New interview round + CSV upload

> A modal or page to create a round: role, interviewer(s) (searchable, shows calendar connected ✓), duration, mode (in-person address / video link auto-created), slot window (date range + daily hours), buffer between interviews, and max slots offered (default 3).
> CSV upload step: drag-and-drop, column mapper (name, phone, email, role), validation preview with errors highlighted (invalid Indian mobile numbers, duplicates), and a WhatsApp opt-in consent checkbox per row with explanatory text.
> Final step: preview of the WhatsApp invite template exactly as the candidate will see it.

## 4. Candidate WhatsApp conversation (mobile mockup)

> A phone mockup of the candidate's WhatsApp chat with "PeoplePilot · Acme Corp Hiring".
> 1. Invite message: "Hi Riya, you're shortlisted for Customer Support Associate at Acme. Pick an interview slot:" with **3 reply buttons** (Tue 12 Nov, 11:00 / Tue 12 Nov, 15:00 / Wed 13 Nov, 10:30) and a "None of these work" option.
> 2. Confirmation: date, time, address/map link or video link, interviewer name, and "Add to calendar".
> 3. Reminder at T-24h with buttons **Confirm · Reschedule · Can't make it**.
> 4. Reminder at T-2h with directions.
> 5. A free-text example: candidate types "bhaiya 2 baje ke baad ho sakta hai?". The bot replies with new slots after 2 pm as buttons.
> 6. Fallback: "I've passed this to the recruiter, they'll reply here."
>
> Also show the Telegram variant side by side.

## 5. Candidate conversation detail (recruiter view)

> Drawer that opens from the board: the full chat transcript on the left, with bot messages labelled and any AI-interpreted intent shown as a small grey tag. On the right: candidate details, booking history timeline, and buttons to take over the chat ("Reply as recruiter" pauses the bot for this candidate) and to cancel or reschedule. Shows "Personal data in logs is redacted after 30 days".

## 6. Identity & sync health

> Admin screen with health cards: Calendar connection (last sync, errors), Messaging channel (status, messages used this month vs 1,000 free service messages, template approval status), AI model (reachable ✓, avg response time), Database backups (last backup). Table of problems to fix: invalid numbers, candidates who never opted in, failed messages with reasons. A "Run diagnostics" button.

## 7. Audit log + trust pack

> Simple, searchable audit table: time, actor (user/bot/system), action, record, result. Filters by date and actor. Metadata only, no message content.
> Top-right button: **"Download trust pack (PDF)"**. It contains the security overview, data flows, where data is stored (your server), retention settings and the open-source licence. No live "attacks blocked" counters.
> Settings section: message log retention (default 30 days), audit retention (default 1 year), and a kill switch "Pause all automated messages".

---

# Phase 2: Employee assistant (same core, design now, build later)

## 8. Employee chat (mobile-first, WhatsApp/Teams/web)

> Mobile-first employee chat, with no conversation-history sidebar on mobile.
>
> **Quick-action chips above the input:** Fix missed punch · Request a letter · Leave balance · Apply leave · Payslip · Form 16 / tax · F&F status · Talk to HR.
>
> **Example 1:** "Fix missed punch" → date picker (yesterday pre-selected) → roster shows "Night shift 21:00–06:00" → choose reason (Biometric failed / Cab late / Forgot) → **confirmation card** "Regularisation request for 3 Nov, 21:00–06:00, reason: Cab late → goes to your manager in Keka" → Confirm/Edit/Cancel → "Submitted ✓ Track in Keka".
>
> **Example 2:** "Can I club sick and casual leave?" → answer with source chip "Leave Policy §4.2 · v2026-01" and a "Was this helpful?" thumbs row.
>
> **Example 3:** "Payslip" → "Enter your 4-digit PIN" step-up → "Here's a secure link, valid for 10 minutes" (never a PDF attachment).
>
> A "Talk to HR" button is always visible. Privacy line: "I only see your own records."

## 9. Sensitive-topic handoff (POSH / self-harm / legal only)

> When the system detects harassment/POSH, self-harm or legal-threat language, the chat switches to a calm fixed screen: no AI-generated text, a short supportive message, Internal Committee contact details, a "Raise a confidential complaint" link to a separate secure form, and helpline numbers. Lock icon, muted colours, previous messages hidden. Text: "This conversation is not stored in AI logs."
> **Counter-example:** "I have fever, need sick leave" must go to the normal leave flow. Show it as a note on the frame.

## 10. Approval card (replaces the manager inbox)

> Design an approval card for Microsoft Teams (Adaptive Card style) and a WhatsApp variant. Card content: employee name, request type (regularisation / leave / WFH / shift swap), dates, policy check (✓ within policy / ⚠ exception with clause), team-overlap note that shows only "2 others away" (never leave types). Buttons: Approve · Reject · Ask a question. After tap: "Recorded in Keka ✓". Note: the approver is re-verified server-side.

## 11. HR admin home

> HR home dashboard.
> - **KPI tiles:** questions this week, % resolved without HR, tickets deflected × minutes-per-ticket (with a settings link "you set: 6 min/ticket"), open escalations, letters pending.
> - **Chart:** top question topics this month, **organisation-level only**.
> - **Tables:** open escalations (employee, topic visible only to the assigned HR person, age, SLA badge), and "Couldn't answer" questions (de-identified) each with an "Add answer" button.
> - **Footer note:** "Team-level breakdowns are hidden for groups under 5 people."

## 12. Policy library + FAQ override editor

> Policy table: name, applies to (location / grade / employment type), visible to (access group), effective from, status (Active / Draft / Superseded), version.
> Policy detail: document preview on the left with highlighted clauses. On the right, **extracted rules** as cards with an **Impact** column ("changes leave numbers" / "explanatory only"). Only number-changing rules need approval; the rest default to "cite, don't compute". Version timeline with a "What changed" diff. Red banner if two active policies conflict. Clauses that came from OCR are marked "needs review".
> Separate tab, **FAQ overrides**: a list of question patterns with HR-written answers that take priority over the AI. Add/edit inline, with a preview of how the bot will reply.

## 13. Letter request queue

> HR queue of letter requests: salary certificate, address proof, employment verification, experience/relieving letter. Columns: employee, letter type, purpose (bank/visa/other), requested on, status. Detail: the letter auto-filled from a template + Keka data, with editable fields highlighted, "Approve & send" (secure link to employee), and "Reject with note".

## 14. Escalation ticket detail

> HR ticket: chat transcript (with what the bot looked up and why it escalated), employee context card (role, location, tenure; no salary unless the HR role allows), an AI-drafted reply clearly labelled "Draft — review before sending" (editable), internal notes, assignee, SLA timer. The reply goes back on the same channel (channel icon shown).

## 15. Broadcast composer

> Compose an announcement: audience picker (all / location / department / shift / client process), channel (WhatsApp template / Teams / email), message editor with WhatsApp template preview, schedule, and an estimated WhatsApp cost line ("~1,200 utility messages ≈ ₹140 billed by Meta to your account"). Common templates: holiday notice, payroll cut-off, policy change.

## 16. HR team workload

> Simple view: each HR team member with open tickets, letters pending, avg first-response time, and SLA breaches this week. Reassign by drag-and-drop. No employee-level analytics.

## 17. Integrations

> Tiles: Keka, greytHR, Zoho People, Darwinbox, Google Workspace, Microsoft 365, Microsoft Teams, Slack, WhatsApp Business, Telegram. Each tile shows connected/not, last sync, and **exact permission scopes** ("read leave balances", "create regularisation request"). The connect modal explains that keys are stored encrypted on your server.

## 18. My data (employee)

> One simple page: what PeoplePilot uses about me, who viewed my records (log), my conversations (delete), the DPDP notice text, and a "Raise a data request" button. Friendly plain language.

---

## Screen build order
1. Phase 1: **1 → 2 → 3 → 4 → 5 → 6 → 7** (enough to run the pilot at your brother's company and one placement cell).
2. Phase 2: **8 → 9 → 10 → 12 → 11 → 13 → 14**, then 15–18.

## Hand-off checklist (design → code)
- Export design tokens (colours, type scale, radii, spacing) from Figma as CSS variables / Tailwind config.
- Keep Lovable's React + Tailwind + shadcn/ui output. Point API calls at FastAPI:
  - Phase 1: `/api/setup`, `/api/rounds`, `/api/candidates`, `/api/bookings`, `/api/health`, `/api/audit`
  - Phase 2: `/api/chat`, `/api/policies`, `/api/faq`, `/api/letters`, `/api/tickets`, `/api/broadcasts`
- The front end never decides permissions. Every check is server-side (safety nets 0, 1 and 3 in `council/VERDICT.md`).
- Button payloads carry a single-use nonce from the server; never build actions client-side.
