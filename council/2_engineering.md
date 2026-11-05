# Council seat 2: AI/agent systems engineering review

## 1. Long-context cache + rules engine + typed tools: right idea, wrong budget

The split is correct: the rules engine handles numbers, typed tools handle live state, and the LLM only explains. But the **free-product constraint changes the policy-Q&A engine.** Putting a 40k-token handbook into every call only works with paid prompt caching. Free tiers break it. Groq's free tier has tokens-per-minute caps below one stuffed call. Gemini's free tier allows content to be used for training, which is a DPDP problem for HR data. Local 7B models on CPU take minutes to prefill 40k tokens. **Make retrieval the default:** clause-level chunks, BM25 plus BGE-M3 fused with RRF, hard SQL filters for version and scope, and top-8 clauses of about 3k tokens of context. Keep full-handbook stuffing only for tenants that bring their own paid key (BYOK).

Failure modes and fixes:
- **Scanned PDFs / Hindi:** Tesseract `hin` OCR is poor. Mark OCR'd clauses `needs_review`, never cite unreviewed text, and let the admin paste corrected text.
- **Tables (leave matrices):** parse them to structured rows and encode them as **rules**, not prose. Models misread the columns of a flattened table.
- **Rule/text drift:** for each rule, auto-generate 5 questions. Compare the LLM's answer from the text with the rules engine's output, and send any disagreement to the admin queue. Hand-authoring rules per tenant is a hidden operations cost for a solo dev.
- **Version change:** each conversation turn resolves `policy_version` by effective date at query time and logs it. Publishing a new version is atomic (status flip); nothing is invalidated in place.
- **Per-employee filtering vs cache (BYOK path):** order the prefix as tenant-common clauses (breakpoint 1), then scope addenda (breakpoint 2). Never put employee data in the prefix. At about 400 conversations/month per tenant, 5-minute caches are mostly cold anyway.
- **Contract clash:** native Claude citations are incompatible with structured-output mode. Build `{answer, citations, computed_values, escalate}` **server-side** from citation blocks and tool results. With free models, require `[clause_id]` markers and validate them against the retrieved set; a turn with an unknown id gets regenerated once, then abstains.

## 2. Orchestration: a plain tool-use loop with a provider-agnostic adapter

Free and BYOK means multiple providers (Groq, Gemini, OpenRouter, Ollama, Claude), so the code cannot be locked to one SDK. **Pick Pydantic AI** (multi-provider, typed tool schemas, cheap to test), or a ~200-line hand loop over an OpenAI-compatible client. Rejected options:
- **LangGraph** is too much machinery for single-step turns.
- **The Claude Agent SDK** is the Claude Code harness, with filesystem and bash tools, which is the wrong attack surface and single-vendor.

Durable workflows (Phase 2) belong in a Postgres `workflow_runs` table plus a `SKIP LOCKED` job queue, not in agent framework state.

**Buttons vs. LLM:** a **deterministic finite-state machine owns the conversation.** Every menu, form and confirm step is a state. Free text goes through four stages in order:
1. A keyword and regex sensitive-topic backstop, which routes to a fixed script and never calls the LLM.
2. A small intent classifier that returns `{intent, slots}`.
3. The FSM, which jumps to that flow's entry state with the slots prefilled.
4. Policy QA, which handles only the `policy_question` intent.

The LLM can never move the FSM into a write state. Writes need a button tap on a server-rendered diff. Button flows cost zero tokens, which matters on a free budget.

## 3. Eval harness for one person

- **Rules engine:** pytest plus Hypothesis property tests (no negative balances, carry-forward ≤ cap, sandwich rule is symmetric). Gate: 100%.
- **Tools/connectors:** contract tests against recorded Keka/greytHR fixtures (VCR-style), plus authz tests confirming that `employee_id` from the model is ignored. Gate: 100%.
- **Golden set:** YAML with `q, lang, employee_fixture, as_of_date, expected_clause_ids, expected_numbers, expect_escalate, must_not_contain`. Start with 60 per pilot plus 100 shared traps (wrong version, wrong state, unanswerable, salary probing, POSH phrasings in Hinglish).
- **Deterministic grading first:**

| Check | Gate |
|---|---|
| Clause recall | ≥ 95% |
| Numeric exact match | 100% |
| Wrong-version answers | 0 |
| Abstention recall on unanswerable questions | ≥ 90% |
| False abstention | ≤ 10% |
| Sensitive-routing recall | 100% |
| Intent accuracy | ≥ 95% |

  Use an LLM judge only for faithfulness, and spot-audit it by hand. Skip RAGAS scores as gates.
- **CI:** GitHub Actions (free) runs the unit, contract and red-team suites on every push (promptfoo). The golden set runs nightly and on any change to prompt, model or retriever. Store results in a `eval_runs` table and fail on regression against the last green run.

