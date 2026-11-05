import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, errorText, fmtDayTime, fmtTime, parseUtc } from "@pp/shared";
import type { CandidateDetail, Employee, Msg, Round } from "../types";
import StatusPill from "./StatusPill";

type SimState = { messages: Msg[]; buttons: { label: string; token: string }[] };

type Props = {
  id: number;
  rounds: Round[];
  employees: Employee[];
  simulator: boolean;
  onClose: () => void;
  onChanged: () => void;
};

export default function CandidateDrawer({ id, rounds, employees, simulator, onClose, onChanged }: Props) {
  const [c, setC] = useState<CandidateDetail | null>(null);
  const [sim, setSim] = useState<SimState | null>(null);
  const [reply, setReply] = useState("");
  const [simText, setSimText] = useState("");
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const threadEnd = useRef<HTMLDivElement>(null);

  async function load() {
    try {
      setC(await api<CandidateDetail>(`/api/candidates/${id}`));
      if (simulator) setSim(await api<SimState>(`/api/dev/sim/${id}`));
    } catch (e) {
      setErr(errorText(e));
    }
  }

  useEffect(() => {
    setC(null);
    setSim(null);
    setErr("");
    setNote("");
    void load();
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ block: "end" });
  }, [c?.messages.length]);

  async function act(path: string, body?: unknown, done?: string) {
    setErr("");
    setNote("");
    setBusy(true);
    try {
      const res = await api<{ telegram_link?: string | null }>(`/api/candidates/${id}/${path}`,
        body === undefined ? { method: "POST" } : { json: body });
      if (res?.telegram_link) setNote(`Share this link with the candidate: ${res.telegram_link}`);
      else if (done) setNote(done);
      await load();
      onChanged();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  async function simSend(payload: { text?: string; token?: string }) {
    setErr("");
    try {
      setSim(await api<SimState>(`/api/dev/sim/${id}`, { json: payload }));
      setSimText("");
      setC(await api<CandidateDetail>(`/api/candidates/${id}`));
      onChanged();
    } catch (e) {
      setErr(errorText(e));
    }
  }

  async function sendReply(e: FormEvent) {
    e.preventDefault();
    if (!reply.trim()) return;
    await act("reply", { text: reply.trim() }, "Sent. The assistant is paused for this candidate.");
    setReply("");
  }

  const round = c && rounds.find((r) => r.id === c.round_id);
  const interviewer = c?.interviewer_id ? employees.find((e) => e.id === c.interviewer_id) : null;
  const past = c?.booked_start ? parseUtc(c.booked_start) < new Date() : false;

  return (
    <div className="drawer-scrim" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Candidate" onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <h2>{c?.name ?? "Loading…"}</h2>
            {c && (
              <div className="small muted">
                {round ? `${round.role_title} · ${round.round_name}` : ""} · <span className="mono">{c.phone_masked}</span>
              </div>
            )}
          </div>
          <button ref={closeRef} className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">Close</button>
        </header>

        {c && (
          <>
            <div className="drawer-facts">
              <StatusPill status={c.status} />
              {c.bot_paused && <span className="pill pill-warn">You're handling this chat</span>}
              {c.booked_start && (
                <span className="small">
                  <span className="mono">{fmtDayTime(parseUtc(c.booked_start))}</span>
                  {interviewer ? ` with ${interviewer.name}` : ""}
                </span>
              )}
            </div>

            <div className="drawer-actions">
              {(c.status === "new" || c.status === "invited") && (
                <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => act("invite", undefined, "Invite sent.")}>
                  {c.status === "new" ? "Send invite" : "Send invite again"}
                </button>
              )}
              {c.bot_paused || c.needs_attention ? (
                <button className="btn btn-sm" disabled={busy} onClick={() => act("resume", undefined, "The assistant is back on.")}>
                  Hand back to assistant
                </button>
              ) : (
                c.status !== "new" && (
                  <button className="btn btn-sm" disabled={busy} onClick={() => act("takeover", undefined, "You're now handling this chat.")}>
                    Take over chat
                  </button>
                )
              )}
              {c.booked_start && !past && (
                <button className="btn btn-sm btn-danger" disabled={busy}
                        onClick={() => confirm("Cancel this interview? The slot will be freed.") && act("cancel", undefined, "Interview cancelled.")}>
                  Cancel interview
                </button>
              )}
              {c.booked_start && past && !["attended", "no_show"].includes(c.status) && (
                <>
                  <button className="btn btn-sm" disabled={busy} onClick={() => act("outcome", { outcome: "attended" })}>Mark attended</button>
                  <button className="btn btn-sm" disabled={busy} onClick={() => act("outcome", { outcome: "no_show" })}>Mark no-show</button>
                </>
              )}
            </div>
            {note && <div className="notice notice-ok" role="status">{note}</div>}
            {err && <div className="notice notice-bad" role="alert">{err}</div>}

            <h3 className="drawer-sub">Conversation</h3>
            <div className="thread" aria-live="polite">
              {c.messages.length === 0 && <p className="muted small">No messages yet. Send the invite to start.</p>}
              {c.messages.map((m, i) => (
                <div key={i} className={`bubble ${m.direction === "in" ? "from-them" : "from-us"} by-${m.sender}`}>
                  <div className="bubble-text">{m.text}</div>
                  <div className="bubble-meta">
                    {m.sender === "recruiter" ? "You" : m.sender === "bot" ? "Assistant" : "Candidate"}
                    {" · "}<span className="mono">{fmtTime(parseUtc(m.at))}</span>
                    {m.intent && m.direction === "in" && <span className="intent">understood as: {m.intent.replace("_", " ")}</span>}
                  </div>
                </div>
              ))}
              <div ref={threadEnd} />
            </div>

            <form className="reply" onSubmit={sendReply}>
              <input className="input" placeholder="Reply as yourself…" value={reply} maxLength={1000}
                     onChange={(e) => setReply(e.target.value)} aria-label="Reply to candidate" />
              <button className="btn" disabled={busy || !reply.trim()}>Send</button>
            </form>
            <p className="hint">Replying pauses the assistant for this candidate until you hand it back.</p>

            {simulator && sim && (
              <section className="sim">
                <h3>Candidate's phone (simulator)</h3>
                <p className="hint">Dev only. Tap a button or type as the candidate would.</p>
                <div className="sim-buttons">
                  {sim.buttons.length === 0 && <span className="small muted">No buttons waiting.</span>}
                  {sim.buttons.map((b) => (
                    <button key={b.token} className="btn btn-sm sim-btn" onClick={() => simSend({ token: b.token })}>
                      {b.label}
                    </button>
                  ))}
                </div>
                <form className="reply" onSubmit={(e) => { e.preventDefault(); if (simText.trim()) void simSend({ text: simText.trim() }); }}>
                  <input className="input" placeholder='e.g. "3 baje ke baad ho sakta hai?"' value={simText}
                         onChange={(e) => setSimText(e.target.value)} aria-label="Message as candidate" />
                  <button className="btn" disabled={!simText.trim()}>Send as candidate</button>
                </form>
              </section>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
