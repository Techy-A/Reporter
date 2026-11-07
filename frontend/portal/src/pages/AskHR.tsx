import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorText } from "@pp/shared";
import type { Me } from "../main";

type Citation = { policy_title: string; version: string; ref: string; heading: string; excerpt: string };
type Action = { id: "ask_hr" | "confirm_ticket" | "private_contact"; label: string; draft: string };
type Answer = {
  kind: "sensitive" | "faq" | "leave" | "policy_answer" | "policy_quote" | "tool_answer" | "no_answer";
  text: string; citations: Citation[]; actions: Action[]; contacts: { label: string; value: string }[];
  event_id: number | null; meta: { used_llm: boolean };
};
type Turn = { id: number; who: "me"; text: string } | { id: number; who: "bot"; q: string; a: Answer };

const CHIPS: { label: string; text?: string; quick?: "leave_balance" }[] = [
  { label: "My leave balance", quick: "leave_balance" },
  { label: "Club sick + casual leave?", text: "Can I club sick and casual leave?" },
  { label: "Overtime credit", text: "When is overtime credited?" },
  { label: "Work from home", text: "How many work from home days are allowed?" },
  { label: "Notice period buyout", text: "Can I buy out my notice period?" },
];

const SOURCE: Record<Answer["kind"], string> = {
  sensitive: "", faq: "Answer from HR", leave: "From HR's records", policy_answer: "Checked against your policy",
  policy_quote: "Quoted from your policy", tool_answer: "From HR's records", no_answer: "",
};

let seq = 0;

export default function AskHR({ me }: { me: Me }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [turns.length, busy]);

  async function send(t: string, quick?: "leave_balance", label?: string) {
    if (busy || (!t.trim() && !quick)) return;
    setErr("");
    setBusy(true);
    setTurns((x) => [...x, { id: ++seq, who: "me", text: label ?? t }]);
    setText("");
    try {
      const a = await api<Answer>("/api/ask", { json: quick ? { quick } : { text: t } });
      setTurns((x) => [...x, { id: ++seq, who: "bot", q: t, a }]);
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void send(text);
  }

  return (
    <div className="p-page ask">
      <div className="p-title">
        <div>
          <h1>Ask HR</h1>
          <p className="small muted">Answers come from your organisation's policies and HR's records, with the source shown.</p>
        </div>
      </div>

      <div className="ask-thread" aria-live="polite">
        {turns.length === 0 && (
          <div className="ask-hello">
            <p>Hi {me.name.split(" ")[0]}, what do you need? Tap a topic or type your question, in English or Hinglish.</p>
          </div>
        )}
        {turns.map((t) => t.who === "me"
          ? <div key={t.id} className="ask-me">{t.text}</div>
          : <BotTurn key={t.id} q={t.q} a={t.a} />)}
        {busy && <div className="ask-bot ask-typing" aria-label="Looking it up">Looking it up…</div>}
        <div ref={end} />
      </div>

      {err && <div className="notice notice-bad" role="alert">{err}</div>}

      <div className="ask-dock">
        <div className="p-chips" role="group" aria-label="Common questions">
          {CHIPS.map((c) => (
            <button key={c.label} className="p-chip" disabled={busy} onClick={() => send(c.text ?? "", c.quick, c.label)}>
              {c.label}
            </button>
          ))}
          <Link className="p-chip" to="/requests?new=1">Talk to HR</Link>
        </div>
        <form className="ask-form" onSubmit={submit}>
          <input className="input" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000}
                 placeholder="Type your question…" aria-label="Your question" />
          <button className="btn btn-primary" disabled={busy || !text.trim()}>Ask</button>
        </form>
        <p className="small muted ask-note">Only you can see this chat. It isn't saved. Don't share bank or Aadhaar numbers here.</p>
      </div>
    </div>
  );
}

