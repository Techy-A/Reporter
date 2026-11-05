# Council seat 4: HR Head, 250-person IT/BPO (Keka + separate LMS, 4 HR staff, shifts and cabs, POSH IC)

## 1. Would I buy it?

**Not as the plan describes it today.** I would sign a paid pilot only if the 30-minute demo shows these:

- **It runs on my own Keka tenant.** Connect it, pull my employees, answer "my leave balance" and "my missed punch on 3 Nov" with real numbers. Do not show me a sandbox.
- **It writes to Keka.** A regularisation or leave request should be created in Keka and appear in the manager's normal Keka approvals. If all I get is a deep link, Keka's own app already does that and I will not pay twice.
- **It answers from my handbook with the clause quoted**, including one trap question where it says "I don't know, routing to HR" and the ticket lands with the full chat attached.
- **It has a price per month that I can defend to my CFO against Keka.** At ₹40–100 PEPM that is ₹1.2–3 lakh a year. Show me 15+ HR hours a week saved, or it is a no.

**What makes me walk out:**

- **The security questionnaire.** Our US/UK BPO clients audit our subprocessors. "ISO 27001 started" fails that audit. I need ISO 27001 or a SOC 2 report, a DPA, a subprocessor list and India data residency on day 1, not in phase 4.
- **Setup that takes my team more than about two days.**
- **"Keka already does X."** Keka has self-service, a helpdesk/ticketing module, an approval inbox and a mobile app. Anything that only repeats those is noise.
- **Employees ignore it.** If adoption is below 40% in month 1, it dies.

## 2. Workflows that actually save hours (ranked)

1. **Attendance regularisation and missed punches.** This is our largest daily volume: biometric failures, shifts that cross midnight, late cab logins. I need it to check against the roster and raise the request in Keka.
2. **Payroll and tax queries.** Payslip breakup, TDS, investment declaration and proof deadlines, Form 16 download, reimbursement status, and full-and-final (F&F) status for people who have left. Ex-employees chase F&F constantly.
3. **Letters.** Salary certificate, address proof, employment verification for banks and visas, and experience/relieving letters. These come from templates plus Keka data and go to HR for approval. That is about 5 hours a week today.
4. **Cab and roster.** Drop-point changes, shift swaps (supervisor approves), cab no-show complaints, and the night-shift transport rules for women.
5. **Leave balance, apply leave and clubbing rules.** These are useful, but Keka partly covers them already.

**Nice-to-have:** training nudges (my LMS already sends them), interview scheduling (TA uses Keka Hire), induction checklists.

**Remove entirely:** the productivity tracker. My night-shift agents will call it surveillance, and the union-style WhatsApp groups will make sure everyone hears that.

**Missing from the plan:**

- Holiday calendar by location and by client process. A US-process team works Diwali.
- Shift swaps.
- Letter generation.
- F&F and exit queries.
- Form 16 and tax-declaration windows.
- ID card, asset and access-card requests.
- Broadcasts to all staff: policy changes, holiday notices, payroll-cut-off reminders.
- Support for ex-employees, who have no SSO.

## 3. Setup reality

**What I will tolerate:** 2 HR person-days and 1 week elapsed. That covers uploading 8–12 policy PDFs and approving the top 15–20 rules. I will not review 80 rule cards. Show me the ones that drive numbers and default everything else to "cite, don't compute".

**What must be zero-effort:**

- Employee and phone mapping pulled from Keka.
- Manager hierarchy and location/grade scope pulled from Keka.
- WhatsApp opt-in sent by the product.
- Holiday calendar imported from Keka.

**IT involvement:** one SSO/Teams admin consent and one Keka API key, nothing more. If my IT head has to deploy anything, it slips by a quarter.

## 4. Employee channels

- **BPO floor agents (about 60% of my headcount).** Many client processes ban phones on the floor (clean-desk rules). They use WhatsApp only on breaks, in the cab and at home. That is also exactly when they hit missed-punch and cab issues, so **WhatsApp is essential for them**. Their desktops are locked down, and Teams is often blocked on client VDIs.
- **IT and office staff:** Teams first, web second. Almost nobody will open a separate web app.
- **Ex-employees:** WhatsApp or email only.
- **Language:** English plus Hinglish typing covers 90%. Formal Hindi is rarely needed. If I have a southern site, Tamil/Telugu matter more than Hindi. Voice notes are low priority for this workforce.

## 5. The 11 screens

**Cut or defer for v1:**

- **#7 Workflow builder.** I will never build flows. Ship preset toggles.
- **#9 Safety centre as a live page.** Make it a downloadable trust pack for IT. A dashboard showing "312 injection attempts blocked" will alarm my CFO, not reassure him.
- **#11 Landing page.** This is marketing, not product.
- **#10 My data.** One simple page is enough.
- **#3 Manager inbox.** This duplicates Keka approvals. Managers will not approve in two places. Replace it with a Teams/WhatsApp approval card that writes back to Keka.

**Missing:**

- An **identity/sync health** screen: unmapped phone numbers, opt-in percentage, last Keka sync.
- A **letter request queue**.
- An **FAQ/answer override editor** that lets me fix one answer without re-uploading a policy.
- A **broadcast** composer.
- An **HR team workload** view showing tickets per HR person.

**What will confuse people:**

- **"Hours saved (estimate)"** on #4. I will not trust a vendor-computed number. Show tickets deflected and the minutes per ticket that I configured.
- **Mixing health with POSH in #2.** "I have fever, need sick leave" must not trigger the locked screen. Keep the fixed script for POSH, self-harm and legal only.
- **The left-hand conversation history in #1.** It is pointless on mobile. Chips are what count there.
- **Rule cards in #5 with no "impact" column.** HR cannot tell which rules change numbers.

## 6. My biggest disagreement

**The plan puts its weight on the wrong things: citation-perfect policy Q&A and safety architecture. My hours go into transactional work.** Regularisation, letters, F&F and tax queries, and cab/shift changes are pushed to phase 2 or are missing entirely. Meanwhile the MVP's write path depends on a Keka write API that the plan itself calls "unconfirmed".

If the agent cannot create records in Keka, I am paying for a polite FAQ bot with a WhatsApp skin. Confirm Keka write access (attendance regularisation, leave) before writing any other code, and make letters plus regularisation the v1 hero workflows. Policy Q&A is table stakes. Getting work done in Keka is what I would pay for.