## 4. Cost and latency at a near-zero budget

Assumptions: 200 employees, about 2 conversations per employee per month, so ~400 conversations; 60% are pure button flows (no LLM); ~3 LLM calls per free-text conversation, at 3–4k tokens each with retrieval.

| Option | Per conversation | Per 200-employee tenant per month | Notes |
|---|---|---|---|
| Groq / OpenRouter free models | $0 | $0 | Rate limits and model churn; not for production HR data unless the terms are read and accepted |
| Gemini free tier | $0 | $0 | **Data may be used for training.** Use it for dev and evals only, never tenant data |
| Local Qwen2.5-7B / Llama-3.1-8B (Ollama, Oracle Always-Free ARM, 24 GB) | ~$0 | $0 | About 5–10 tok/s on CPU, so 10–25 s per answer. Acceptable on async WhatsApp/Telegram, poor on web |
| **BYOK (recommended default for paid-quality answers)** | ~$0.003 (Claude Haiku 5.5, about $0.10/M in, assumed) | ≈ $0.50, paid by the tenant | Tenant key, tenant bill. Product stays free |

- **Routing:** button flows → FSM (0 tokens). Classifier → local small model or BYOK Haiku. Policy QA → BYOK model if present, else local 7B with a strict abstain threshold.
- **Embeddings:** BGE-M3 runs locally at ingest only (CPU is fine).
- **Infra:**
  - Oracle Always Free (always-on, no sleep) or Fly. Avoid Render free: its 30–60 s cold starts break webhook acknowledgements.
  - Postgres: Neon or Supabase free with pgvector. Supabase pauses after a week of inactivity, so ping it.
- **Channels:** Telegram, Slack and Teams bots are free. WhatsApp Cloud API includes only 1,000 free service messages per number per month, and utility templates are charged, so proactive nudges cost money. Field staff use WhatsApp, so make WhatsApp **tenant-funded or opt-in**.
- **Safety nets on free open-source tools:**

| Safety net | Free option |
|---|---|
| Row-level security | Postgres RLS |
| PII redaction | Presidio (MIT), with custom UAN/IFSC recognizers |
| Prompt-injection filter | Prompt Guard 2 22M, on CPU |
| Content safety | Llama Guard 3 1B, on CPU |
| Red-team suite | promptfoo |
| Audit / tracing | Langfuse self-hosted (v3 needs ClickHouse, Redis and S3, too heavy for a free tier), so use an append-only Postgres `audit_events` table plus Arize Phoenix if traces are needed |

  **What you lose:** India data residency (Bedrock Mumbai isn't free), and that weakens the DPDP pitch.

## 5. Minimal backend layout (FastAPI + Postgres)

```
app/
  api/            # webhooks: telegram, slack, whatsapp, admin
  channels/       # adapters -> normalized InboundMessage / OutboundMessage
  fsm/            # flows as data (YAML) + engine
  agent/          # llm adapter, intent, policy_qa, citation validator
  retrieval/      # ingest, chunk-to-clause, bm25+bge, filters
  rules/          # schema, evaluators, compute_* (pure functions)
  connectors/     # keka, greythr (typed, re-authorize per call)
  safety/         # sensitive router, presidio, promptguard, output dlp
  workers/        # pg queue jobs: ingest, nudges
  db/             # sqlalchemy models, alembic, RLS policies
evals/            # golden/*.yaml, runner.py, redteam/
```

**Tables** (every table carries `tenant_id` under RLS):
- `tenants`, `employees` (hrms_id, phone, email, state, grade, emp_type), `channel_identities`, `consents`
- `policy_docs`, `policy_versions` (effective_from/to, status), `clauses` (version_id, clause_id, text, scope jsonb, overrides_clause_id, review_status, embedding, tsv), `rules` (json, source_clause_id, approved_by)
- `conversations` (fsm_state, policy_version_ids), `messages` (redacted text, short TTL)
- `tool_calls`, `pending_actions` (diff, idempotency_key, status), `tickets` (transcript ref, sla_due), `restricted_cases` (separate schema)
- `audit_events` (append-only), `eval_runs`

## 6. Biggest disagreement

**The scope is fantasy for one student, and the free mandate makes the plan's core technical bet the wrong default.** Ten weeks for two HRMS connectors, WhatsApp plus Slack, Hindi, all eight safety nets, a rules engine and India residency is a 6+ person-month build. And "long-context + caching" is a paid-API optimization. Cut the MVP to:
- one HRMS (Keka);
- Telegram or Slack plus a web widget, with WhatsApp tenant-funded;
- English and Hinglish;
- read-only Tier 1;
- retrieval plus rules plus FSM;
- BYOK or local LLM.

Prove accuracy on the golden set before building any write workflow.
