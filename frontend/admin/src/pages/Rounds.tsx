import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorText, fmtDay, parseUtc } from "@pp/shared";
import type { CandidateRow, Employee, Round } from "../types";
import { useLoad } from "../useLoad";

type CsvResult = { created: number; errors: { row: number; error: string }[] };

const TEMPLATE = "name,phone,consent,email\nRiya Verma,9876543210,yes,riya@example.com\n";
const today = () => new Date().toISOString().slice(0, 10);
const inDays = (n: number) => new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);

export default function Rounds() {
  const rounds = useLoad(() => api<Round[]>("/api/rounds"));
  const people = useLoad(() => api<Employee[]>("/api/employees"));
  const cands = useLoad(() => api<CandidateRow[]>("/api/candidates"));
  const [showForm, setShowForm] = useState(false);

  const interviewers = (people.data ?? []).filter((e) => e.active && e.is_interviewer);
  const name = (id: number) => people.data?.find((e) => e.id === id)?.name ?? `#${id}`;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Interview rounds</h1>
          <p className="summary">A round is one role and stage, with its interviewers and the dates candidates can pick from.</p>
        </div>
        <div className="head-actions">
          {!showForm && <button className="btn btn-primary" onClick={() => setShowForm(true)}>New round</button>}
        </div>
      </header>

      {showForm && (
        interviewers.length === 0 ? (
          <div className="card pad">
            <p>Add at least one interviewer before creating a round.</p>
            <Link className="btn btn-primary" to="/people">Add an interviewer</Link>
          </div>
        ) : (
          <NewRound interviewers={interviewers} onDone={() => { setShowForm(false); void rounds.reload(); }}
                    onCancel={() => setShowForm(false)} />
        )
      )}

      {rounds.error && <div className="notice notice-bad">{rounds.error}</div>}
      {rounds.data?.length === 0 && !showForm && (
        <div className="card empty">
          <h2>No rounds yet</h2>
          <p className="muted">Create your first round to start inviting candidates.</p>
        </div>
      )}

      <div className="round-list">
        {(rounds.data ?? []).map((r) => {
          const count = (cands.data ?? []).filter((c) => c.round_id === r.id).length;
          return (
            <article key={r.id} className="card round-card">
              <div className="round-main">
                <h2>{r.role_title}</h2>
                <div className="small muted">
                  {r.round_name} · {r.duration_min} min · {r.mode === "video" ? "Video" : "In person"}
                </div>
                <dl className="facts">
                  <div><dt>Dates</dt><dd className="num">{fmtDay(parseUtc(r.window_start))} to {fmtDay(parseUtc(r.window_end))}</dd></div>
                  <div><dt>Interviewers</dt><dd>{r.interviewer_ids.map(name).join(", ")}</dd></div>
                  <div><dt>Candidates</dt><dd className="num">{count}</dd></div>
                </dl>
              </div>
              <CsvUpload roundId={r.id} onDone={() => void cands.reload()} />
            </article>
          );
        })}
      </div>
    </div>
  );
}