function BotTurn({ q, a }: { q: string; a: Answer }) {
  const [rated, setRated] = useState<boolean | null>(null);
  const [sent, setSent] = useState<string>("");
  const [draft, setDraft] = useState<string | null>(null);
  const [err, setErr] = useState("");

  async function rate(helpful: boolean) {
    if (!a.event_id) return;
    setRated(helpful);
    await api(`/api/ask/${a.event_id}/feedback`, { json: { helpful } }).catch(() => {});
  }
  async function ticket(kind: "question" | "sensitive", body: string) {
    setErr("");
    try {
      const t = await api<{ id: number }>("/api/tickets", { json: { kind, text: body } });
      setSent(`Sent to HR as request #${t.id}. You'll see their reply under Requests.`);
      setDraft(null);
    } catch (x) {
      setErr(errorText(x));
    }
  }

  if (a.kind === "sensitive") {
    return (
      <div className="ask-bot ask-sensitive">
        <div className="ask-lock" aria-hidden>🔒</div>
        <p>{a.text}</p>
        <ul className="ask-contacts">
          {a.contacts.map((c) => (
            <li key={c.label}><span className="small muted">{c.label}</span>
              {/^\d+$/.test(c.value) ? <a className="mono" href={`tel:${c.value}`}>{c.value}</a> : <b>{c.value}</b>}</li>
          ))}
        </ul>
        {sent ? <div className="notice notice-ok small">{sent}</div> : (
          <button className="btn" onClick={() => ticket("sensitive", "")}>Ask HR to contact me privately</button>
        )}
        {err && <div className="notice notice-bad small">{err}</div>}
      </div>
    );
  }

  return (
    <div className={`ask-bot${a.kind === "no_answer" ? " is-unknown" : ""}`}>
      {SOURCE[a.kind] && !(a.kind === "leave" && a.actions.length > 0) && <div className="ask-source small">{SOURCE[a.kind]}{a.meta.used_llm && " · AI"}</div>}
      <p className="ask-text">{a.text}</p>
      {a.citations.length > 0 && (
        <div className="ask-cites">
          {a.citations.map((c, i) => (
            <details key={i} className="ask-cite" open={a.kind === "policy_quote"}>
              <summary>
                <span className="ask-cite-title">{c.policy_title}{c.ref && <span className="mono"> §{c.ref}</span>}</span>
                {c.heading && <span className="small muted"> {c.heading}</span>}
              </summary>
              {c.excerpt && <p className="small">{c.excerpt}</p>}
              {c.version && <div className="small muted mono">Version {c.version}</div>}
            </details>
          ))}
        </div>
      )}

      {draft !== null ? (
        <div className="ask-draft">
          <label className="field"><span>Message to HR</span>
            <textarea className="input" rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={2000} />
          </label>
          <div className="ask-actions">
            <button className="btn btn-primary btn-sm" disabled={!draft.trim()} onClick={() => ticket("question", draft)}>Send to HR</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setDraft(null)}>Cancel</button>
          </div>
        </div>
      ) : sent ? <div className="notice notice-ok small">{sent}</div> : (
        <div className="ask-actions">
          {a.actions.map((x) => (
            <button key={x.id} className={`btn btn-sm${a.kind === "no_answer" ? " btn-primary" : ""}`}
                    onClick={() => setDraft(x.id === "confirm_ticket" ? x.draft : q)}>
              {x.label}
            </button>
          ))}
          {a.event_id && a.kind !== "no_answer" && (
            rated === null ? (
              <span className="ask-rate">
                <span className="small muted">Helpful?</span>
                <button className="btn btn-ghost btn-sm" aria-label="Helpful" onClick={() => rate(true)}>👍</button>
                <button className="btn btn-ghost btn-sm" aria-label="Not helpful" onClick={() => rate(false)}>👎</button>
              </span>
            ) : <span className="small muted">Thanks for the feedback.</span>
          )}
        </div>
      )}
      {err && <div className="notice notice-bad small">{err}</div>}
    </div>
  );
}
