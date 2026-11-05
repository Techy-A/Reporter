# Retrieval and Reasoning Architecture for an HR Policy Q&A Agent (beyond naive RAG), as of Nov 2026

Scope: answering HR policy questions reliably (leave rules, WFH, PF nomination, notice-period buyout, combining sick and casual leave, overtime payout timelines, appraisal cycles) and recommending an MVP architecture plus later upgrades for a solo or small team in India.

Overall note on evidence: the strongest primary sources are the Anthropic Contextual Retrieval post, the CRAG, LightRAG, VersionRAG and LaRA papers, and the Hindi-BEIR paper. Much of the comparison material (agent frameworks, GraphRAG cost, eval thresholds) is practitioner blogs and should be treated as directional.

---

## 1. Retrieval approaches compared: naive RAG vs hybrid+rerank vs contextual retrieval vs agentic RAG vs GraphRAG/LightRAG vs long-context stuffing

### Takeaway
For a corpus the size of an HR handbook (usually 20-300 pages, well under 200k tokens per tenant), the evidence supports two options. One is long-context stuffing with prompt caching. The other is contextual retrieval: hybrid BM25 plus dense search, then a cross-encoder reranker, which cut retrieval failures 67% vs naive dense RAG in Anthropic's tests. GraphRAG and LightRAG target global "sensemaking" questions over large corpora. They are poorly matched to clause-level policy lookup and are not justified for an MVP. Agentic self-correction (CRAG/Self-RAG style) gives modest, model-dependent gains (about 3-7 points in recent reproductions).

