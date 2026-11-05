# Safe, Lawful Per-Employee Analytics for an AI HR Product (India-first, then EU/US) — as of Nov 2026

> Not legal advice. Several items below are fast-moving (DPDP timeline compression, EU Digital Omnibus formal adoption, Colorado AI Act). Items marked "[primary text, not re-fetched this session]" cite the statutory text from background knowledge with a link to the official/standard text; verify before relying on them.

## 1. India — DPDP Act 2023 + DPDP Rules 2025: status, employment basis, duties, penalties

### Takeaway
The DPDP Rules were notified 13 Nov 2025 with a three-phase rollout; most substantive obligations (notice, consent, legitimate uses, security, breach notification, SDF duties, penalties) bite on 13 May 2027 unless MeitY's proposed compression to 13 Nov 2026 is notified (proposed in early 2026; no confirmed amendment found). Employers can rely on Section 7(i) "purposes of employment" instead of consent, but commentators disagree on how far that stretches — predictive/behavioural analytics (attrition scoring, sentiment, burnout inference) is the contested edge, so the product should not assume 7(i) covers everything.

### Cited Findings
**Status and phased timeline**
- Phase 1 (13 Nov 2025): Data Protection Board and initial provisions — Sections 1(2), 2, 18–26, 35, 38–43, 44(1),(3); Rules 1, 2, 17–21. — [Taxmann analysis](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)
- Phase 2 (13 Nov 2026): Consent Manager provisions — Section 6(9), 27(1)(d), Rule 4. — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/); [AZB & Partners (phased rollout note)](https://www.azbpartners.com/bank/indias-digital-personal-data-protection-act-phased-rollout-and-key-compliance-milestones/)
- Phase 3 (13 May 2027): Sections 3–17 (incl. notice, consent, legitimate uses, fiduciary obligations, children, SDFs) plus Board enforcement/penalties; Rules 3, 5–16, 22, 23. — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/); [StartupTalky](https://startuptalky.com/dpdp-act-timeline-phases-2026-2027-explained/)
- Conflict: one secondary source lists Sections 7–17 among provisions already in force; most sources (and the Rule 5 linkage) place them in the May 2027 phase. — [search-result summaries incl. Trilegal PDF](https://trilegal.com/wp-content/uploads/2025/11/DPDPA.pdf), [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)
- MeitY held stakeholder consultations 22–23 Jan 2026 proposing to cut the 18-month window to 12 months (deadline 13 Nov 2026); reports differ on whether it covers all fiduciaries or mainly SDFs; Rule 8(3) retention possibly cut to 3 months. As of an April 2026 report this was still a plan; no notified amendment found. — [SS Rana / Mondaq](https://www.mondaq.com/india/data-protection/1773554/meity-plans-to-cut-short-dpdp-compliance-timeline-and-notify-cross-border-restrictions-for-sdfs); [Storyboard18](https://www.storyboard18.com/amp/digital/meity-seeks-industry-views-on-fast-tracking-dpdp-act-rollout-proposes-12-month-compliance-timeline-88332.htm); [KNN India](https://knnindia.co.in/news/newsdetails/sectors/dpdp-act-compliance-timeline-for-major-data-fiduciaries-may-be-cut-from-18-to-12-months)

**Consent vs legitimate use for employment**
- Section 7(i) permits processing without consent "for the purposes of employment or those related to safeguarding the employer from loss or liability" (e.g., corporate espionage, confidentiality, IP) or provision of a service/benefit sought by the employee. — [KSK](https://ksandk.com/data-protection-and-data-privacy/can-employers-monitor-employees-dpdp-act/); [factoHR guide](https://factohr.com/dpdp-act-2023/); statute: [MeitY DPDP Act text](https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf) [primary text, not re-fetched this session]
- KSK (2026): Act does not prohibit monitoring, but 7(i) should not be read as permitting unrestricted surveillance; scope/intrusiveness matter. — [KSK](https://ksandk.com/data-protection-and-data-privacy/can-employers-monitor-employees-dpdp-act/)
- Narrow reading (FES, union-oriented): surveillance assessing employee efficiency falls outside 7(i) and needs consent. — [FES](https://collections.fes.de/publikationen/content/pagetext/1990055)
- LiveLaw opinion: blanket employment surveillance clauses are void under DPDP since processing must rest on consent or a listed legitimate use. — [LiveLaw](https://www.livelaw.in/articles/employment-surveillance-clauses-void-dpdp-regime-539957)
- SansaLegal: 7(i) processing does not trigger Section 5 consent-notice, but lawful-purpose requirement still applies. — [SansaLegal](https://www.sansalegal.com/post/how-to-rely-on-the-employment-legitimate-use-under-section-7-i-of-the-dpdp-act)
- Note: consent under DPDP must be free, specific, informed, unconditional and unambiguous; in an employment power imbalance, consent is a weak basis for invasive analytics (inference). See also [Bar & Bench (NovoJuris)](https://www.barandbench.com/view-point/navigating-legitimate-use-exemption-employee-data-digital-personal-data-protection-act-2023); [Mondaq: is consent required for employee data](https://www.mondaq.com/india/data-protection/1755320/is-consent-required-to-process-employees-personal-data-under-the-dpdp-act)

**Fiduciary/processor duties, security, breach, retention**
- Data Fiduciary remains responsible even when a processor processes data (S. 8(1)); processor contracts must include reasonable security safeguards (Rule 6(f)). — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)
- Rule 6 security: encryption/obfuscation/masking/virtual tokens, access control, logging & monitoring, backups; logs and associated personal data retained at least one year. — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)
- Breach: inform affected Data Principals and the Board without delay; detailed report to the Board within 72 hours of becoming aware. — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)
- Erasure when purpose no longer served/consent withdrawn unless legal retention applies; 48-hour pre-erasure notice (Third Schedule entity classes). — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)

**Significant Data Fiduciary (SDF)**
- Rule 13: annual DPIA and audit, significant observations reported to Board; India-based DPO reporting to board; independent data auditor; due diligence that algorithmic software does not pose risks to Data Principals' rights; government may require specified data to stay in India (Rule 13(4)). — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)
- MeitY also reportedly considering notifying cross-border restrictions for SDFs. — [SS Rana / Mondaq](https://www.mondaq.com/india/data-protection/1773554/meity-plans-to-cut-short-dpdp-compliance-timeline-and-notify-cross-border-restrictions-for-sdfs)

**Cross-border**
- Rule 15 / S.16: transfers outside India generally permitted unless restricted by Central Government order (negative-list model). — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)

**Penalties (Schedule)**
- Up to ₹250 crore for failing reasonable security safeguards (S.8(5)); up to ₹200 crore for failing breach notification (S.8(6)); up to ₹200 crore for children's-data breaches (S.9); up to ₹150 crore for SDF obligations (S.10). — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)

### Inferences
- Role split: the HR SaaS vendor will typically be a **Data Processor**; the employer customer is the **Data Fiduciary**. The vendor's DPA must flow down Rule 6 safeguards, 72-hour breach support, deletion on purpose-end, and log retention ≥1 year. Vendor's own product-improvement/model-training use of employee data would make it a fiduciary for that purpose — avoid or obtain a separate basis.
- Routine HR analytics (headcount, leave balances, training completion, payroll accuracy) sits comfortably within 7(i). Individual-level *predictive/inferred* scores (attrition risk, burnout, sentiment of HR queries) are the contested zone; safest defaults: aggregate-only, or individual scores visible only to the employee, with a notice even if 7(i) arguably doesn't require one.
- Children's data (S.9) is largely irrelevant for workforce products, except interns/apprentices under 18 — add an age flag to exclude minors from analytics.
- Large customers (banks, IT services) may be designated SDFs; they will push algorithmic due-diligence and DPIA obligations onto the vendor contractually. Ship a DPIA pack and algorithm risk assessment as sales enablement.
- Plan for the 13 Nov 2026 compression scenario even though it is unconfirmed.

### Gaps
- No primary MeitY/Gazette confirmation found of whether the 12-month compression was notified (as of the latest found reports, April 2026). Check meity.gov.in / egazette.
- Couldn't extract text from the ELP employee-data paper (PDF); AZB page failed to load. No Cyril Amarchand / Trilegal employment-specific analysis read in full.
- No DPB guidance or case law yet on the scope of "purposes of employment" for predictive analytics.
- SDF designation criteria/notifications for specific companies not found.

## 2. EU — AI Act (high-risk employment AI, emotion recognition ban, Digital Omnibus delay) and GDPR Art. 22

### Takeaway
Employment AI that monitors/evaluates worker performance or behaviour, or informs promotion/termination/task allocation, is Annex III high-risk; the Digital Omnibus (political deal 7 May 2026) pushed Annex III obligations from 2 Aug 2026 to 2 Dec 2027. The Article 5(1)(f) ban on emotion recognition in the workplace has applied since 2 Feb 2025, and per Commission guidance covers inferring emotions from biometrics (face, voice) — text-based sentiment of HR queries is not biometric, but burnout/stress inference from voice/video would be prohibited.

### Cited Findings
- Annex III point 4: (a) recruitment/selection; (b) AI "intended to be used to make decisions affecting terms of work-related relationships, the promotion or termination ..., to allocate tasks based on individual behaviour or personal traits or characteristics or to monitor and evaluate the performance and behaviour of persons in such relationships." — [Annex III text](https://artificialintelligenceact.eu/annex/3/) [primary text, not re-fetched this session]; scope commentary: [Mondaq — what the AI Act means for employers](https://www.mondaq.com/new-technology/1499674/what-does-the-ai-act-mean-for-employers)
- Deployer (employer) duties under Art. 26: use per instructions, human oversight, monitor operation, keep logs ≥6 months, and **before** use at the workplace inform workers' representatives and affected workers. — [Art. 26 text](https://artificialintelligenceact.eu/article/26/); [Steptoe deployer obligations](https://www.steptoe.com/a/web/g66ihcpdaFJgbX9yS3r3FN/eu-ai-act-decoded-issue-6-obligations-for-deployers-of-high-risk-ai-final.pdf)
- Provider obligations (the SaaS vendor) for high-risk systems include risk management, data governance, technical documentation, logging, transparency/instructions, human oversight design, accuracy/robustness, QMS, conformity assessment, registration (Arts 9–17, 43, 49). — [AI Act text](https://artificialintelligenceact.eu/article/16/) [primary text, not re-fetched this session]
- Digital Omnibus: provisional agreement 7 May 2026; Annex III stand-alone high-risk obligations delayed 16 months to 2 Dec 2027; Annex I product-embedded to 2 Aug 2028; fixed dates instead of standards-linked trigger. — [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement); [Sidley](https://datamatters.sidley.com/?p=8999); [White & Case](https://www.whitecase.com/insight/eu-agrees-digital-omnibus-deal-simplify-ai-rules); [Taylor Wessing](https://taylorwessing.com/en/insights-and-events/insights/2026/05/the-eu-digital-omnibus-on-ai-what-the-political-deal-means)
- One source reports Council final approval 29 June 2026 (single source, unverified). — [SecurePrivacy](https://secureprivacy.ai/blog/eu-ai-act-digital-omnibus-the-new-high-risk-ai-deadlines-after-council-approval)
- Art. 5(1)(f) bans AI inferring emotions of natural persons in the workplace and education, except for medical or safety reasons (applies since 2 Feb 2025). Commission guidelines (C(2025) 884, non-binding) give prohibited examples: supermarket cameras tracking employee happiness; call-centre webcams/voice recognition tracking employee emotions. Covers recruitment/probation; "workplace" read broadly (incl. remote). — [Lewis Silkin](https://www.lewissilkin.com/insights/2025/02/17/understanding-the-eu-ai-acts-prohibited-practices-key-workplace-and-advertising-102k011); [FPF](https://fpf.org/blog/red-lines-under-eu-); [Wolters Kluwer Global Workplace Law blog](https://legalblogs.wolterskluwer.com/global-workplace-law-and-policy/the-prohibition-of-ai-emotion-recognition-technologies-in-the-workplace-under-the-ai-act/)
- Analysis of guidelines: a system to detect burnout or depression at work would not fall within the medical/safety exception; contrasting commentary suggests stress detection tied directly to safety in e.g. factories could qualify — fact-dependent. — [AIGL analysis](https://www.aigl.blog/ai-act-guidelines-on-prohibited-artificial-intelligence-ai-practices-an-analysis-for-the-emotion-recognition-field/); contrasted by [HCAMag](https://www.hcamag.com/ca/specialization/employment-law/eus-new-ai-act-restricts-emotion-recognition-systems-in-workplaces/524292)
- The ban is tied to emotion recognition systems defined as based on biometric data; text sentiment analysis is not biometric (per Art. 3(39) definition). — [Art. 3 definitions](https://artificialintelligenceact.eu/article/3/) [primary text, not re-fetched this session]
- GDPR Art. 22: right not to be subject to a decision based solely on automated processing, including profiling, producing legal or similarly significant effects; Art. 88 allows Member State employment-specific rules (e.g., German/Italian/Spanish monitoring regimes, works council co-determination); Art. 35 DPIA required for systematic evaluation/profiling. — [GDPR Art. 22](https://gdpr-info.eu/art-22-gdpr/); [Art. 88](https://gdpr-info.eu/art-88-gdpr/) [primary text, not re-fetched this session]
- National labour consultation regimes (Italy, Spain) interact with Art. 26 worker information duty. — [remoteworkeurope](https://remoteworkeurope.eu/insights/eu-ai-act-remote-work-monitoring)

### Inferences
- If the product produces individual attrition/burnout/performance scores visible to managers in the EU, it is very likely Annex III 4(b) high-risk → full provider obligations by 2 Dec 2027 (assuming Omnibus formally adopted). Aggregated, team-level insights with k-thresholds and no individual decisioning plausibly fall outside "evaluate the performance and behaviour of persons" — but the Art. 6(3) "no significant risk" carve-out does not apply where a system profiles natural persons, so individual profiling = high-risk.
- Hard product rule: never infer emotion/stress/burnout from voice, video, keystroke-face-biometrics for EU workers. Text sentiment of HR queries is not banned but is still profiling under GDPR, so keep it aggregate.
- Individual-level adverse actions must have meaningful human review to avoid Art. 22.

### Gaps
- Did not fetch the Commission guidelines PDF directly; final adopted Omnibus text in OJ not confirmed.
- No EDPB-specific 2025–26 guidance on people analytics found in this pass.

## 3. US — NYC LL144, Colorado AI Act, Illinois HB 3773, litigation

### Takeaway
US rules focus on discrimination in employment decisions rather than privacy: NYC requires annual independent bias audits (impact ratios) for automated employment decision tools in hiring/promotion; Illinois (effective 1 Jan 2026) bans discriminatory AI use and zip-code proxies across the employment lifecycle and requires notice; Colorado's law was delayed to 30 June 2026 and then stayed by a federal court in April 2026 with a replacement bill pending. Mobley v. Workday shows vendors themselves can face disparate-impact liability.

### Cited Findings
- NYC LL144: bias audits compute impact ratio = group selection rate / most-selected group rate; <0.80 (four-fifths) is a red flag but not per se violation; auditor may exclude categories <2% of data; law requires no specific remediation. — [Holistic AI](https://www.holisticai.com/blog/bias-audit-impact-ratio-small-sample); [Deloitte](https://www.deloitte.com/us/en/pages/audit/articles/nyc-local-law-144-algorithmic-bias.html); critique of 2% rule: [arXiv 2501.10371](https://br.arxiv.org/pdf/2501.10371)
- NY State Comptroller audit (Dec 2025) of DCWP enforcement (Jul 2023–Jun 2025) found weak enforcement — no routine monitoring of audit compliance, rare enforcement actions, no remediation follow-up. — [NY OSC audit](https://www.osc.ny.gov/state-agencies/audits/2025/12/02/enforcement-local-law-144-automated-employment-decision-tools); [DCI summary](https://blog.dciconsult.com/recommended-changes-to-local-law-144)
- Illinois HB 3773 (amends Illinois Human Rights Act, signed 9 Aug 2024, effective 1 Jan 2026): covers recruitment, hiring, promotion, training, discharge, discipline, terms/conditions; bans AI with discriminatory effect and use of zip codes as proxy; requires notice to employees (IDHR rules on notice — finalization status unclear). — [Seyfarth](https://www.seyfarth.com/news-insights/legal-update-new-illinois-ai-law-requires-employee-notice-affirms-existing-employer-nondiscrimination-duties.html); [Morgan Lewis](https://morganlewis.com/pubs/2024/09/illinois-passes-new-law-to-address-ai-in-the-workplace)
- Colorado AI Act (SB24-205): delayed from 1 Feb 2026 to 30 June 2026 (SB25B-004); federal magistrate stayed enforcement 27 Apr 2026 in xAI litigation; SB 26-189 introduced 1 May 2026 as replacement. Covers employment decisions incl. hiring, promotion, compensation, performance management. — [Fisher Phillips](https://www.fisherphillips.com/en/news-insights/colorado-delays-ai-law-to-june-2026.html); [Proskauer](https://www.proskauer.com/blog/major-developments-put-colorados-ai-law-on-ice-ahead-of-implementation)
- Mobley v. Workday: May 2025 conditional certification of ADEA collective (applicants 40+) on theory that Workday's AI recommendations caused disparate impact; case ongoing as of April 2026. — [Fisher Phillips](https://www.fisherphillips.com/en/news-insights/discrimination-lawsuit-over-workdays-ai-hiring-tools-can-proceed-as-class-action-6-things); [Maynard Nexsen](https://www.maynardnexsen.com/publication-emerging-liability-for-ai-driven-hiring-tools-key-developments-in-mobley-v-workday-inc); [Clearinghouse](https://clearinghouse.net/case/44074/)

### Inferences
- Attrition scores that feed promotion, compensation, or "who to retain/invest in" decisions are within Illinois' and (if revived) Colorado's scope; build impact-ratio reporting into the product regardless of jurisdiction.
- Vendor liability risk (Mobley "agent" theory) means the vendor cannot rely on "the customer decides."

### Gaps
- Outcome of SB 26-189 and xAI stay after May 2026 not found; IDHR final notice rules not confirmed; California CCPA ADMT regulations and California FEHA AI regs (effective Oct 2025) not researched in this pass.

## 4. Evidence on accuracy, harms, and fairness auditing

### Takeaway
Independent evidence on the real-world accuracy of individual attrition or burnout scores is thin; vendor accuracy claims are relative ("x times better than guessing") and inconsistent, and attrition is a rare event so accuracy flatters. Main documented harms: scores creating new, unseen information about people, self-fulfilling prophecies (withholding investment from "flight risks"), and group bias (age, gender).

### Cited Findings
- Visier docs: resignation-risk predictions "up to 17x more accurate than guesswork", average ~5x across clients; older Visier material said up to 8x (10x for top-100). Visier warns about data leakage from future/backdated data. — [Visier docs: strengths and limitations](https://docs.visier.com/developer/Visier%20People%20Metrics/predictions/predictions%20strengths%20and%20limitations.htm); [TLNT](https://tlnt.com/tech-vendors-can-do-a-better-job-predicting-whos-a-flight-risk-than-you)
- Practitioner guidance: because leaving is rare, accuracy flatters; a score is new information the employee didn't give and may not know exists; scores should not reduce access to promotion/raises (self-fulfilling). — [Rework](https://resources.rework.com/libraries/ai-for-hr/ai-attrition-prediction)
- Age bias in attrition models and adversarial debiasing, measuring group fairness by 5-year age bands. — [SMU Data Science Review 2020](https://scholar.smu.edu/datasciencereview/vol3/iss2/11)
- AutoML comparison found one tool over-predicts attrition for women. — [arXiv 2608.07477](https://arxiv.org/pdf/2608.07477)
- Fairness-performance tension in feature selection (equal opportunity difference), largely on synthetic IBM HR dataset. — [WJCM](https://wjcm.uowasit.edu.iq/index.php/wjcm/article/view/404)
- Fairness audit metric used in law: impact ratio / four-fifths rule (see Section 3). — [Holistic AI](https://www.holisticai.com/blog/bias-audit-impact-ratio-small-sample)

### Inferences
- Report precision/recall/calibration at the operating threshold and base rate, not "x times better than random"; publish per-group false-positive rates (equalized odds) plus impact ratios; small groups → wide confidence intervals (aggregate thresholds also help statistically).
- Burnout scoring has even weaker validity than attrition (no clean ground-truth label); treat as wellbeing signal at team level only.

### Gaps
- No large independent peer-reviewed audit of deployed commercial attrition/burnout models found; much academic work uses the synthetic IBM dataset.

## 5. Design safeguards and what responsible vendors do

### Takeaway
Leading vendors converge on: aggregation with minimum group sizes (typically ≥5, stricter ≥10 for manager views), differential-privacy noise for manager/leader dashboards, individual data visible only to the individual, protections against filter-differencing, and customer-configured confidentiality. These map directly onto DPDP purpose limitation/security and EU AI Act/GDPR minimisation.

### Cited Findings
- Microsoft Viva Insights: default minimum group size 5; admins cannot set lower than 5 (applies to charts using HR data). — [Microsoft Learn — privacy considerations](https://learn.microsoft.com/en-us/viva/insights/privacy/privacy-considerations); [privacy settings](https://learn.microsoft.com/en-us/viva/insights/advanced/setup-maint/privacy-settings)
- Viva manager insights threshold reportedly 10 (Microsoft staff forum post; not confirmed in current docs). — [Tech Community](https://techcommunity.microsoft.com/t5/manager-and-leader-insights/minimum-group-size/m-p/3861932)
- Viva applies differential privacy (first in Manager and leader insights), "introducing slight variations to the data"; states no manager can conclude with confidence anything specific about any individual (legacy Workplace Analytics doc). Org insights combine minimum group sizes, DP, and masked distributions. — [Microsoft Learn — differential privacy](https://learn.microsoft.com/en-us/viva/insights/Privacy/differential-privacy); [Org insights](https://learn.microsoft.com/sr-latn-rs/viva/insights/org-team-insights/org-insights)
- Culture Amp: "reporting group minimum" — can't filter to groups below the minimum (example uses 5); "Strong" indirect-identification protection hides the next-smallest group to block subtraction attacks; separate (often higher) comments minimum. — [Culture Amp — confidentiality protections](https://support.cultureamp.com/en/articles/7048386-confidentiality-protections-in-reporting); [report filters](https://support.cultureamp.com/en/articles/7048607-report-filters)
- inFeedo Amber: trust statement displayed at start of each conversation; offers confidential (identifiable for follow-up) vs anonymous modes; privacy policy puts classification/consent/access of custom fields on the customer. — [IndiaAI](https://indiaai.gov.in/article/this-ai-based-startup-won-t-let-a-company-lose-their-top-employees-play-safe); [Evalueserve case study](https://www.casestudies.com/company/infeedo/case-study/how-bhavana-kandari-vp-hr-at-evalueserve-built-employee-first-culture-with-an-engagement-chatbot); [inFeedo privacy policy](https://www.infeedo.ai/privacy-policy)
- Visier: says employees deserve to understand how their data is used in predictive models. — [Visier blog](https://www.visier.com/blog/predictive-hr-analytics/)
- Legal anchors: DPDP Rule 6 (access controls, logging, masking), Rule 13 algorithmic due diligence and DPIA for SDFs — [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/); AI Act Art. 26 worker notice + 6-month logs — [Art. 26](https://artificialintelligenceact.eu/article/26/)

### Inferences (recommended product safeguards; synthesis, not sourced claims)
- **Tiering of analytics:**
  - Green (ship, 7(i)/legitimate interest): leave balances & patterns at team level, training completion (individual completion is a normal HR record), headcount/turnover reporting, aggregate HR-query topics.
  - Amber (aggregate-only, k≥5 default, ≥10 for manager views, DP noise, no drill-down): engagement, sentiment of HR queries, burnout/wellbeing indicators, attrition risk by segment.
  - Red (don't build / EU-prohibited or high-risk without full conformity): individual attrition/burnout scores shown to managers; emotion inference from voice/video/webcam; keystroke/screen productivity scoring; using leave patterns (medical, maternity) or protected traits/proxies (age, gender, zip/pincode, caste, religion) as model features; automated adverse decisions.
- Minimum group thresholds enforced server-side, with complementary suppression against filter-differencing; separate higher threshold for free-text.
- Differential privacy (Laplace/Gaussian noise with a per-tenant privacy budget) on manager/leader dashboards.
- "My data" view: employee sees every data point and any score about them, the purpose, and can contest/correct (supports DPDP S.11–13 rights to access/correction/grievance).
- Purpose registry: each analytic tied to a declared purpose; block reuse (e.g., wellbeing data for performance). Retention: raw query text short-lived (e.g., 90 days), aggregates retained; delete on exit subject to legal holds; keep ≥1-year access logs (Rule 6).
- RBAC/ABAC: HRBP vs manager vs exec; managers never see individual-level inferred scores; break-glass with audit trail.
- Human-in-the-loop: no automated adverse decisions; scores framed as "prompts for supportive conversation," not ratings.
- Explainability & documentation: model cards (data, metrics at base rate, per-group FPR, impact ratios, limitations), annual bias audit (NYC-style impact ratios plus equalized odds), DPIA template covering necessity/proportionality, worker representative consultation (EU), and Rule 13 algorithmic due-diligence pack for SDF customers.
- Opt-in for sensitive modules and a customer-side "works council/employee notice" kit.

### Gaps
- Workday-specific privacy/aggregation controls for Peakon/Workday People Analytics not researched in this pass; Visier aggregation thresholds not found.
- No standard published k-value consensus beyond the vendor norm of 5 (sometimes 3–4 allowed by e.g. 15Five; 10 for Viva manager insights).
