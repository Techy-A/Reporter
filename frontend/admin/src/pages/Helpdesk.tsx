import { useState, type FormEvent } from "react";
import { api, errorText, fmtDayTime, parseUtc, relative } from "@pp/shared";
import type { HelpdeskStats, Ticket } from "../types";
import { useLoad } from "../useLoad";

const KIND = { question: "Question", talk_to_hr: "Talk to HR", sensitive: "Private contact" } as const;
const STATUS = { open: "pill-warn", answered: "pill-info", closed: "" } as const;
type Tab = "open" | "answered" | "closed" | "all";

export default function Helpdesk() {
  const stats = useLoad(() => api<HelpdeskStats>("/api/helpdesk/stats"));
  const [tab, setTab] = useState<Tab>("open");
  const tickets = useLoad(() => api<Ticket[]>(`/api/tickets?status=${tab}`), [tab]);
  const [openId, setOpenId] = useState<number | null>(null);
  const s = stats.data;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Help desk</h1>
          <p className="summary">
            Employees ask HR questions in their portal. Answers come from your policies, FAQ answers and leave
            records. Anything the assistant can't answer, and anything sensitive, lands here for a person.
          </p>
        </div>
      </header>

      {s && (
        <section className="kpis" aria-label="Last 7 days">
          <Kpi n={s.questions_7d} label="Questions this week" />
          <Kpi n={s.answered_without_hr_7d} label="Answered without HR"
               sub={s.questions_7d ? `${Math.round((100 * s.answered_without_hr_7d) / s.questions_7d)}%` : undefined} />
          <Kpi n={s.open_tickets} label="Waiting for HR" tone={s.open_tickets ? "warn" : undefined} />
          <Kpi n={s.helpful_rate === null ? "–" : `${Math.round(s.helpful_rate * 100)}%`} label="Rated helpful" />
        </section>
      )}

      <div className="hd-grid">
        <section className="card">
          <div className="table-tools">
            <div className="tabs" role="tablist">
              {(["open", "answered", "closed", "all"] as Tab[]).map((t) => (
                <button key={t} role="tab" aria-selected={tab === t} className={`tab${tab === t ? " is-on" : ""}`}
                        onClick={() => { setTab(t); setOpenId(null); }}>
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>
          {tickets.error && <div className="notice notice-bad">{tickets.error}</div>}
          <ul className="ticket-list">
            {(tickets.data ?? []).map((t) => (
              <li key={t.id}>
                <button className={`ticket-row${openId === t.id ? " is-on" : ""}`} onClick={() => setOpenId(t.id)}>
                  <span className="strong">{t.employee_name}</span>
                  <span className={`pill ${STATUS[t.status]}`}>{t.status}</span>
                  <span className="small muted">{KIND[t.kind]}{t.sensitive && " · owner only"}</span>
                  <span className="small muted right">{relative(parseUtc(t.updated_at))}</span>
                </button>
              </li>
            ))}
          </ul>
          {tickets.data?.length === 0 && <div className="empty muted">Nothing {tab === "all" ? "yet" : tab}.</div>}
        </section>

        {openId ? <TicketPanel id={openId} onChange={() => { void tickets.reload(); void stats.reload(); }} />
          : s && <ModelCard s={s} />}
      </div>
    </div>
  );
}

function Kpi({ n, label, sub, tone }: { n: number | string; label: string; sub?: string; tone?: string }) {
  return (
    <div className={`kpi card${tone ? ` kpi-${tone}` : ""}`}>
      <div className="kpi-n mono">{n}{sub && <span className="kpi-sub"> {sub}</span>}</div>
      <div className="small muted">{label}</div>
    </div>
  );
}

function TicketPanel({ id, onChange }: { id: number; onChange: () => void }) {
  const t = useLoad(() => api<Ticket>(`/api/tickets/${id}`), [id]);
  const [text, setText] = useState("");
  const [err, setErr] = useState("");

  async function reply(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api(`/api/tickets/${id}/reply`, { json: { text } });
      setText("");
      await t.reload();
      onChange();
    } catch (x) {
      setErr(errorText(x));
    }
  }
  async function close() {
    await api(`/api/tickets/${id}/close`, { method: "POST" }).catch((x) => setErr(errorText(x)));
    await t.reload();
    onChange();
  }

  const d = t.data;
  return (
    <section className="card pad ticket-panel">
      {!d ? <p className="muted">{t.error || "Loading…"}</p> : (
        <>
          <div className="split">
            <div>
              <h2>{d.employee_name}</h2>
              <div className="small muted">{KIND[d.kind]} · opened {fmtDayTime(parseUtc(d.created_at))}</div>
            </div>
            {d.status !== "closed" && <button className="btn btn-sm" onClick={close}>Close</button>}
          </div>
          {d.sensitive && (
            <div className="notice notice-info small">
              Private request from the sensitive-topic screen. What the employee typed there was not saved. Contact
              them directly and follow your POSH / grievance process.
            </div>
          )}
          <div className="thread">
            {d.messages?.map((m, i) => (
              <div key={i} className={`bubble ${m.sender === "hr" ? "from-us" : "from-them"}`}>
                <div className="bubble-text">{m.text}</div>
                <div className="bubble-meta">{m.sender === "hr" ? "HR" : d.employee_name} · {fmtDayTime(parseUtc(m.at))}</div>
              </div>
            ))}
          </div>
          {d.status !== "closed" && (
            <form className="reply" onSubmit={reply}>
              <textarea className="input" rows={3} required value={text} onChange={(e) => setText(e.target.value)}
                        placeholder="Reply to the employee. They'll see it in their portal." aria-label="Reply" />
              <button className="btn btn-primary">Send reply</button>
            </form>
          )}
          {err && <div className="notice notice-bad">{err}</div>}
        </>
      )}
    </section>
  );
}

function ModelCard({ s }: { s: HelpdeskStats }) {
  const m = s.model;
  const rows: [boolean, string, string][] = [
    [true, "Safety gate", "POSH, self-harm and legal topics go to a person before any AI sees them."],
    [true, "HR's own answers", "FAQ answers you write always win."],
    [true, "Search (RAG)", "Only active policies that apply to the employee's location, grade and type."],
    [m.embeddings, "Meaning search (embeddings)", m.embeddings ? `On: ${m.embed_model}` : "Off: keyword search only. Free option: Ollama nomic-embed-text."],
    [m.configured, "AI answers", m.configured ? `${m.name}, temperature 0, ${m.context_tokens}-token context budget` : "Off: employees get the policy text quoted. Free option: Ollama."],
    [m.configured && m.tools, "Tools + agent", m.configured && m.tools ? `Up to ${m.max_steps} steps; can only read the employee's own data and draft a ticket` : "Off"],
    [true, "Grounding check", "Citations must be real and every number must appear in the cited text."],
  ];
  return (
    <section className="card pad">
      <h2>How answers are made</h2>
      <ul className="status-list">
        {rows.map(([on, label, note]) => (
          <li key={label}><span className={`dot ${on ? "dot-ok" : "dot-warn"}`} /><b>{label}</b><span className="small muted">{note}</span></li>
        ))}
      </ul>
      {m.configured && (
        <p className="small muted">
          This week: {m.calls_7d} AI answers · {m.tokens_in_7d.toLocaleString("en-IN")} tokens in,{" "}
          {m.tokens_out_7d.toLocaleString("en-IN")} out{m.avg_steps !== null && ` · ${m.avg_steps.toFixed(1)} steps on average`}
        </p>
      )}
      <p className="small muted">Select a request on the left to read and reply.</p>
    </section>
  );
}
