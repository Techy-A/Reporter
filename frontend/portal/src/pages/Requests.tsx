import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api, errorText, fmtDayTime, parseUtc } from "@pp/shared";

type Ticket = {
  id: number; kind: "question" | "talk_to_hr" | "sensitive"; status: "open" | "answered" | "closed";
  created_at: string; updated_at: string; messages: { sender: "employee" | "hr"; text: string; at: string }[];
};
const STATUS = { open: ["Waiting for HR", "pill-warn"], answered: ["HR replied", "pill-ok"], closed: ["Closed", ""] } as const;
const KIND = { question: "Question", talk_to_hr: "Talk to HR", sensitive: "Private contact" } as const;

export default function Requests() {
  const [params, setParams] = useSearchParams();
  const [list, setList] = useState<Ticket[] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const composing = params.get("new") === "1";

  const load = useCallback(async () => {
    try {
      setList(await api<Ticket[]>("/api/tickets"));
    } catch (e) {
      setErr(errorText(e));
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="p-page">
      <div className="p-title">
        <div>
          <h1>Requests</h1>
          <p className="small muted">Questions you've sent to HR and their replies.</p>
        </div>
        {!composing && <button className="btn btn-sm" onClick={() => setParams({ new: "1" })}>New request</button>}
      </div>

      {composing && <Compose onDone={(id) => { setParams({}); void load(); setOpen(id); }} onCancel={() => setParams({})} />}
      {err && <div className="notice notice-bad">{err}</div>}

      {list?.length === 0 && !composing && <div className="p-empty">No requests yet. If the assistant can't answer something, you can send it to HR from the chat.</div>}
      {list?.map((t) => (
        <div key={t.id} className="p-card2 req">
          <button className="req-head" onClick={() => setOpen(open === t.id ? null : t.id)} aria-expanded={open === t.id}>
            <span className="strong">#{t.id} · {KIND[t.kind]}</span>
            <span className={`pill ${STATUS[t.status][1]}`}>{STATUS[t.status][0]}</span>
            <span className="small muted">Updated {fmtDayTime(parseUtc(t.updated_at))}</span>
          </button>
          {open === t.id && <Thread id={t.id} onChange={load} />}
        </div>
      ))}
    </div>
  );
}

function Compose({ onDone, onCancel }: { onDone: (id: number) => void; onCancel: () => void }) {
  const [text, setText] = useState("");
  const [err, setErr] = useState("");
  async function send(e: FormEvent) {
    e.preventDefault();
    try {
      const t = await api<Ticket>("/api/tickets", { json: { kind: "talk_to_hr", text } });
      onDone(t.id);
    } catch (x) {
      setErr(errorText(x));
    }
  }
  return (
    <form className="p-card" onSubmit={send}>
      <h2>Talk to HR</h2>
      <label className="field"><span>What do you need?</span>
        <textarea className="input" rows={4} required maxLength={2000} value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="My joining date is wrong on my profile…" /></label>
      <p className="small muted">Only HR sees this. For harassment or anything you'd rather say privately, use the chat and HR's contact options appear.</p>
      {err && <div className="notice notice-bad">{err}</div>}
      <div className="ask-actions">
        <button className="btn btn-primary">Send to HR</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function Thread({ id, onChange }: { id: number; onChange: () => void }) {
  const [t, setT] = useState<Ticket | null>(null);
  const [text, setText] = useState("");
  const [err, setErr] = useState("");
  const load = useCallback(async () => setT(await api<Ticket>(`/api/tickets/${id}`)), [id]);
  useEffect(() => {
    void load().catch((e) => setErr(errorText(e)));
  }, [load]);

  async function reply(e: FormEvent) {
    e.preventDefault();
    try {
      setT(await api<Ticket>(`/api/tickets/${id}/reply`, { json: { text } }));
      setText("");
      onChange();
    } catch (x) {
      setErr(errorText(x));
    }
  }

  if (!t) return <p className="small muted">{err || "Loading…"}</p>;
  return (
    <div className="req-thread">
      {t.messages.map((m, i) => (
        <div key={i} className={m.sender === "hr" ? "ask-bot" : "ask-me"}>
          <div className="ask-source small">{m.sender === "hr" ? "HR" : "You"} · {fmtDayTime(parseUtc(m.at))}</div>
          <div className="ask-text">{m.text}</div>
        </div>
      ))}
      {t.status !== "closed" && (
        <form className="ask-form" onSubmit={reply}>
          <input className="input" required maxLength={2000} value={text} onChange={(e) => setText(e.target.value)}
                 placeholder="Add a message" aria-label="Add a message" />
          <button className="btn btn-sm">Send</button>
        </form>
      )}
      {err && <div className="notice notice-bad small">{err}</div>}
    </div>
  );
}
