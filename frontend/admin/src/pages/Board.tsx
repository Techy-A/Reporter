import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDayTime, parseUtc, relative } from "@pp/shared";
import CandidateDrawer from "../components/CandidateDrawer";
import SlotRail from "../components/SlotRail";
import StatusPill from "../components/StatusPill";
import type { CandidateRow, Employee, Health, Kpis, Round } from "../types";
import { useLoad } from "../useLoad";

export default function Board() {
  const [roundId, setRoundId] = useState<number | "">("");
  const [onlyNeedsMe, setOnlyNeedsMe] = useState(false);
  const [open, setOpen] = useState<number | null>(null);

  const rows = useLoad(() => api<CandidateRow[]>("/api/candidates"));
  const rounds = useLoad(() => api<Round[]>("/api/rounds"));
  const people = useLoad(() => api<Employee[]>("/api/employees"));
  const kpis = useLoad(() => api<Kpis>("/api/kpis"));
  const health = useLoad(() => api<Health>("/api/health"));

  const roundById = useMemo(() => new Map((rounds.data ?? []).map((r) => [r.id, r])), [rounds.data]);
  const empById = useMemo(() => new Map((people.data ?? []).map((e) => [e.id, e])), [people.data]);

  const visible = (rows.data ?? []).filter(
    (r) => (roundId === "" || r.round_id === roundId) && (!onlyNeedsMe || r.needs_attention),
  );

  function refresh() {
    void rows.reload();
    void kpis.reload();
  }

  const k = kpis.data;
  const noRounds = rounds.data && rounds.data.length === 0;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Scheduling board</h1>
          {k && (
            <p className="summary">
              <b>{k.invited}</b> invited · <b>{k.booked}</b> booked ·{" "}
              <b>{k.zero_touch_pct}%</b> booked without you · <b>{k.no_shows_7d}</b> no-shows this week
              {k.needs_attention > 0 && (
                <>
                  {" · "}
                  <button className="link-btn attention" onClick={() => setOnlyNeedsMe(true)}>
                    {k.needs_attention} need{k.needs_attention === 1 ? "s" : ""} you
                  </button>
                </>
              )}
            </p>
          )}
        </div>
        <div className="head-actions">
          <Link className="btn btn-primary" to="/rounds">New round</Link>
        </div>
      </header>

      {health.data?.messaging_paused && (
        <div className="notice notice-bad">All outgoing messages are paused. Turn them back on in Settings.</div>
      )}
      {health.data?.simulator && (
        <div className="notice notice-info">
          Simulator mode: no real messages are sent. Open a candidate to play their side of the chat.
        </div>
      )}

      <SlotRail rows={rows.data ?? []} onOpen={setOpen} />

      <section className="card table-card">
        <div className="table-tools">
          <label className="field inline">
            <span>Round</span>
            {/* ds-allow-native-select: native is the better phone control; see design/DESIGN_RULES.md */}
            <select className="input" value={roundId} onChange={(e) => setRoundId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">All rounds</option>
              {(rounds.data ?? []).map((r) => (
                <option key={r.id} value={r.id}>{r.role_title} · {r.round_name}</option>
              ))}
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={onlyNeedsMe} onChange={(e) => setOnlyNeedsMe(e.target.checked)} />
            Only candidates who need you
          </label>
          <button className="btn btn-ghost btn-sm" onClick={refresh}>Refresh</button>
        </div>

        {rows.error && <div className="notice notice-bad">{rows.error}</div>}

        {noRounds ? (
          <div className="empty">
            <h2>Start with an interview round</h2>
            <p className="muted">Create a round, add interviewers, then upload your candidate list as a CSV.</p>
            <Link className="btn btn-primary" to="/rounds">Create a round</Link>
          </div>
        ) : visible.length === 0 ? (
          <div className="empty">
            <p className="muted">{onlyNeedsMe ? "Nobody needs you right now." : "No candidates yet. Upload a CSV on the Interview rounds page."}</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Round</th>
                  <th>Status</th>
                  <th>Interview</th>
                  <th>Interviewer</th>
                  <th>Last message</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => {
                  const rd = roundById.get(r.round_id);
                  return (
                    <tr key={r.id} className={r.needs_attention ? "row-attention" : ""} onClick={() => setOpen(r.id)}>
                      <td>
                        <button className="link-btn strong" onClick={(e) => { e.stopPropagation(); setOpen(r.id); }}>{r.name}</button>
                        <div className="small muted num">{r.phone_masked}</div>
                      </td>
                      <td className="small">{rd ? <>{rd.role_title}<div className="muted">{rd.round_name}</div></> : ""}</td>
                      <td><StatusPill status={r.status} /></td>
                      <td className="num small">{r.booked_start ? fmtDayTime(parseUtc(r.booked_start)) : <span className="muted">Not booked</span>}</td>
                      <td className="small">{r.interviewer_id ? empById.get(r.interviewer_id)?.name ?? "" : <span className="muted">Not assigned</span>}</td>
                      <td className="small muted">{r.last_message_at ? relative(parseUtc(r.last_message_at)) : "No messages yet"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {open !== null && (
        <CandidateDrawer
          id={open}
          rounds={rounds.data ?? []}
          employees={people.data ?? []}
          simulator={!!health.data?.simulator}
          onClose={() => setOpen(null)}
          onChanged={refresh}
        />
      )}
    </div>
  );
}
