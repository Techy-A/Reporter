import { api, fmtDayTime, parseUtc } from "@pp/shared";
import type { AuditRow } from "../types";
import { useLoad } from "../useLoad";

const ACTOR: Record<string, string> = { admin: "Admin", employee: "Employee", candidate: "Candidate", system: "System" };

export default function Activity() {
  const log = useLoad(() => api<AuditRow[]>("/api/audit?limit=300"));
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Activity log</h1>
          <p className="summary">Who did what, and when. Message content is never stored here. Entries are kept for one year.</p>
        </div>
      </header>
      {log.error && <div className="notice notice-bad">{log.error}</div>}
      <section className="card table-card">
        <div className="table-scroll">
          <table className="table">
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Record</th><th>Result</th></tr></thead>
            <tbody>
              {(log.data ?? []).map((a, i) => (
                <tr key={i}>
                  <td className="mono small">{fmtDayTime(parseUtc(a.at))}</td>
                  <td className="small">{ACTOR[a.actor_type] ?? a.actor_type}{a.actor_id ? <span className="muted"> #{a.actor_id}</span> : ""}</td>
                  <td className="small mono">{a.action}</td>
                  <td className="small muted">{a.record_type ? `${a.record_type} #${a.record_id}` : "—"}</td>
                  <td>{a.result === "ok" ? <span className="pill pill-ok">ok</span> : <span className="pill pill-bad">{a.result}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
