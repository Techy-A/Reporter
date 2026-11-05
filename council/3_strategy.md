# Council Seat 3: Skeptical B2B SaaS Founder/Investor (Indian HR-tech, SMB GTM)

*Revised for the constraint that the product is free for everyone, with no paid SaaS.*

## 1. Does "free" change the wedge?

**Free against free is not a wedge.** greytHR NAVOS, Kredily KAI and Zimyo already give away an agent inside the system of record, with permissions, data and support built in. A free overlay still costs an HR team setup time, an integration, a security review and a new vendor to trust. "₹0" beats "₹0 plus zero setup" only when the free product does something the bundled one structurally cannot.

**What free plus open source *does* unlock:**
1. **Self-hosting and data control.** The employer runs it on its own cloud with its own keys, so employee data never reaches a startup's servers. That defuses the strongest objection to a student-built HR tool under DPDP: "who are you, and where does our data go?" It also deletes most of the plan's compliance burden (DPA, ISO 27001, residency), because the vendor is no longer a processor.
2. **Use by people who are not HRMS customers.** Firms on Excel or a local payroll vendor, staffing agencies, CA firms serving clients, and college placement cells.
3. **Extensibility.** Developers can add connectors (Keka, Zoho, Darwinbox) that a solo founder never could.

**Still the wrong wedge:** HRMS-agnostic employee policy Q&A. It needs N connectors, carries the highest liability per wrong answer, and competes head-on with the bundled agents.

**My one wedge: an open-source, self-hostable WhatsApp interview-scheduling and no-show agent.**
- It covers one of the brother's named time sinks.
- It needs no HRMS connector, only Google/M365 calendar plus WhatsApp.
- It has no policy-correctness liability.
- Candidates are external people whom NAVOS and KAI never reach.
- It has countable value: recruiter hours saved and no-shows avoided.
- It fits a niche no incumbent serves for free: **college placement cells and staffing agencies**. A student founder has privileged access to placement cells.

## 2. MVP: cut it by roughly 80%

The plan's 11-component MVP (8 safety nets, Bedrock residency, Langfuse, two HRMS connectors, Slack plus WhatsApp, a rules engine, Hinglish evals, analytics) is a 6–9 month build for a team. For a solo founder in 10 weeks, ship one workflow:

**Features:**
- A recruiter uploads a candidate CSV and links a calendar.
- A WhatsApp utility template offers 3 slot buttons, then books the slot and creates the invite.
- Reminders go out at T-24h and T-2h, with Reschedule and Can't-make-it buttons.
- A status table shows each candidate.
- The LLM is used only to classify free text. Anything it cannot handle is handed to the recruiter.

**Packaging:**
- `docker compose up` with a single Postgres, plus a setup wizard for Meta Cloud API credentials and an LLM key.
- Safety at MVP depth: tenant isolation, no free-form tools, PII-redacted logs, and an audit table.
- **Start Meta business verification in week 1.**

**Pilot success metric** (6 weeks, measured against a 2-week manual baseline at the brother's company or one placement cell):
- ≥60% of interviews scheduled with zero recruiter touch;
- no-shows down ≥25%;
- the team **keeps using it after the pilot without the founder's help**.

## 3. Sustaining running costs at near-zero budget

**Rule: the founder never pays for other people's usage.**
- **BYO everything by default.** Each adopter uses their own WhatsApp Business number and pays Meta directly. Each number gets 1,000 free service messages a month, and utility templates cost about ₹0.115 each, so roughly ₹1–2 per scheduled interview. Each adopter also brings their own LLM key. A button-first flow makes LLM cost close to nil, and a small or local model can do the classification.
- **No free hosted multi-tenant service.** That is where free projects bleed out, and it would make the founder a DPDP data processor. At most, run one demo sandbox with hard caps.
- **Cover the founder's own costs (demo, CI, pilot) with:**
  - cloud and AI startup credits (AWS Activate, Google for Startups, Microsoft for Startups, model-provider credit programmes);
  - GitHub Sponsors and Open Collective;
  - Indian FOSS grants (for example FOSS United);
  - university incubator funds.
- **Optional paid paths later, if wanted:** managed hosting, setup help for agencies, or sponsorship by a BSP or ATS vendor that benefits from the integration. Leave the door open but do not build for it now.

## 4. Winning adoption and trust

**Trust:**
- Use a permissive or AGPL licence, with the code public from day one.
- Keep a clear `SECURITY.md` and a threat model that borrows the plan's 8-nets doc as a roadmap.
- Use no telemetry, or only opt-in telemetry.
- Self-hosting is the trust argument. Say "your data never leaves your servers" up front.

**First 10 adopters:**
1. The brother's company.
2. Three or four placement cells, starting with the founder's own college and then nearby colleges via TPO networks.
3. Three or four staffing agencies reached through the brother's TA network and local HR WhatsApp and LinkedIn groups.
4. One or two CA or payroll firms willing to deploy it for clients.

**Distribution:**
- Post on GitHub with a 90-second Hinglish demo.
- Post on r/developersIndia, Hacker News (Show HN) and FOSS United meetups.
- Write "how we cut no-shows by X%" case posts from the pilot.

**Lower setup friction.** The real enemy is the 2–6 weeks Meta verification takes for each adopter. Write a step-by-step guide, and consider partnering with a BSP that offers fast onboarding.

## 5. Kill criteria (adoption, not revenue)

- **Week 3:** fewer than 5 of 20 TA/TPO/HR conversations rank scheduling or no-shows as a top-3 pain, or fewer than 3 commit to a pilot. → Re-wedge.
- **Week 6:** an adopter cannot get from zero to their first scheduled interview in under 1 day of their own effort (Meta verification excluded), or WhatsApp verification blocks most pilots. → Simplify or move to email/SMS.
- **Week 8:** zero-touch scheduling is under 40%, or recruiters route around the bot.
- **Week 12:** fewer than 3 organisations are still active 4 weeks after onboarding without founder hand-holding, or nobody from outside the founder's network has deployed it. → Pivot or stop.
- **Ignore GitHub stars.** Count only *active deployments* and *interviews scheduled per week*.

## 6. Biggest disagreement

**The plan perfects the architecture before anyone has said they want the product.** "Free" makes that worse, not better.
- The plan is an enterprise blueprint (8 safety nets, India residency, differential-privacy analytics, ISO 27001) whose wedge comes from desk research, not from users.
- Free removes the revenue test, so the only remaining proof is **retained usage**, and a 10-week build of 11 components yields none.
- In a free model, self-hosting and BYO keys *replace* most of that compliance stack.
- So: ship one narrow, self-hostable workflow, get 3 organisations using it unaided, then add the safety nets as real deployments demand them. Tenant isolation and no-PII logs ship on day one.
