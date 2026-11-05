# HR Workflow Automations and System Integrations (India-first, as of Nov 2026)

Scope: which HR workflows from an Indian HR practitioner's pain-point list an AI agent can automate end to end; the systems, APIs and channels involved; and where humans must stay in the loop. Research was limited to about 17 tool calls. Many vendor API details come from third-party directories (Knit, Apideck, Ballerina, Jentic) rather than the vendors' own docs, and are flagged where that applies.

---

## 1. Per-workflow automation pattern, data, system of record, approval step, failure modes

### Takeaway
Most of the "frequent questions" are read-only lookups (leave balance, appraisal timing, payroll and overtime credit date) or policy Q&A, and can be fully automated with RAG over the company policy plus an HRIS read API. Transactional flows (apply leave or WFH, schedule interviews, chase training completions) can be automated up to a manager approval step that the HRIS already enforces. The categories the practitioner named as human-only (POSH, succession, workforce planning, internal mobility, performance, data breach) should be intake and routing only.

### Cited Findings
- Keka exposes leave types (`/api/v1/time/leavetypes`) and leave balances (`/api/v1/time/leavebalance`) on the tenant domain, using OAuth 2.0 client credentials. This is per third-party directories, not the official reference — [Knit Keka API directory](https://getknit.dev/blog/comprehensive-guide-to-keka-api-directory.md); [APIs.io Keka](https://apis.io/providers/keka/)
- An unofficial figure puts the Keka rate limit at about 50 requests per minute — [Keka search summary via Knit/APIs.io](https://getknit.dev/blog/comprehensive-guide-to-keka-api-directory.md) (unverified)
- Keka webhooks ("Event Triggers") are configured under Settings > Communications > Event Triggers, and setup needs the "manage event triggers" permission. Documented events include `leaverequestcreated`, `EmployeeSalaryUpdated` and `exitCancelled`, with "expense approved", "employee added" and "employee exit approved" given as examples. The payload is form-encoded (`employeeIdentifier`, `eventType`, `subDomain`). No signature scheme is documented; optional custom headers can be added — [Keka developer docs: webhooks](https://developers.keka.com/docs/getting-started-with-webhooks)
- Microsoft Graph `findMeetingTimes` suggests slots using attendees' working hours and free/busy data. It supports required and optional attendees and `minimumAttendeePercentage`, returns `emptySuggestionsReason` when nothing fits, and defaults to UTC unless a `Prefer: outlook.timezone` header is sent. It works only with Microsoft 365 work or school mailboxes — [Microsoft Learn: findMeetingTimes](https://learn.microsoft.com/graph/findmeetingtimes-example)
- Docebo webhooks include `course.enrollment.completed` and `course.enrollment.updated`. An older (2021) community thread reported no learning-plan-completion webhook and recommended polling a completion report as a workaround — [Docebo webhook events](https://developer.docebo.com/docs/webhooks-events); [Docebo community](https://community.docebo.com/integrations-apis-45/api-webhooks-completed-learning-plan-594)
- TalentLMS has no generic webhooks. An admin "automation" can call a URL on course completion, passing user ID and course ID as GET parameters, and further data then comes from the API — [TalentLMS help](https://help.talentlms.com/hc/en-us/articles/9651457002908-How-to-trigger-a-custom-action-when-users-complete-a-specific-course-in-TalentLMS)
- SAP SuccessFactors Employee Central Time Off is reached through OData v2 (time accounts, holiday calendars, time-off requests). The Time Account object is "Secured", so the API user needs role-based permissions. Leave-of-absence updates fail validation if the actual return date is not one day after the end date — [WSO2 SF Time Off connector](https://wso2.com/integration-platform/docs/connectors/catalog/hrms/sap.successfactors.ectimeoff/overview); [SAP KBA 2836870](https://userapps.support.sap.com/sap/support/knowledge/en/2836870); [SAP KBA 3649713](https://userapps.support.sap.com/sap/support/knowledge/en/3649713)
- Workday Absence Management over REST v1 (OAuth 2.0 bearer) offers balances for absence plans and leave types, leaves of absence by worker, and eligible absence types, capped at 100 objects per response. `POST /workers/{ID}/requestTimeOff` is listed for time-off requests. This comes from a generated or third-party spec, not Workday's own docs — [Ballerina Workday absence connector](https://central.ballerina.io/ballerinax/workday.absencemanagement/1.5.1); [Jentic Workday absence](https://jentic.com/apis/workday.com/workday-absence-management); [dltHub](https://dlthub.com/context/source/workday-absence-management)
- The standard Fivetran Workday HCM connector reportedly does not cover ordinary time off via REST, only long absences. This is a sign that time-off coverage varies between integration layers — [Fivetran community](https://support.fivetran.com/hc/en-us/community/posts/37967583395479-Connector-Improvement-Request-to-implement-REST-APIs-for-Absence-Management-in-Workday-HCM-connector)
- greytHR API v2 employee endpoints (for example `GET https://api.greythr.com/employee/v2/employees/{id}`) and leave endpoints are documented by Knit. greytHR does not publish rate limits — [Knit greytHR guide](https://getknit.dev/blog/developer-guide-to-get-employee-data-from-greythr-api); [Knit greytHR leave](https://getknit.dev/blog/developer-guide-to-get-employee-leave-information-from-greythr.md)
- Darwinbox API access is request-only (integrations@darwinbox.in). Auth uses a SHA-512 hash of admin email + secret key + epoch timestamp; sources differ on the exact inputs. Docs are at api-docs.darwinbox.com. One source says there are no native webhooks, so polling is needed — [Knit Darwinbox](https://getknit.dev/blog/a-to-z-of-integrating-with-darwinbox-api.md); [Bindbee Darwinbox](https://bindbee.dev/feeds/service/darwinbox-api-documentation)
- Freshteam is covered by Apideck (ATS and HRIS) and Unified.to. In those layers its webhooks are "virtual" (generated by polling) rather than native. Employee created, updated and terminated events are listed; interview-specific events were not confirmed — [Apideck Freshteam ATS](https://developers.apideck.com/apis/ats/freshteam); [Unified.to Freshteam](https://docs.unified.to/integrations/freshteam.md)
- On Zoho People leave-balance API, I found only a community forum thread, no official docs — [Zoho community](https://help.zoho.com/portal/en/community/topic/api-leave-balance?page=4)

### Inferences (workflow-by-workflow design; derived from the findings above plus general practice)

| Workflow (from practitioner) | Automation pattern | Data needed | System of record | Human / approval step | Failure modes |
|---|---|---|---|---|---|
| Leave balance query | Read-only tool call (Keka leavebalance / SF Time Account / Workday balances / greytHR leave) and answer | Employee ID mapped from chat identity (email or phone), leave types | HRIS | None | Identity mismatch (WhatsApp phone not in HRIS); stale accruals; SF Time Account permission missing; rate limits |
| When overtime money is credited | RAG over payroll calendar and policy, plus a payroll-run status lookup if the API exposes it | Payroll cut-off dates, OT approval status | Payroll module (Keka Payroll, greytHR, SF ECP) | None for the info; OT approval stays with the manager | Bot states a date that the payroll team then slips; OT not yet approved. Answer with "as per cycle" plus status, never promise a credit |
| Notice-period buyout option | Policy RAG answer, then a guided flow to raise a request to HRBP | Offer letter or appointment terms, policy | HRIS / contract docs | HRBP and manager approve buyout and recovery amount | Contract-specific terms differ from the generic policy, so the bot should cite the employee's own contract if available, else route |
| PF / EPF / EPS nomination how-to | Guided step-by-step flow linking to the EPFO Unified Member Portal; collect nothing sensitive | UAN activation status (HRIS), Aadhaar-seeded status | EPFO (external); UAN in HRIS | None; employee self-serves on EPFO. The bot must never collect Aadhaar, OTP or UAN password | User has no activated UAN, Aadhaar not seeded, or no photo; PPF confusion (PPF is a bank/post-office product and not employer-administered) |
| Who to contact for employee referrals | Policy and directory RAG, plus ATS deep link (Freshteam / Keka Hire / Darwinbox referral portal) | Referral policy, bonus rules, TA owner | ATS | None | Outdated owner names, so pull from the HRIS org chart rather than static docs |
| Are trainings mandatory | LMS lookup of assigned courses with a "mandatory" flag and due dates, plus policy RAG | Assignments, due dates | LMS | None | Mandatory flag modelled differently across LMSs |
| Can sick + casual leave be clubbed | Policy RAG (company leave policy) with an explicit "per company policy" answer | Leave policy document by entity or state | Policy docs / HRIS leave rules | None; edge cases go to HR | State Shops and Establishments Acts and the company policy vary, so the bot must not generalise nationally |
| Appraisal timing | RAG over the performance-cycle calendar, plus PMS cycle API if available | Cycle dates | PMS (Keka PMS / SF PM / Workday) | None | Bot drifting into ratings or outcomes, which is human-only |
| WFH for a date range | Guided flow: pick dates, check policy cap, create request via HRIS API (Keka "work from home" request / SF / Workday) | Policy caps, holidays | HRIS attendance module | Manager approval inside the HRIS workflow | API may not expose WFH-request write (unconfirmed for Keka); fallback is a deep link |
| Interview scheduling | Agent: pull panel calendars (Graph `findMeetingTimes` / Google free-busy), propose slots to candidate via email or WhatsApp template, book event and video link, write back to ATS | Panel list, interview stage, candidate TZ, room | ATS (Freshteam / Keka Hire / Workday Recruiting / SF RCM) plus calendar | Recruiter can override; no approval needed for routine slots | Personal Gmail or outlook.com panelists (findMeetingTimes needs M365 work accounts); reschedules; no-shows; ATS write-back gaps (Freshteam interview events unconfirmed) |
| Induction / onboarding | Event-driven: "employee added" webhook (Keka) triggers checklist tasks, document collection, LMS enrolment, IT ticket, buddy intro, day-1 schedule | Joining date, location, role | HRIS | HR verifies documents (BGV, statutory forms such as Form 11 and Form 2) | Document fraud or OCR errors; joining date changes |
| Training-completion follow-ups | LMS completion webhook (Docebo) or automation URL (TalentLMS) or polling (Moodle/others), then a nudge sequence to employee and escalation to manager | Assignments, due dates | LMS | Manager escalation after N nudges | Learning-plan completion events missing (Docebo); spam fatigue; WhatsApp costs per template |
| Daily productivity trackers | Scheduled pull from attendance and project tools into a sheet or dashboard; bot collects a daily stand-up via buttons | Attendance, timesheets | HRIS attendance / PM tool | Manager review | Surveillance and privacy concerns (DPDP Act); data quality |
| Grievance answering via chat | Classify the message. FAQ-type grievances (payslip error, reimbursement delay) go to a ticket in HR helpdesk with SLA. Sensitive categories (harassment, discrimination, safety, data breach) bypass the LLM and route to a human or the IC | Ticket system | Helpdesk / HRIS | Always human for resolution of real grievances | Misclassification of a POSH complaint as a general grievance (highest-risk failure) |
| Cab / rota assignment | Rule or optimisation engine fed by the shift roster and addresses; bot shares the cab/rota and takes swap requests via buttons | Shift roster, addresses, women's night-shift safety rules | Rostering tool / transport vendor | Supervisor approves swaps; transport desk for escalations | Last-minute changes; safety-compliance rules for women on night shifts (state-specific) |
| POSH, succession, workforce planning, internal mobility, performance, data breach | Intake and routing only; the bot provides information and handoff | n/a | n/a | Fully human | See section 5 |

### Gaps
- Official Keka API reference pages for leave apply, WFH requests, attendance and Keka Hire interview objects were not fetched (an index exists at developers.keka.com/llms.txt).
- Zoho People official leave API docs were not found.
- Moodle `core_completion_*` web-service details were not found in this pass. Moodle is known to use REST web services with tokens, but this was not verified here.
- No vendor documentation was found for a "payroll credit date" API on any HRIS.

---

## 2. Public APIs/webhooks per vendor, unified HRIS APIs and India coverage, MCP servers

### Takeaway
Every target system has some API, but access models differ widely. Keka uses self-serve OAuth plus admin-configured event triggers. Darwinbox and greytHR are request-gated or partner-gated. Workday and SuccessFactors are enterprise APIs needing tenant admin setup. Western unified APIs (Merge, Finch, Kombo) have weak or unconfirmed coverage of Indian HRIS such as Keka and greytHR; Knit is the unified API that lists Keka, greytHR and Darwinbox. Darwinbox is the only HRIS confirmed to ship its own MCP server.

### Cited Findings
- Unified API coverage:
  - Knit lists Darwinbox as a live connector, and publishes Keka and greytHR API guides — [Knit](https://getknit.dev/?p=455); [Knit greytHR](https://getknit.dev/blog/greythr-api-guide.md)
  - Merge has a Darwinbox integration page, and lists Zoho People as Beta — [Merge Darwinbox](https://www.merge.dev/integrations/darwinbox?ff2089a5_page=2); [Merge Zoho People](https://www.merge.dev/integrations/zoho-people)
  - Kombo supports Zoho People read and write — [Kombo Zoho People](https://www.kombo.dev/integrations/zohopeople/hris)
  - Apideck covers Freshteam (HRIS and ATS) — [Apideck Freshteam](https://developers.apideck.com/apis/hris/freshteam)
  - No Merge, Finch or Kombo listing for Keka or greytHR was found — [search synthesis; Kombo vs Merge](https://www.kombo.dev/blog/kombo-vs-merge)
- Integration counts are self-reported and conflict. Kombo claims about 85 HRIS integrations vs Merge's 80 (Kombo blog); Nango lists Merge at 87 HRIS (8 being identity or file). Finch is quoted at 180+ (Personio) and 250+ elsewhere — [Kombo vs Merge](https://www.kombo.dev/blog/kombo-vs-merge); [Nango](https://nango.dev/blog/best-unified-apis-for-hris-ats-payroll); [Personio partner page](https://developer.personio.de/docs/ipaas-partner)
- Darwinbox launched its own remote MCP server in May 2025 (beta for select customers and partners). It exposes core HR functions as tools and respects API-level ACLs and RBAC — [People Matters](https://www.peoplematters.in/?p=45528); [The Week wire](https://www.theweek.in/wire-updates/business/2025/05/13/dcm27-darwinbox.html)
- Workday MCP status is unclear. One source reports "Agent-Ready Tools" in early access with GA projected later in 2026; another says MCP support comes via an Agent Gateway with no standalone server. SuccessFactors has no vendor-run MCP server, only community servers or gateways — [Hirevire MCP for HR guide](https://hirevire.com/articles/mcp-for-hr-guide); [Calamari MCP for HR](https://calamari.io/blog/mcp-for-hr-how-the-model-context-protocol-is-changing-what-ai-can-actually-do-in-your-hr-stack)
- A community Keka MCP server exists (huebnermarketing/keka-mcp) — [Glama: keka-mcp](https://glama.ai/mcp/servers/huebnermarketing/keka-mcp)
- Zoho Recruit (not Zoho People) reportedly runs its own MCP server — [Hirevire](https://hirevire.com/articles/mcp-for-hr-guide)

### Inferences
- For an India-first product, a direct Keka connector is the priority, since no major Western unified API was confirmed to cover it. Knit is the main unified option spanning Keka, greytHR and Darwinbox. Merge or Kombo would suit Workday, SuccessFactors and Zoho People.
- Keka webhooks lack documented signature verification, so the receiver should use a secret custom header plus IP allow-listing, and re-fetch the record via API rather than trust the payload.
- Darwinbox and greytHR onboarding needs a per-customer request to the vendor, which adds sales-cycle friction. Budget for polling where webhooks are absent (Darwinbox, Freshteam).
- Community MCP servers (Keka, SuccessFactors) are fine for prototyping but need a security review before production use with employee PII.

### Gaps
- Live connector lists for Merge, Finch and Kombo were not fetched directly, so Keka and greytHR absence is "not found", not "confirmed absent".
- Apideck's India HRIS coverage beyond Freshteam was not checked.
- The current GA status of Workday's MCP / Agent Gateway as of Nov 2026 is unverified.
- Google Calendar `freeBusy` API and Google Workspace scheduling specifics were not fetched (well known, but uncited here).

---

## 3. Channel integration: Slack, Teams, WhatsApp Business API, hybrid guided + LLM design

### Takeaway
WhatsApp is the highest-reach channel for Indian frontline and blue-collar staff, but it carries per-message costs that changed in 2026. From 1 Oct 2026, utility messages inside the 24-hour window are no longer free, and service messages are free only up to 1,000 per number per month. It also needs opt-in, template approval and INR billing migration by 31 Dec 2026. Reply buttons (max 3) and lists (max 10 rows) are a natural fit for the practitioner's "bank-style" guided flows, with LLM free text as a fallback.

### Cited Findings
- Meta has billed per delivered message since 1 Jul 2025, by category (marketing, utility, authentication = templates; service = non-template) and recipient market. User-to-business messages are free — [Meta WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- Service messages were free from 1 Nov 2024. Since 1 Oct 2026, each business phone number gets 1,000 free service messages per month (no rollover), and utility messages sent inside an open customer-service window are now charged at the regular rate — [Meta WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- The customer-service window is 24 hours from the user's last message. Non-template messages can only be sent inside it — [Meta WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- India is a standalone market. Marketing rates rose on 1 Jan 2026. INR billing launched 1 Jan 2026, and eligible India customers must migrate to INR by 31 Dec 2026; from 1 Jan 2027, messages from non-INR accounts stop delivering. Volume tiers apply to utility and authentication only. Price changes happen only on quarter starts, with one month's notice — [Meta WhatsApp pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- India rates (third-party, not from Meta's page): marketing about ₹0.8631 per message from 1 Jan 2026 (previously ₹0.7846), and utility and authentication about ₹0.115. One source cites marketing at about ₹1.09 (US$0.0118 from 1 Apr 2026). BSP fees and 18% GST come on top. The sources conflict, so check Meta's rate-card CSV — [Robylon](https://www.robylon.ai/blog/whatsapp-business-api-pricing-india); [Monty Mobile](https://montymobile.com/blogs/whatsapp-business-api-pricing-in-india-inr-rates-gst-and-the-2026-currency-migration-deadline); [FormBeep](https://formbeep.pages.dev/whatsapp-api-pricing/)
- Opt-in: businesses must collect opt-in before messaging, through an existing channel (website, SMS, email, or an onboarding form), and must provide an opt-out path. Templates require Meta approval — [Netcore WhatsApp docs](https://emaildocs.netcorecloud.com/docs/whatsapp-business-api)
- Interactive messages: reply buttons (max 3, short titles of about 20 characters; sources differ between 20 and 25) and list messages (max 10 rows) don't need templates inside the window. WhatsApp Flows (multi-screen forms) are not supported on WhatsApp Web — [Meta interactive messages](https://developers.facebook.com/docs/whatsapp/guides/interactive-messages/); [ChatDaddy rules](https://help.chatdaddy.tech/article/button-and-list-rules-in-whatsapp-messages); [ElevenLabs WhatsApp docs](https://elevenlabs.io/docs/eleven-agents/whatsapp/interactive-messages)

### Inferences
- Cost model for an HR bot: most HR chats are employee-initiated (service messages, so the first 1,000 per number per month are free). Proactive nudges (training reminders, interview confirmations, payroll notices) are utility templates at about ₹0.115 plus GST plus BSP fee. Avoid "marketing" categorisation, for example engagement or celebration messages, which costs roughly 7-9x more.
- Guided flows: use lists and buttons for the top intents (Leave balance, Apply leave/WFH, Payslip and OT, PF nomination help, Policies, Raise a ticket, Talk to HR). Use WhatsApp Flows for multi-field forms (WFH date range), with a deep-link fallback for web users. Let free text go to the LLM with intent classification. Any sensitive-category hit should switch to a fixed, non-LLM script.
- Opt-in can be captured at onboarding (HRIS form or offer letter e-sign), since employees' phone numbers are already in the HRIS. Record the consent timestamp per DPDP practice.
- Slack and Teams: use them for desk employees and managers. Use Teams Adaptive Cards for approvals (manager approves WFH in-line, with the card calling the HRIS approval API). Teams and Slack messaging has no per-message cost, unlike WhatsApp. (Teams Action.Execute and Slack Block Kit specifics were not researched in this pass.)

### Gaps
- Meta's official India rate CSV was not opened, so exact INR figures for Q4 2026 are unconfirmed.
- Teams Adaptive Card `Action.Execute` / Universal Actions and Slack Block Kit details are uncited.
- Whether WhatsApp employee-to-employer HR use can be categorised as "utility" for all proactive messages depends on Meta's template review. This was not verified.

---

## 4. EPFO/UAN nomination facts and Indian statutory leave / Labour Code basics

### Takeaway
EPF e-nomination is employee self-service on the EPFO Unified Member Portal, with Aadhaar OTP e-sign. The bot should guide the steps and never handle credentials or OTPs. The status of the Labour Codes is contested in sources: the central notification came on 21 Nov 2025, but state rules are patchy. The agent should answer statutory questions with "per company policy and applicable law" and route anything else to HR rather than assert Code-level entitlements.

### Cited Findings
- E-nomination prerequisites are an activated UAN linked to verified Aadhaar, an Aadhaar-linked mobile and a profile photo. Steps: log in to the Unified Member Portal, go to Manage > E-Nomination, confirm address, add family and nominee details with shares totalling 100%, Save EPF Nomination, then e-sign via Aadhaar OTP. A 16-digit Virtual ID can be used for e-sign — [TaxGuru EPFO circular](https://taxguru.in/corporate-law/provision-e-nomination-member-interface-unified-epfo-portal.html); [EPFO help file](https://epfindia.gov.in/EP_Cal/Doc/eNominationHelpFile.pdf); [Business Standard](https://www.business-standard.com/article/current-affairs/how-to-file-epfo-e-nomination-online-via-uan-check-steps-and-features-122061301166_1.html)
- Nominee photos are needed; one guide suggests each be under 100 KB — [Fibe](https://altcont.fibe.in/how-to-do-e-nomination-in-pf-account-step-by-step-guide/)
- Nominations can be changed later on the portal, and history can be viewed — [Outlook Money](https://www.outlookmoney.com/retirement/epf-e-nomination-what-members-need-to-do-to-ensure-it-is-complete)
- Labour Codes:
  - Law-firm alerts (Cyril Amarchand, Trilegal) report that the four Codes were notified and brought into force from 21 Nov 2025, with some provisions dependent on rules. The Jan 2026 CAM note lists leave encashment and overtime consent among rule-dependent items — [Cyril Amarchand "60 days of Labour Codes"](https://www.cyrilshroff.com/wp-content/uploads/2026/01/60-days-of-Labour-Codes.pdf); [Trilegal via ELA](https://www.ela.law/firms/trilegal/articles/trilegal-update-labour-codes-go-live)
  - A July 2026 article claims none of the Codes is in force, because commencement depends on state rules. It says Maharashtra, Rajasthan, UP and Haryana have notified rules under some Codes but no state under all four — [Bhatt & Joshi](https://bhattandjoshiassociates.com/the-labour-codes-2026-what-actually-changed-for-employers/)
  - These sources conflict. The law-firm alerts are more authoritative on the central notification; the state-rule picture remains patchy.
- OSH Code retains annual leave at 1 day per 20 days worked and keeps the 48 hours/week and 9 hours/day maximum. Under the Wage Code, allowances beyond 50% of remuneration count as "wages" — [Bhatt & Joshi](https://bhattandjoshiassociates.com/the-labour-codes-2026-what-actually-changed-for-employers/)
- Secondary reports describe eligibility for leave after 180 days (down from 240), a 30-day carry-forward cap with excess encashed, and encashment applying mainly to "workers". These are unverified against the Code text or final rules — [LatestLY](https://www.latestly.com/india/news/new-labour-codes-in-india-key-changes-to-leave-salary-and-working-hours-explained-7375557.html); [People Matters](https://www.peoplematters.in/news/strategic-hr/leave-carry-forward-and-encashment-rules-set-for-nationwide-standardisation-49221)
- Fixed-term employees get pro-rata gratuity under the Codes — [Bhatt & Joshi](https://bhattandjoshiassociates.com/the-labour-codes-2026-what-actually-changed-for-employers/)

### Inferences
- Guardrails: the bot should never collect Aadhaar numbers, OTPs or UAN passwords, and should deep-link to the EPFO portal. It can check from HRIS whether the UAN is activated and KYC-seeded, and nudge the employee. Clarify that PPF is a personal savings scheme (bank or post office) and is not linked to EPF nomination. (The PPF distinction is general knowledge, not cited here.)
- Statutory answers need a jurisdiction-aware policy layer (entity, state, worker vs non-worker classification), because Shops and Establishments Acts and Code rules vary by state. The agent's knowledge base should be the company's own leave policy, versioned, with legal review. Statutory claims (overtime at twice the wage rate, F&F within 2 working days, 180-day leave eligibility) should be included only if HR or legal confirms them.

### Gaps
- Primary MoLE notifications and gazette texts were not fetched. The overtime rate, wage-payment timelines on separation, and the 1-year fixed-term gratuity threshold could not be verified in this pass.
- No authoritative tracker of state-wise Code rules as of Nov 2026 was found.

---

## 5. POSH Act: Internal Committee escalation and what a bot may / may not do

### Takeaway
Under the POSH Act, complaints go to the Internal Committee in writing within three months (extendable by three more), and Section 16 bars disclosure of identities and proceedings. A bot may explain the process, provide IC contacts and help the complainant reach the IC through a confidential channel. It must not investigate, conciliate, assess merit, or store or share details beyond the IC.

### Cited Findings
- Section 9: a written complaint to the IC is due within 3 months of the incident (or of the last incident in a series). The IC may extend this by up to 3 months, for reasons recorded in writing — [SS Rana](https://ssrana.in/posh-law/ufaq/is-there-any-specific-time-frame-for-filing-a-posh-complaint/); [Mondaq POSH FAQs](https://www.mondaq.com/india/discrimination-disability-sexual-harassment/1401310/navigating-the-posh-act-2013-faqs-explained)
- Section 16: identities of the complainant, respondent and witnesses, the complaint contents, inquiry proceedings and recommendations must not be published, communicated or made known. This overrides the RTI Act — [ILMS Academy](https://www.ilms.academy/blog/confidentiality-in-posh-complaints-explained-legal-duties-penalties-best-practices); [Rainmaker IC responsibilities](https://rainmaker.co.in/internal-committee-responsibilities-posh-act/)
- Employer guides describe the IC as the sole body to receive and inquire into complaints — [RestTheCase employer guide](https://restthecase.com/knowledge-bank/business-and-compliance/employers-guide-to-handling-posh-complaints-in-india)
- No sources specifically addressed AI chatbots and POSH — [search result: none found]

### Inferences
- **Bot may:** detect potential POSH content (keyword plus classifier, tuned for high recall), stop LLM generation, and show a fixed script. The script would say what POSH is, that complaints go to the IC in writing within 3 months, list IC members' contact details, give the option to send a written complaint directly to the IC's confidential mailbox or form, and point to external options (Local Committee, police for criminal offences).
- **Bot must not:** ask for incident details in the general chat, summarise or forward to managers or HRBPs, judge severity, suggest conciliation, log content into general analytics or LLM training logs, or send the conversation to a third-party LLM without a DPA. Store only a minimal routing record, with access restricted to IC members.
- The same "hard handoff" pattern applies to data-breach incidents (route to the DPO or security team, aligned with DPDP Act breach-notification obligations). Performance, succession, mobility and workforce planning questions get informational answers only, and decisions stay with humans.

### Gaps
- No regulatory guidance specific to AI or chatbot handling of POSH complaints was found. The design above is inference.
- DPDP Act 2023 / DPDP Rules 2025 breach-notification timelines were not researched in this pass.