### Cited Findings
**Contextual retrieval (Anthropic)**
- Baseline failure rate (1 − recall@20) was 5.7%. Contextual Embeddings cut failures 35% (to 3.7%). Contextual Embeddings + Contextual BM25 cut them 49% (to 2.9%). Adding reranking cut them 67% (to 1.9%). — [Anthropic, Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- Settings: chunks of a few hundred tokens; 50-100 tokens of LLM-generated context prepended per chunk; top-20 chunks to the model beat top-10 and top-5; rerank top-150 down to top-20 (Cohere reranker tested). — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- One-time cost to contextualize chunks with prompt caching: about $1.02 per million document tokens (Claude 3 Haiku, 800-token chunks, 8k-token docs). Contextual retrieval improved every embedding model tested; Gemini and Voyage embeddings performed best. — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- Anthropic's explicit guidance: knowledge bases under 200,000 tokens (about 500 pages) can go straight into the prompt without RAG, with prompt caching cutting latency more than 2x and cost by up to 90%. — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)

**Long-context vs RAG**
- LaRA (ICML 2025; 2,326 test cases, 11 LLMs) concludes there is "no silver bullet". The best choice depends on model capability, context length, task type and retrieval characteristics. — [LaRA, arXiv 2502.09977](https://arxiv.org/abs/2502.09977)
- Secondary summary of LaRA: at 32k context, long context averaged about 2.4% higher accuracy than RAG. At 128k, RAG averaged about 3.68% higher. RAG helps weaker models most (e.g. Mistral-Nemo-12B at 128k), while long context does better on reasoning and comparison tasks with strong models (GPT-4o). These numbers are unverified against the paper. — [themoonlight review of LaRA](https://themoonlight.io/review/lara-benchmarking-retrieval-augmented-generation-and-long-context-llms-no-silver-bullet-for-lc-or-rag-routing)
- Current Claude prompt-caching economics: cache writes cost 1.25x base input (5-minute TTL) or 2x (1-hour TTL). Cache reads cost 0.1x base input generally, and 0.05x for Claude Opus 5.5 and Sonnet 5.5. Minimum cacheable prompt is 512 tokens on current 5.x models. Up to 4 cache breakpoints. — [Claude docs, Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

**Agentic / self-corrective RAG**
- CRAG (latest paper version): +7.0% accuracy on PopQA over standard RAG with SelfRAG-LLaMA2-7b, and +4.4% with LLaMA2-hf-7b. Self-CRAG beat Self-RAG by 20.0% (LLaMA2-hf-7b) and 6.9% (SelfRAG-LLaMA2-7b). An earlier version reported a larger +19.0% on PopQA. — [CRAG, arXiv 2401.15884](https://arxiv.org/pdf/2401.15884)
- An independent 2026 reproduction (Phi-3-mini) got 54.4% on PopQA vs a 51.4% vanilla-RAG baseline, a gain of only about 3 points. — [Open-source reproduction of CRAG, arXiv 2603.16169](https://arxiv.org/pdf/2603.16169)

**GraphRAG / LightRAG**
- LightRAG (Guo et al., 2024) claims to beat Naive RAG, RQ-RAG, HyDE and GraphRAG on LLM-judged comprehensiveness, diversity and empowerment win rates over Agriculture, CS, Legal and Mix datasets. Reported example (secondary source): Legal comprehensiveness win rate of 83.6% vs 16.4% for naive RAG. It supports incremental index updates, whereas GraphRAG's community structure needs a full rebuild when data is added. — [LightRAG arXiv 2410.05779](https://arxiv.org/html/2410.05779v3); [emergentmind summary](https://www.emergentmind.com/topics/lightrag-framework)
- One summary notes GraphRAG did better than LightRAG on the Mix dataset, so the accuracy picture is mixed. — [lilys.ai summary](https://lilys.ai/notes/en/openai-agent-builder-20260208/lightrag-vs-graphrag-rag-efficiency)
- Indexing cost: commentary says full GraphRAG indexing cost about $33,000 for one dataset in early 2024, reduced roughly 1000x by mid-2025 (Medium, paywalled, unverified). The RAGU paper reports about $10,000 construction cost for MS-GraphRAG vs about $100 for its own system, with LightRAG in the cheaper class. — [Graph Praxis/Medium](https://medium.com/graph-praxis/the-graphrag-cost-cliff-how-33-000-became-33-in-eighteen-months-be1b0fbe37e4); [RAGU, arXiv 2607.11683](https://arxiv.org/pdf/2607.11683)
- On a versioned-document QA benchmark, GraphRAG scored only 64% vs 58% for naive RAG and 90% for a purpose-built version-aware method. Its indexing cost about 2.97M tokens and 5h12m, vs 186K tokens and 25 min for VersionRAG. — [VersionRAG, arXiv 2510.08109](https://arxiv.org/html/2510.08109v1)

### Inferences
- HR Q&A is mostly "find the specific clause and apply it", not global sensemaking. LightRAG's win rates are LLM-judged comprehensiveness and diversity, not exact-answer accuracy, so they say little about questions like "how many CL can I carry forward?". The graph approaches add cost and an ingestion pipeline without solving the real failure modes: wrong version, wrong location or grade variant, and arithmetic.
- A typical startup HR handbook (roughly 30-80k tokens) fits comfortably in context. For an MVP, "stuff the active, employee-filtered policy set with a cached prefix" is likely the simplest, highest-recall option. Each tenant's handbook becomes a cached prefix. Questions that combine clauses (e.g. sick + casual leave combined with sandwich rules) benefit because the model sees all relevant clauses at once.
- Switch to contextual hybrid retrieval when a tenant's corpus (handbook, circulars, location variants, FAQs, past HR tickets) exceeds about 100-150k tokens, or when per-query cost or latency becomes a problem.
- Agentic patterns worth adopting cheaply: query rewriting (Hinglish → canonical English HR terms), a retrieval-sufficiency check, and abstain or escalate when the check fails. Avoid elaborate multi-hop loops; the measured gains are small.

### Gaps
- No public benchmark specifically for HR or enterprise policy QA was found. The numbers above come from general QA (PopQA), Anthropic's internal codebase/fiction/arXiv mix, and technical docs.
- I could not verify the 6000x per-query token claim for LightRAG vs GraphRAG (blog source). It is excluded.
- I found no data on OP-RAG.

---

## 2. Policy-as-rules: extracting structured rules for deterministic computation

### Takeaway
Numeric and eligibility answers (leave accrual, carry-forward caps, notice-buyout amounts, overtime payout dates) should be computed by deterministic code from a structured rule representation, with the LLM handling interpretation and explanation. The research pattern (P2T, 2025) is: LLM extraction into a fixed JSON schema/DSL, with provenance to source spans, a judge-and-repair loop, solver-based conflict checks, and mandatory human review. Catala shows the formal end of this spectrum, prioritized default logic for "general rule plus exceptions", but is heavyweight for an MVP.

### Cited Findings
- P2T ("Executable Governance for AI", arXiv 2512.04408) uses an LLM constrained by few-shot examples and a fixed JSON schema to extract rules from policy text. Each rule keeps provenance (doc, citation, span_id). The pipeline adds deterministic checks, an LLM judge, a repair step and SMT conflict detection between rules. The authors say the compact DSL does not capture all nuances (e.g. temporal constraints) and stress human oversight. Code, DSL and prompts are open source. — [arXiv 2512.04408](https://arxiv.org/html/2512.04408v1)
- Practitioner pattern (AeroRule): Human Policy → LLM → JSON rules with CEL conditions → deterministic engine → traceable decision. This is a blog/project post and unverified. — [dev.to](https://dev.to/kanwaloswal/stop-asking-llms-does-this-pass-turn-policies-into-executable-rules-instead-16of)
- Catala (Inria / Microsoft Research, POPL/PACMPL 2021) is a DSL for translating statutory law into executable code. It is built on prioritized default logic, which suits general-case-plus-exceptions legal structure. It uses literate programming, with code interleaved with legal text, and was co-designed with lawyers. It was applied to French tax law and US IRC §121, where it found a bug in an official implementation. It compiles to general-purpose languages via an OCaml compiler. — [Microsoft Research](https://www.microsoft.com/en-us/research/publication/catala-a-programming-language-for-the-law/); [arXiv 2103.03198](https://arxiv.org/abs/2103.03198v2)
- NeMo Guardrails and Guardrails AI enforce developer-authored rules at runtime. This suits output constraints, not computing HR entitlements. — [P2T paper discussion via search summary](https://arxiv.org/html/2512.04408v1)

### Inferences
- A practical HR rule schema (JSON, validated with Pydantic or JSON Schema) could cover:
  - `leave_type` and `accrual` (rate and period, pro-rata on joining)
  - `carry_forward_cap`, `encashment`, `max_consecutive`
  - `combinable_with` / `cannot_club_with`, and `sandwich_rule`
  - `min_service_for_eligibility` and `notice_period_days`
  - `buyout_allowed` and `buyout_formula` (e.g. basic/30 × shortfall days)
  - `overtime_rate` and `payout_cycle`, `appraisal_cycle` dates
  - Applicability keys (`location`, `grade`, `employment_type`) and `effective_from` / `effective_to`
  - `source_clause_id`
- The LLM agent calls a tool such as `compute_leave_entitlement(employee_id, leave_type, dates)` or `check_clubbing(leave_types, dates)`. That tool evaluates the rules plus live HRMS data and returns both the result and the source clause IDs to cite.
- Extraction workflow: LLM drafts the rules, HR admin reviews them in a UI (diffs against the source clause shown side by side), then the rules are published. Regenerate the draft when a policy document version changes. This human-in-the-loop step is also a sellable "policy configuration" feature.
- Statutory Indian rules (Shops & Establishments Acts by state, Factories Act overtime at twice ordinary wages, EPF nomination via Form 2 / UAN e-nomination, gratuity) can be a vendor-maintained shared rule pack. Company policy rules then layer over it with precedence ("company may be more generous than statute, never less"). This is the same default-and-exception structure Catala formalizes. Those statutory specifics should be checked by the compliance researcher; they are not sourced here.
- json-rules-engine (JS), CEL, or plain Python functions keyed off a validated JSON config are enough. Rete-style engines (Drools) are overkill.

### Gaps
- I found no published HR-specific case study of LLM-to-rules extraction with accuracy numbers.
- I found no evaluation of LLM extraction accuracy into Catala or json-rules-engine specifically.

---

## 3. Policy versioning, effective dates, and per-location/grade variants

### Takeaway
Version-awareness must be enforced as hard metadata filters before retrieval, never left to the LLM to infer from text. Version-aware retrieval roughly doubled accuracy over naive RAG on versioned docs (90% vs 58%). Each chunk needs a document family ID, version, effective_from/to, status, and applicability scopes (entity, location/state, grade band, employment type). The query is filtered by the employee's attributes and an "as-of" date.

### Cited Findings
- VersionRAG builds a hierarchy of category, document, version (temporally linked), chunk and change nodes, where change nodes come from changelogs or diffs. An LLM classifies each query as content, version-listing or change retrieval. Content queries use vector search filtered to the relevant version. VersionQA results: 90% accuracy vs 58% for naive RAG and 64% for GraphRAG; implicit change detection 60% vs 0-10% for baselines. — [VersionRAG, arXiv 2510.08109](https://arxiv.org/html/2510.08109v1)
- Practitioner pattern: tag every chunk with a family ID, version ordinal, effective start/end, and status. Apply a hard as-of filter before scoring, a recency prior after, then rerank. Effective dates belong on the chunk, not only in a registry, and the effective date is distinct from the ingestion timestamp. — [Particula, version-aware RAG](https://particula.tech/blog/version-aware-rag-superseded-documents)
- Missing effective dates, ambiguous filenames, or conflicting active revisions should trigger clarification or abstention, not an automatic "latest" choice. File modification time is a weak signal. — [Zimaspace](https://shop.zimaspace.com/blogs/tech-ai-hub/features-reliable-document-version-selection-rag)
- Backend caveat: some vector DBs lack a date type (Pinecone uses epoch ints), and highly selective filters combined with ANN indexes can return fewer results than requested. — [Particula](https://particula.tech/blog/version-aware-rag-superseded-documents)
- Some teams keep active and archived corpora in separate indexes instead of relying on query-time filters. A practitioner warns that metadata only works if ingestion enforces it consistently. — [Reddit snapshot](https://reddit.sentinel-team.org/posts/1s21z4s/snapshots/2026-03-24T20%3A34%3A00.450683Z)

### Inferences
- Recommended data model (Postgres):
  - `policy_document(family_id, version, effective_from, effective_to, status[draft|active|superseded], supersedes_id)`
  - `policy_scope(document_id, entity, state, location, grade_min, grade_max, employment_type)`
  - `chunk(document_id, clause_id, section_path, text, contextual_prefix, embedding, tsvector)`
- At query time, resolve the employee profile from the HRMS (location, grade, employment type, joining date). Build a SQL WHERE clause from it: `status = 'active'` (or as-of date for historical questions such as "what was the rule when I joined"), scope match, and tenant_id. Then run hybrid search. The filter is ordinary SQL in Postgres, which avoids the ANN filter-recall problem at HR-corpus scale.
- Precedence rules for overlapping documents (location addendum overrides global handbook; a later circular overrides a handbook clause) should be explicit fields (`overrides_clause_id`), not inferred.
- For the long-context MVP path, the same filter decides which documents get stuffed into the cached prefix. Cache key = tenant + scope combination.
- Answers should state the version used ("per Leave Policy v3.2, effective 1 Apr 2026, applicable to Maharashtra employees").

### Gaps
- I found no HR-specific benchmark on version or scope errors. VersionRAG uses technical software docs.

---

## 4. Static knowledge (RAG) vs live data (tools/APIs); orchestrators as of 2026

### Takeaway
Treat policy text as retrievable knowledge. Treat employee-specific state (leave balance, payslip, request status, manager, grade) as tool calls against the HRMS. The answer for "can I take 3 days sick + 2 casual next week?" comes from a tool that combines rules, balances and calendar. An MCP server is a good boundary for HRMS integrations. For orchestration, practitioner comparisons suggest LangGraph for durable stateful workflows and human-in-the-loop, Pydantic AI for type-safe, provider-agnostic agents, and the Claude Agent SDK or OpenAI Agents SDK for the least scaffolding if committed to one provider. All evidence here is blog-level.

### Cited Findings
- LangGraph exposes the agent loop as an explicit graph of nodes and edges; the OpenAI Agents SDK hides it behind a thin Runner abstraction. — [Morph, AI agent frameworks 2026](https://www.morphllm.com/ai-agent-framework)
- LangGraph (and Microsoft Agent Framework) lead on durable execution, checkpoints and human-in-the-loop pauses. — [Morph](https://www.morphllm.com/ai-agent-framework)
- Pydantic AI suits type-safety-focused teams. One anecdotal comparison built the same chat app in about 160 lines vs about 280 for LangGraph. — [Towards AI](https://pub.towardsai.net/i-compared-6-python-ai-agent-frameworks-so-you-dont-have-to-langgraph-vs-crewai-vs-pydanticai-vs-d8a5e6e43262)
- Claude Agent SDK (renamed from Claude Code SDK) is recommended when committed to Claude and wanting the least scaffolding. Multi-agent styles differ: OpenAI uses handoffs, LangGraph subgraphs, Claude Agent SDK subagents. LangGraph and Pydantic AI are cross-provider. — [youngju.dev deep dive](https://www.youngju.dev/transcribe/culture/2026-05-16-ai-agent-frameworks-2026-langgraph-autogen-crewai-semantic-kernel-openai-agents-claude-sdk-pydantic-ai-deep-dive.en); [respan.ai](https://www.respan.ai/articles/best-ai-agent-frameworks)
- A common production pattern combines Pydantic AI domain agents with LangGraph for long-running orchestration. — [Morph](https://www.morphllm.com/ai-agent-framework)

### Inferences
- Tool set for the MVP (narrow and typed):
  - `search_policy(query, filters)` (filters auto-injected from the session's employee profile, never chosen by the model)
  - `get_employee_profile()`
  - `get_leave_balance(leave_type?)`
  - `get_request_status(request_id?)`
  - `get_payslip(month)`
  - `compute_entitlement(rule_id, params)` / `check_leave_application(types, dates)`
  - `escalate_to_hr(summary)`
- Authorization: the employee identity comes from the auth session and is bound server-side into each tool. The LLM must never pass an arbitrary employee_id. This prevents cross-employee data leakage via prompt injection.
- An HR Q&A agent is mostly single-turn tool use plus retrieval, with no long-running workflows. A thin loop is enough: provider SDK tool use, Pydantic AI, or Claude Agent SDK. LangGraph becomes worthwhile when approval workflows are added (leave application → manager approval → HRMS write) that need checkpoints and human-in-the-loop.
- Wrap HRMS connectors (Keka, Darwinbox, greytHR, Zoho People, which are common in India) as MCP servers. They can then be reused across orchestrators and exposed to customers' own AI clients.

### Gaps
- I found no rigorous benchmark comparing orchestrators. All comparison sources are blogs, some with inconsistent dates (e.g. the OpenAI Agents SDK release date is reported as both March 2025 and March 2026).
- MCP adoption specifics for Indian HRMS vendors were not researched here.

---

## 5. Citation, grounding, abstention, and evaluation

### Takeaway
Use the model provider's native citation feature (Anthropic Citations gave up to 15% higher recall accuracy than prompt-based citation in Anthropic's own evaluation, and one customer reported source hallucinations falling from 10% to 0%). Require clause-level citations, and abstain or escalate when no supporting clause is retrieved. Evaluate with a custom golden set of real HR questions, with RAGAS or DeepEval in CI. There are no authoritative thresholds. Practitioner starting points are faithfulness ≥0.75-0.90 and context recall ≥0.80; for HR, faithfulness and citation correctness should be set higher.

### Cited Findings
- Anthropic Citations API: source documents (PDF or plain text) are split into sentences and answers link to exact passages. Anthropic's internal evaluation found up to 15% higher recall accuracy vs prompt-based approaches. Cited text adds no output-token cost. — [Anthropic, Introducing Citations](https://www.anthropic.com/news/introducing-citations-api)
- Endex reported source hallucinations and formatting issues falling from 10% to 0%, plus a 20% increase in references per response. Some outlets instead report this as "reference accuracy". These are self-reported customer figures. — [Anthropic](https://www.anthropic.com/news/introducing-citations-api); [Enterprise AI World](https://www.enterpriseaiworld.com/Articles/News/News/Anthropic-Grounds-Claude-Outputs-with-New-Seamless-Citations-Feature-167789.aspx)
- RAGAS provides four core metrics without ground truth: faithfulness, answer relevancy, context precision and context recall. DeepEval is Pytest-native with 50+ metrics for CI regression gates. — [Particula, DeepEval vs RAGAS vs TruLens](https://particula.tech/blog/deepeval-vs-ragas-vs-trulens-rag-evaluation-stack)
- Suggested thresholds ("practitioner consensus", not official): faithfulness ≥0.75, answer relevancy ≥0.80, context precision ≥0.70, context recall ≥0.80. Another example gates on faithfulness ≥0.90 and context recall ≥0.80 using a 60-item golden set. — [hackernoon skill page](https://hackernoon.com/skills/pramoddutta-rag-evaluation-metrics); [qaskills](https://qaskills.sh/skills/thetestingacademy/rag-evaluation-metrics)
- Golden sets should hold expert-verified contexts and answers, with alerting thresholds. Keep CI sets small (up to a few hundred items). Low context recall points to chunking, embedding or retrieval problems; low faithfulness with good context points to prompt or guardrail problems. — [blckalpaca](https://blckalpaca.at/en/knowledge-base/ai-agents/what-is-a-rag-system/rag-evaluation-ragas-trulens); [Anyscale RAG eval docs](https://docs.anyscale.com/rag/evaluation)
- When dates or versions are missing or conflicting, abstain or clarify. — [Zimaspace](https://shop.zimaspace.com/blogs/tech-ai-hub/features-reliable-document-version-selection-rag)
- CRAG's retrieval evaluator (correct / incorrect / ambiguous) is a published pattern for gating generation on retrieval quality. — [CRAG](https://arxiv.org/pdf/2401.15884)

### Inferences
- Proposed HR-specific golden set: 150-300 questions per pilot tenant, stratified by category:
  - leave, WFH, PF/ESI nomination, notice buyout, combining leave, overtime, appraisal, reimbursement
  - English, Hindi and Hinglish phrasings
  - deliberately unanswerable questions, to test abstention
  - version- and scope-trap questions (e.g. "I'm in Bangalore, grade L2")
  - numeric questions checked against rule-engine ground truth
- Proposed custom metrics beyond RAGAS:
  - citation correctness (cited clause actually supports the claim, judged per claim)
  - correct-version/scope rate
  - numeric exact match
  - abstention precision and recall (refuses when it should; does not over-refuse)
  - escalation rate
- Suggested MVP targets (my inference, not sourced):
  - numeric exact match ≥99%, via deterministic tools
  - citation correctness ≥95%
  - faithfulness ≥0.9
  - context recall ≥0.9
  - wrong-version answers effectively 0 on the trap set
  - abstention recall ≥90% on unanswerable questions
- Output contract: a structured response `{answer, citations:[{doc, version, clause_id, quote}], computed_values:[{tool, inputs, output}], confidence, escalate:boolean}`. The UI renders clickable clause quotes. Reject or regenerate when an answer has a factual claim without a citation.

### Gaps
- I found no independent benchmark of the Citations API, and none for newer Claude models.
- No authoritative threshold standards exist. All thresholds above are practitioner opinion.

---

## 6. Recommended stack: database, embeddings, rerankers, multilingual (Hindi/Hinglish)

### Takeaway
Postgres with pgvector plus a BM25 extension (ParadeDB pg_search, or the newer pg_textsearch), fused with Reciprocal Rank Fusion, is enough at HR scale. It keeps tenancy, versioning metadata, rules and audit logs in one transactional store. For Hindi, BGE-M3 clearly beats multilingual-E5 and BM25 on Hindi-BEIR. Cohere Rerank 3.5 and later versions list Hindi among optimized languages. No benchmark covers Hinglish (romanized code-mixed text), so that must be handled with query normalization and a custom eval.

### Cited Findings
- ParadeDB hybrid search uses Reciprocal Rank Fusion (k=60 default; lower k sharpens top results). Tune branch weights on a labelled query set. The fused result can only include rows some branch returned, so per-branch LIMIT caps recall. The hybrid layer is labelled beta (v0.25.0+), while BM25 itself is described as production-ready. — [ParadeDB hybrid docs](https://api.pgxn.org/src/pg_search/pg_search-0.25.7/docs/documentation/hybrid/rrf.mdx); [ParadeDB blog, Hybrid Search in PostgreSQL](https://paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)
- pg_textsearch was open-sourced in late 2025 and is self-described as production-ready, but it is younger than ParadeDB. — [awesome-search: Search using PostgreSQL](https://frutik.github.io/awesome-search/Topics/Search-using-PostgreSQL)
- Hindi-BEIR: BGE-M3 averaged 47.29 NDCG@10 vs 39.93 for multilingual-E5 and 36.50 for BM25. — [Hindi-BEIR, arXiv 2408.09437](https://arxiv.org/pdf/2408.09437)
- NLLB-E5 is a zero-shot Hindi retriever distilled from multilingual E5 and needs no Hindi training data. The Hindi-BEIR benchmark has 15 datasets across 7 tasks. — [arXiv 2409.05401](https://arxiv.org/html/2409.05401v3)
- Indic benchmark across 12 Indian languages (2026): E5-Large-Instruct had the best monolingual Recall@1 (27.4%); BGE-M3 led reverse retrieval (32.1%). — [arXiv 2601.10205](https://arxiv.org/html/2601.10205)
- Cohere Rerank 3.5 supports 100+ languages, with "state-of-the-art" claims on 10 business languages including Hindi (vendor claim). Cohere docs list Rerank 4 and Rerank 5 variants, naming Hindi for Rerank 5, and caution that performance varies by language. — [Cohere Rerank overview](https://docs.cohere.com/v2/docs/rerank-overview)
- Voyage rerank-3.5 has a 32K context. One listing describes it in English and JSON terms, and I found no Hindi benchmark for it. — [cloudprice listing](https://cloudprice.net/models/voyage-rerank-3-5)
- In Anthropic's contextual retrieval tests, Gemini and Voyage embeddings performed best. Gemini Embedding tops MTEB with a 68.32 mean task score (blog-reported). — [Anthropic](https://www.anthropic.com/news/contextual-retrieval); [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2025/03/gemini-embedding/)
- A single-author preprint claims a custom Hindi embedding model gives 23% better retrieval precision than multilingual alternatives. Treat with caution. — [DeepRAG, arXiv 2503.08213](https://arxiv.org/html/2503.08213v1)

### Inferences
- **Database:** use managed Postgres (Supabase, Neon, or AWS RDS/Aurora in ap-south-1 Mumbai, for DPDP Act data-residency comfort). Add pgvector (HNSW) for vectors and a BM25 extension (or plain Postgres `tsvector` for an MVP), fused with RRF in SQL. A dedicated vector DB (Qdrant, Weaviate, Pinecone) is unnecessary until millions of chunks per tenant, which an HR corpus will not reach. Row-level security on tenant_id gives multi-tenancy.
- **Embeddings:** BGE-M3 (open, self-hostable, dense + sparse + multi-vector, strong Hindi) or a hosted multilingual model (Gemini embedding, Voyage multilingual, Cohere embed-multilingual). Pick by a 50-100-query bakeoff on your own data.
- **Reranker:** Cohere Rerank (3.5/4/5, Hindi supported) hosted, or bge-reranker-v2-m3 self-hosted for cost and data residency.
- **Hinglish:** apply an LLM query-rewrite step that turns code-mixed or romanized input into a canonical English query (plus Devanagari if docs are Hindi), keeping the original for BM25. Most Indian company handbooks are in English, so cross-lingual query → English docs is the main path. The answer goes back in the user's language or register.
- **Generator:** a mid-tier frontier model with native citations and prompt caching (e.g. Claude Sonnet- or Haiku-class). Cache reads on current Claude models are 0.05-0.1x input price, which makes long-context stuffing cheap at the per-tenant scale.

### Gaps
- I found no benchmark for Hinglish or romanized Hindi retrieval, and no evaluation of Sarvam or other Indian-vendor embedding models.
- I found no independent head-to-head of Cohere, Voyage and BGE rerankers on Hindi.
- I did not verify embedding and reranker API pricing in INR, or India-region hosting availability for Cohere and Voyage.

---

## Synthesized recommendation (inference, built on the cited findings above)

**MVP (weeks 0-8)**
1. Ingest PDF/DOCX policies, parse them into clause-level structure (section path and clause_id), and capture version and scope metadata through an HR-admin review UI.
2. Retrieval:
   - **Default path:** filter policies by the employee's scope and active status, then put the full filtered policy text in a cached prompt prefix. This works when it fits in about 100-150k tokens, which is most SMB handbooks.
   - **Fallback path (larger tenants):** contextual chunking (prepend LLM context to each chunk) plus Postgres hybrid search (pgvector + BM25, RRF), then rerank top-50-150 down to top-20.
3. Native citations with a mandatory clause-level citation. Abstain or escalate to HR when retrieval is insufficient, versions conflict, or the question involves discretionary judgment.
4. Live-data tools (HRMS via API or MCP) with server-side identity binding. Deterministic calculators for leave balance and eligibility, combining leave, notice buyout and overtime, starting with a hand-authored JSON rule config per tenant.
5. Hinglish query rewriting. Golden set of about 200 questions with RAGAS or DeepEval plus custom metrics for citation, version, numeric accuracy and abstention, run in CI.

**Later upgrades**
- LLM-assisted rule extraction (P2T-style: schema-constrained extraction, provenance, judge/repair, conflict checks, human approval), plus a shared statutory rule pack per Indian state.
- Version-diff and change-node indexing (VersionRAG-style) to answer "what changed in the leave policy this year?".
- CRAG-style retrieval grading and a single corrective re-query for low-confidence cases.
- LangGraph (or equivalent durable runtime) once transactional workflows are added (apply leave, raise ticket, approvals).
- Fine-tuned or domain-adapted reranker, or embeddings trained on logged Hinglish queries.
- GraphRAG or LightRAG only if cross-document sensemaking becomes a real use case, e.g. "summarize all policies affecting contractors".
