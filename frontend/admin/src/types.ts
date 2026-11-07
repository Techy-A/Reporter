export type Me = { id: number; email: string; role: "owner" | "recruiter"; mfa_enabled: boolean; active: boolean };

export type Employee = {
  id: number; name: string; email: string; is_interviewer: boolean; active: boolean;
  location: string; grade: string; employment_type: string;
};

export type Round = {
  id: number;
  role_title: string;
  round_name: string;
  duration_min: number;
  mode: "video" | "in_person";
  location: string;
  window_start: string;
  window_end: string;
  interviewer_ids: number[];
};

export type CandidateRow = {
  id: number;
  round_id: number;
  name: string;
  phone_masked: string;
  channel: string;
  status: string;
  booked_start: string | null;
  interviewer_id: number | null;
  needs_attention: boolean;
  bot_paused: boolean;
  last_message_at: string | null;
};

export type Msg = { direction: "in" | "out"; sender: string; text: string; intent: string | null; at: string };
export type CandidateDetail = CandidateRow & { messages: Msg[] };

export type Kpis = {
  invited: number;
  booked: number;
  zero_touch_pct: number;
  reminders_sent: number;
  no_shows_7d: number;
  needs_attention: number;
};

export type Health = {
  database: boolean;
  channels: { whatsapp: boolean; telegram: boolean };
  llm_configured: boolean;
  messaging_paused: boolean;
  candidates_without_consent: number;
  simulator: boolean;
};

export type AuditRow = {
  at: string;
  actor_type: string;
  actor_id: number | null;
  action: string;
  record_type: string | null;
  record_id: number | null;
  result: string;
};

export const STATUS: Record<string, { label: string; tone: "" | "ok" | "warn" | "bad" | "info" }> = {
  new: { label: "Not invited", tone: "" },
  invited: { label: "Invited", tone: "info" },
  choosing: { label: "Choosing a slot", tone: "info" },
  booked: { label: "Booked", tone: "ok" },
  rescheduled: { label: "Rescheduled", tone: "ok" },
  confirmed: { label: "Confirmed", tone: "ok" },
  needs_recruiter: { label: "Needs you", tone: "warn" },
  cant_make_it: { label: "Can't make it", tone: "bad" },
  cancelled: { label: "Cancelled", tone: "bad" },
  attended: { label: "Attended", tone: "ok" },
  no_show: { label: "No-show", tone: "bad" },
};

// ---------------------------------------------------------------- Phase 2: help desk
export type Citation = { policy_title: string; version: string; ref: string; heading: string; excerpt: string };
export type AskAction = { id: string; label: string; draft: string };
export type AskResult = {
  kind: "sensitive" | "faq" | "leave" | "policy_answer" | "policy_quote" | "tool_answer" | "no_answer";
  text: string;
  citations: Citation[];
  actions: AskAction[];
  contacts: { label: string; value: string }[];
  event_id: number | null;
  route?: string;
  meta: { used_llm: boolean; tokens_in: number; tokens_out: number; agent_steps: number; tools_used: string[] };
};
export type Policy = {
  id: number; title: string; version: string; effective_from: string; status: "draft" | "active" | "superseded";
  locations: string[]; grades: string[]; employment_types: string[]; source_name: string;
  clause_count: number; embedded: number; created_at: string;
  clauses?: { id: number; ref: string; heading: string; text: string }[] | null;
};
export type Faq = { id: number; question: string; answer: string; active: boolean; updated_at: string };
export type Ticket = {
  id: number; employee_name: string; kind: "question" | "talk_to_hr" | "sensitive"; sensitive: boolean;
  status: "open" | "answered" | "closed"; created_at: string; updated_at: string;
  messages?: { sender: "employee" | "hr"; text: string; at: string }[] | null;
};
export type EvalCase = {
  id: number; question: string; expect_route: string; expect_policy_title: string; expect_ref: string;
  must_include: string; as_location: string; as_grade: string; as_employment_type: string;
  last_passed: boolean | null; last_detail: string; last_run_at: string | null;
};
export type HelpdeskStats = {
  questions_7d: number; answered_without_hr_7d: number; by_route_7d: Record<string, number>;
  helpful_rate: number | null; open_tickets: number;
  model: {
    configured: boolean; name: string | null; tools: boolean; max_steps: number; context_tokens: number;
    embeddings: boolean; embed_model: string | null; calls_7d: number; tokens_in_7d: number; tokens_out_7d: number;
    avg_steps: number | null;
  };
};
