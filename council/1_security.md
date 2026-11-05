# Council seat 1: Adversarial security & privacy red-team

## 1. Top 5 first-year breach and leak paths

1. **The WhatsApp number becomes the password.** The MVP says "OTP-free verification via the HRMS record", which means anyone who sends from a number listed in the HRMS is treated as that employee. Indian operators recycle numbers after about 90 days of inactivity. SIM swaps are common, and deskless staff share family phones. Offboarding sync also lags. A recycled number or a swapped SIM then receives payslips, balances and PF/UAN status. This is the most likely incident, and it lands in the very segment the product is built for.
2. **One stolen connector token exposes an entire employer.** Keka and greytHR client-credentials tokens are org-wide admin tokens. "On-behalf-of identity, never a superuser" cannot be achieved against these APIs, so all authorization lives in our tool layer. A single bug in `get_my_*` tools, an SSRF, or a leaked secrets store exposes every tenant's HRMS. RLS protects only our own Postgres, not the vendor APIs.
3. **Employee text hijacks a more privileged agent.** Employee messages reach the HR ticket console, where the AI drafts the reply. They also feed manager copilots, and later candidate emails, calendar invites and LMS titles reach the workflow agent. Injected instructions in a low-privilege input execute with HR or manager privileges, for example by putting another employee's data into a "suggested reply" or exfiltrating through a link. The plan guards uploads and policy PDFs, but this lateral path is the more dangerous one.
4. **Over-scoped policy context and caches.** Long-context stuffing sends the whole "active policy set" to every employee. Handbooks routinely contain restricted material such as executive severance, grade pay bands and investigation SOPs. Filtering by location, grade and employment type is not an access-control list. The provider's prompt cache is fine. The real cross-tenant risk is an app-level answer or semantic cache, or a mis-keyed cache prefix, that serves one tenant's or one grade's content to another.
5. **The telemetry becomes the honeypot.** Langfuse traces, full-transcript handoff tickets, "Knowledge gaps" raw questions, golden sets built from "200 real questions per pilot", and promptfoo CI fixtures all collect free-text health, pregnancy and grievance disclosures. Presidio catches Aadhaar and PAN but not "my wife miscarried". Sensitive-topic classification also runs after the turn has already been traced and sent to the LLM. LLM-provider retention is a smaller risk than our own logs, eval sets and CI repository.

## 2. The 8 safety nets

- **#1 contradicts the WhatsApp wedge.** "SSO is the source of truth" does not hold for deskless WhatsApp users, who have no SSO. The binding should work like this:
  - **Enrolment:** bind the WhatsApp `wa_id` to the employee through an HRMS-sent magic link or email OTP, plus a one-time code shown in the web or SSO session.
  - **Re-checks:** re-verify every 60–90 days, and force re-enrolment whenever the `wa_id` or profile changes.
  - **Step-up:** require a PIN or OTP before payslip, compensation, bank or PF details.
  - **Payslips:** deliver them as single-use authenticated links with a 10-minute TTL. Never send them as attachments.
  - **Exits:** revoke access on the exit or last-working-day webhook or a daily diff. Absence of the employee from the next sync also triggers revocation.
  - **Slack/Teams:** map users by immutable user ID, not by display email.
- **#2 (Prompt Guard) should be demoted to telemetry.** It is weak on Hindi and Hinglish and easy to bypass. It should not count as a "net".
- **#4 needs a trust-level model.** "Write tools disabled once untrusted content enters context" needs a definition of trust. Policy corpus = trusted-admin. Employee text = untrusted. Third-party email = hostile. Add a rule that no agent may hold both untrusted text and tools above the caller's own privilege.
- **#5 is a quality control, not a security control.** It should not crowd the security budget.
- **#6 HITL:** each confirmation needs a single-use nonce bound to a hash of the diff, plus an expiry, so that replayed or stale WhatsApp button payloads fail. Re-check the approver's identity server-side, because a Slack button can be clicked by anyone in the channel.
- **#7 output DLP is vague.** Make it concrete: block other-employee names, IDs or amounts that do not appear in the caller's tool results for the turn, strip all URLs and markdown, and allow-list deep-link domains.
- **#8 is mis-ordered with sensitive routing.** "Sensitive matters never touch the LLM" is false if the classifier is an LLM. The order should be: local classifier plus keywords → buffered trace → commit or drop.
- **Audit vs. traces:** keep the audit log metadata-only (actor, tool, record IDs, decision) for at least one year. Keep content traces for 30 days or less.
- **Missing controls to add:**
  - Per-tenant KMS envelope encryption for connector secrets.
  - Document-level ACLs on the policy corpus.
  - No standing vendor production access: break-glass only, with a log visible to the customer.
  - Mandatory MFA for HR admins (they hold the keys to the corpus and the rules).
  - Per-identity enumeration and rate limits.
  - A 72-hour breach runbook, drilled before the pilot.

## 3. Analytics: what I'd move

- **Team-level leave patterns, green → amber.** In a 4-person team, the leave type reveals maternity or medical leave. Suppress leave type and apply k≥5.
- **Aggregate query topics per team, green → amber.** "Maternity policy" queries from a team of 6 amount to a pregnancy inference. Topics should be org-level only, or apply k.
- **"Knowledge gaps" raw questions, green → amber/red.** De-identify them, and send nothing from sensitive classes.
- **Manager inbox and team calendar (currently implicitly green) need a fix.** Show "away", never the leave type.
- **Escalation table topic: restrict it to the assigned HR person only.**
- **Amber tier for tenants under about 150 employees: do not ship.** DP noise and k-floors are not meaningful at that size.

## 4. Must-fix before pilot (≤8)

1. WhatsApp `wa_id` binding, step-up auth, exit revocation, and link-based payslips (see §2).
2. Per-tenant encrypted connector secrets, with authorization unit and property tests on every tool (salary-probe and IDOR suite).
3. Document-level ACLs on the policy set, plus caches keyed on tenant, scope and ACL hash. No cross-user answer cache.
4. Sensitive-topic routing runs before any LLM call and before any trace is committed.
5. Trace and audit split with retention limits. No real employee text in golden sets or CI without de-identification and the fiduciary's written consent.
6. Confused-deputy isolation: employee and third-party text never reaches a tool-bearing HR or manager agent. Treat AI drafts as untrusted output.
7. HITL nonce and diff-hash binding, with server-side approver checks.
8. MFA for HR admins, vendor break-glass access, a DPA, and a drilled 72-hour breach runbook.

**Can wait:** Llama Guard, Prompt Guard tuning, CaMeL-lite (until employees can upload documents), DP noise, amber analytics, SOC 2, and the Indian-region Bedrock verification (do it, but it is not a breach path).

## 5. Biggest disagreement

The plan treats identity as a mapping exercise ("phone/email-to-HRMS employee mapping, OTP-free") and puts its security effort into LLM-shaped threats: injection filters, groundedness and citations. In year one this product will not be breached by a clever prompt. It will be breached by a phone number that now belongs to someone else, or by an org-wide HRMS token sitting behind a buggy tool. Identity binding and connector-credential blast radius should be the top items, and ahead of all eight nets.