function NewRound({ interviewers, onDone, onCancel }: { interviewers: Employee[]; onDone: () => void; onCancel: () => void }) {
  const [f, setF] = useState({
    role_title: "",
    round_name: "Round 1",
    duration_min: 30,
    buffer_min: 10,
    mode: "video",
    location: "",
    start_date: inDays(1),
    end_date: inDays(7),
    day_start_hour: 10,
    day_end_hour: 18,
    max_slots_offered: 3,
  });
  const [picked, setPicked] = useState<number[]>(interviewers.slice(0, 1).map((i) => i.id));
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f, num = false) => (e: { target: { value: string } }) =>
    setF({ ...f, [k]: num ? Number(e.target.value) : e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api("/api/rounds", { json: { ...f, interviewer_ids: picked } });
      onDone();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card pad form-grid" onSubmit={submit}>
      <h2 className="span-all">New round</h2>
      <label className="field span-2">
        <span>Role</span>
        <input className="input" required minLength={2} placeholder="Customer Support Associate" value={f.role_title} onChange={set("role_title")} />
      </label>
      <label className="field">
        <span>Round name</span>
        <input className="input" value={f.round_name} onChange={set("round_name")} />
      </label>
      <label className="field">
        <span>Length (minutes)</span>
        <input className="input" type="number" min={10} max={240} step={5} value={f.duration_min} onChange={set("duration_min", true)} />
      </label>
      <label className="field">
        <span>Format</span>
        {/* ds-allow-native-select: native is the better phone control; see design/DESIGN_RULES.md */}
        <select className="input" value={f.mode} onChange={set("mode")}>
          <option value="video">Video call</option>
          <option value="in_person">In person</option>
        </select>
      </label>
      <label className="field span-2">
        <span>{f.mode === "video" ? "Meeting link" : "Address"}</span>
        <input className="input" placeholder={f.mode === "video" ? "https://meet.google.com/…" : "Office address"} value={f.location} onChange={set("location")} />
      </label>
      <label className="field">
        <span>First day</span>
        <input className="input" type="date" min={today()} required value={f.start_date} onChange={set("start_date")} />
      </label>
      <label className="field">
        <span>Last day</span>
        <input className="input" type="date" min={f.start_date} required value={f.end_date} onChange={set("end_date")} />
      </label>
      <label className="field">
        <span>From (hour)</span>
        <input className="input" type="number" min={0} max={23} value={f.day_start_hour} onChange={set("day_start_hour", true)} />
      </label>
      <label className="field">
        <span>Until (hour)</span>
        <input className="input" type="number" min={1} max={24} value={f.day_end_hour} onChange={set("day_end_hour", true)} />
      </label>
      <label className="field">
        <span>Gap between interviews (min)</span>
        <input className="input" type="number" min={0} max={120} step={5} value={f.buffer_min} onChange={set("buffer_min", true)} />
      </label>
      <label className="field">
        <span>Slots to offer at once</span>
        <input className="input" type="number" min={1} max={9} value={f.max_slots_offered} onChange={set("max_slots_offered", true)} />
      </label>
      <fieldset className="field span-all chips">
        <span>Interviewers</span>
        <div className="chip-row">
          {interviewers.map((i) => (
            <label key={i.id} className={`chip${picked.includes(i.id) ? " is-on" : ""}`}>
              <input type="checkbox" checked={picked.includes(i.id)}
                     onChange={(e) => setPicked(e.target.checked ? [...picked, i.id] : picked.filter((x) => x !== i.id))} />
              {i.name}
            </label>
          ))}
        </div>
        <span className="hint">Candidates get a slot when any of these interviewers is free. Weekdays and Saturdays, in IST.</span>
      </fieldset>
      {err && <div className="notice notice-bad span-all" role="alert">{err}</div>}
      <div className="span-all form-actions">
        <button className="btn btn-primary" disabled={busy || picked.length === 0}>{busy ? "Creating…" : "Create round"}</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function CsvUpload({ roundId, onDone }: { roundId: number; onDone: () => void }) {
  const [res, setRes] = useState<CsvResult | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function upload(file: File) {
    setErr("");
    setRes(null);
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      setRes(await api<CsvResult>(`/api/rounds/${roundId}/candidates/csv`, { form }));
      onDone();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  const templateHref = `data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE)}`;

  return (
    <div className="csv-box">
      <h3>Add candidates</h3>
      <label className="btn btn-sm file-btn">
        {busy ? "Uploading…" : "Upload CSV"}
        <input type="file" accept=".csv,text/csv" disabled={busy}
               onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ""; }} />
      </label>
      <a className="small" href={templateHref} download="candidates-template.csv">Download template</a>
      <p className="hint">Columns: name, phone, consent (yes/no). Only people who said yes are added.</p>
      {err && <div className="notice notice-bad small">{err}</div>}
      {res && (
        <div className="small">
          <div className="notice notice-ok">Added {res.created} candidate{res.created === 1 ? "" : "s"}.</div>
          {res.errors.length > 0 && (
            <ul className="csv-errors">
              {res.errors.map((e) => <li key={e.row}>Row {e.row}: {e.error}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
