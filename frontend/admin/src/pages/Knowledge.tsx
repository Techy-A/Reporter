import { useState, type FormEvent } from "react";
import { api, errorText, fmtDayTime, parseUtc } from "@pp/shared";
import AnswerView from "../components/AnswerView";
import type { AskResult, EvalCase, Faq, Policy } from "../types";
import { useLoad } from "../useLoad";

type Tab = "policies" | "faqs" | "leave" | "checks";
const TABS: [Tab, string][] = [["policies", "Policies"], ["faqs", "FAQ answers"], ["leave", "Leave balances"],
  ["checks", "Try & check"]];

export default function Knowledge() {
  const [tab, setTab] = useState<Tab>("policies");
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Answers & policies</h1>
          <p className="summary">
            What the employee assistant knows. It answers only from active policies, your FAQ answers and the leave
            balances you upload, and it shows employees where each answer came from.
          </p>
        </div>
      </header>
      <div className="tabs" role="tablist">
        {TABS.map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={`tab${tab === k ? " is-on" : ""}`}
                  onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {tab === "policies" && <Policies />}
      {tab === "faqs" && <Faqs />}
      {tab === "leave" && <Leave />}
      {tab === "checks" && <Checks />}
    </div>
  );
}

// ------------------------------------------------------------------ policies
const STATUS = { draft: ["Draft", "pill-warn"], active: ["Active", "pill-ok"], superseded: ["Retired", ""] } as const;

function Policies() {
  const list = useLoad(() => api<Policy[]>("/api/policies"));
  const [openId, setOpenId] = useState<number | null>(null);
  const [err, setErr] = useState("");

  async function act(p: Policy, what: "activate" | "retire" | "delete") {
    setErr("");
    if (what === "delete" && !confirm(`Delete the draft "${p.title}" ${p.version}?`)) return;
    try {
      if (what === "delete") await api(`/api/policies/${p.id}`, { method: "DELETE" });
      else await api(`/api/policies/${p.id}/${what}`, { method: "POST" });
      await list.reload();
    } catch (x) {
      setErr(errorText(x));
    }
  }

  return (
    <>
      <PolicyUpload onDone={(id) => { void list.reload(); setOpenId(id); }} />
      <section className="card">
        {err && <div className="notice notice-bad">{err}</div>}
        <table className="table">
          <thead><tr><th>Policy</th><th>Applies to</th><th>Effective</th><th>Sections</th><th>Status</th><th /></tr></thead>
          <tbody>
            {(list.data ?? []).map((p) => (
              <tr key={p.id}>
                <td>
                  <button className="link-btn strong" onClick={() => setOpenId(openId === p.id ? null : p.id)}>{p.title}</button>
                  <div className="small muted mono">v{p.version} · {p.source_name}</div>
                </td>
                <td className="small">{audience(p)}</td>
                <td className="small num">{p.effective_from}</td>
                <td className="small num">{p.clause_count}{p.embedded > 0 && <span className="muted"> · {p.embedded} embedded</span>}</td>
                <td><span className={`pill ${STATUS[p.status][1]}`}>{STATUS[p.status][0]}</span></td>
                <td className="right nowrap">
                  {p.status !== "active" && <button className="btn btn-sm" onClick={() => act(p, "activate")}>Make live</button>}
                  {p.status === "active" && <button className="btn btn-ghost btn-sm" onClick={() => act(p, "retire")}>Retire</button>}
                  {p.status === "draft" && <button className="btn btn-ghost btn-sm btn-danger" onClick={() => act(p, "delete")}>Delete</button>}
                </td>
              </tr>
            ))}
            {list.data?.length === 0 && <tr><td colSpan={6} className="muted">No policies yet. Upload your leave policy to start.</td></tr>}
          </tbody>
        </table>
      </section>
      {openId && <PolicyClauses id={openId} />}
    </>
  );
}

const audience = (p: Policy) =>
  [p.locations.join(", "), p.grades.join(", "), p.employment_types.join(", ")].filter(Boolean).join(" · ") || "Everyone";

function PolicyUpload({ onDone }: { onDone: (id: number) => void }) {
  const [f, setF] = useState({ title: "", version: "", effective_from: new Date().toISOString().slice(0, 10),
    locations: "", grades: "", employment_types: "" });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setMsg(null);
    const form = new FormData();
    form.append("file", file);
    Object.entries(f).forEach(([k, v]) => form.append(k, v));
    try {
      const p = await api<Policy>("/api/policies", { form });
      setMsg({ ok: true, text: `Read ${p.clause_count} sections from ${p.source_name}. Check them below, then click "Make live".` });
      setFile(null);
      onDone(p.id);
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card pad" onSubmit={submit}>
      <h2>Upload a policy</h2>
      <div className="form-grid">
        <label className="field span-2"><span>Title</span>
          <input className="input" required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Leave Policy" /></label>
        <label className="field"><span>Version</span>
          <input className="input" required value={f.version} onChange={(e) => setF({ ...f, version: e.target.value })} placeholder="2026-01" /></label>
        <label className="field"><span>Effective from</span>
          <input className="input" type="date" required value={f.effective_from} onChange={(e) => setF({ ...f, effective_from: e.target.value })} /></label>
        <label className="field"><span>Locations</span>
          <input className="input" value={f.locations} onChange={(e) => setF({ ...f, locations: e.target.value })} placeholder="All, or Bengaluru, Pune" /></label>
        <label className="field"><span>Grades</span>
          <input className="input" value={f.grades} onChange={(e) => setF({ ...f, grades: e.target.value })} placeholder="All" /></label>
        <label className="field"><span>Employment types</span>
          <input className="input" value={f.employment_types} onChange={(e) => setF({ ...f, employment_types: e.target.value })} placeholder="All, or Contract" /></label>
        <label className="field"><span>File (.md, .txt or text .pdf)</span>
          <input className="input" type="file" required accept=".md,.markdown,.txt,.pdf"
                 onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
      </div>
      <p className="hint">Numbered headings like “4.2 Sick leave” become citable sections. Leave a filter empty to apply it to everyone.</p>
      <div className="form-actions">
        <button className="btn btn-primary" disabled={busy || !file}>{busy ? "Reading…" : "Upload as draft"}</button>
      </div>
      {msg && <div className={`notice ${msg.ok ? "notice-ok" : "notice-bad"}`}>{msg.text}</div>}
    </form>
  );
}

function PolicyClauses({ id }: { id: number }) {
  const p = useLoad(() => api<Policy>(`/api/policies/${id}`), [id]);
  if (!p.data) return null;
  return (
    <section className="card pad">
      <h2>{p.data.title} <span className="muted mono small">v{p.data.version}</span></h2>
      <p className="small muted">These are the sections employees will see cited. If a heading split looks wrong, fix the document and upload it again.</p>
      <ol className="clauses">
        {p.data.clauses?.map((c) => (
          <li key={c.id}>
            <div className="strong">{c.ref && <span className="clause-ref">§{c.ref}</span>}{c.heading || <span className="muted">(no heading)</span>}</div>
            <p className="small">{c.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ------------------------------------------------------------------ FAQ answers
function Faqs() {
  const list = useLoad(() => api<Faq[]>("/api/faqs"));
  const [f, setF] = useState({ question: "", answer: "" });
  const [editing, setEditing] = useState<number | null>(null);
  const [err, setErr] = useState("");

  async function save(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      if (editing) await api(`/api/faqs/${editing}`, { method: "PUT", json: { ...f, active: true } });
      else await api("/api/faqs", { json: f });
      setF({ question: "", answer: "" });
      setEditing(null);
      await list.reload();
    } catch (x) {
      setErr(errorText(x));
    }
  }
  async function remove(id: number) {
    if (!confirm("Delete this answer?")) return;
    await api(`/api/faqs/${id}`, { method: "DELETE" }).catch((x) => setErr(errorText(x)));
    await list.reload();
  }

  return (
    <>
      <form className="card pad" onSubmit={save}>
        <h2>{editing ? "Edit answer" : "Add an answer"}</h2>
        <p className="small muted">Your answer is used, word for word, whenever an employee asks something close to this question. It wins over the policies.</p>
        <label className="field"><span>Question</span>
          <input className="input" required value={f.question} onChange={(e) => setF({ ...f, question: e.target.value })}
                 placeholder="When is overtime credited?" /></label>
        <label className="field"><span>Answer</span>
          <textarea className="input" required rows={3} value={f.answer} onChange={(e) => setF({ ...f, answer: e.target.value })}
                    placeholder="Approved overtime is paid with the next month's salary." /></label>
        <div className="form-actions">
          <button className="btn btn-primary">{editing ? "Save" : "Add answer"}</button>
          {editing && <button type="button" className="btn btn-ghost" onClick={() => { setEditing(null); setF({ question: "", answer: "" }); }}>Cancel</button>}
        </div>
        {err && <div className="notice notice-bad">{err}</div>}
      </form>
      <section className="card">
        <table className="table">
          <thead><tr><th>Question</th><th>Answer</th><th /></tr></thead>
          <tbody>
            {(list.data ?? []).map((q) => (
              <tr key={q.id}>
                <td className="strong">{q.question}</td>
                <td className="small">{q.answer}</td>
                <td className="right nowrap">
                  <button className="btn btn-ghost btn-sm" onClick={() => { setEditing(q.id); setF({ question: q.question, answer: q.answer }); }}>Edit</button>
                  <button className="btn btn-ghost btn-sm btn-danger" onClick={() => remove(q.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {list.data?.length === 0 && <tr><td colSpan={3} className="muted">No FAQ answers yet.</td></tr>}
          </tbody>
        </table>
      </section>
    </>
  );
}

// ------------------------------------------------------------------ leave balances
const LEAVE_TEMPLATE = "email,leave_type,balance,as_of\npriya@acme.co.in,Casual,4,2026-11-01\npriya@acme.co.in,Sick,6,2026-11-01\n";

function Leave() {
  const sum = useLoad(() => api<{ employees: number; rows: number; latest_as_of: string | null }>("/api/leave-balances/summary"));
  return (
    <section className="card pad">
      <h2>Leave balances</h2>
      <p className="small muted">
        Export balances from Keka / your HR system and upload them here. Employees see only their own numbers,
        exactly as uploaded. No AI calculates leave.
      </p>
      {sum.data && (
        <dl className="facts">
          <div><dt>People</dt><dd className="num">{sum.data.employees}</dd></div>
          <div><dt>Rows</dt><dd className="num">{sum.data.rows}</dd></div>
          <div><dt>Latest “as of”</dt><dd className="num">{sum.data.latest_as_of ?? "Nothing uploaded"}</dd></div>
        </dl>
      )}
      <CsvButton path="/api/leave-balances/csv" label="Upload leave CSV" template={LEAVE_TEMPLATE}
                 templateName="leave-balances.csv" hint="Columns: email, leave_type, balance, as_of (YYYY-MM-DD). Re-uploading replaces each person's balance per leave type."
                 onDone={() => void sum.reload()} />
    </section>
  );
}

export function CsvButton({ path, label, template, templateName, hint, onDone }: {
  path: string; label: string; template: string; templateName: string; hint: string; onDone: () => void;
}) {
  const [res, setRes] = useState<{ imported: number; updated: number; errors: string[] } | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function upload(file: File) {
    setErr(""); setRes(null); setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      setRes(await api(path, { form }));
      onDone();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="csv-inline">
      <div className="head-actions">
        <label className="btn btn-sm file-btn">{busy ? "Uploading…" : label}
          <input type="file" accept=".csv,text/csv" disabled={busy}
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ""; }} />
        </label>
        <a className="small" href={`data:text/csv;charset=utf-8,${encodeURIComponent(template)}`} download={templateName}>Download template</a>
      </div>
      <p className="hint">{hint}</p>
      {err && <div className="notice notice-bad small">{err}</div>}
      {res && (
        <div className="small">
          <div className="notice notice-ok">Added {res.imported}, updated {res.updated}.</div>
          {res.errors.length > 0 && <ul className="csv-errors">{res.errors.map((e) => <li key={e}>{e}</li>)}</ul>}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ try & check (evals)
const ROUTES: [string, string][] = [["policy", "Policy answer"], ["faq", "HR's FAQ answer"], ["leave", "Leave balance"],
  ["no_answer", "Should go to HR"], ["sensitive", "Sensitive: a person"], ["agent", "AI using tools"]];

function Checks() {
  const [q, setQ] = useState({ question: "", location: "", grade: "", employment_type: "" });
  const [res, setRes] = useState<AskResult | null>(null);
  const [err, setErr] = useState("");
  const cases = useLoad(() => api<EvalCase[]>("/api/evals"));
  const [report, setReport] = useState<{ total: number; passed: number; sensitive_total: number; sensitive_routed: number } | null>(null);
  const [running, setRunning] = useState(false);
  const empty = { question: "", expect_route: "policy", expect_policy_title: "", expect_ref: "", must_include: "",
    as_location: "", as_grade: "", as_employment_type: "" };
  const [c, setC] = useState(empty);

  async function tryIt(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      setRes(await api<AskResult>("/api/helpdesk/try", { json: q }));
    } catch (x) {
      setErr(errorText(x));
    }
  }
  async function addCase(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api("/api/evals", { json: c });
      setC({ ...empty, expect_route: c.expect_route });
      await cases.reload();
    } catch (x) {
      setErr(errorText(x));
    }
  }
  async function run() {
    setRunning(true);
    try {
      setReport(await api("/api/evals/run", { method: "POST" }));
      await cases.reload();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setRunning(false);
    }
  }
  async function remove(id: number) {
    await api(`/api/evals/${id}`, { method: "DELETE" });
    await cases.reload();
  }

  return (
    <>
      <form className="card pad" onSubmit={tryIt}>
        <h2>Try a question</h2>
        <p className="small muted">See exactly what an employee with this profile would get. Nothing is recorded.</p>
        <div className="form-grid">
          <label className="field span-all"><span>Question</span>
            <input className="input" required value={q.question} onChange={(e) => setQ({ ...q, question: e.target.value })}
                   placeholder="Kya main sick aur casual leave club kar sakta hoon?" /></label>
          <label className="field"><span>As location</span><input className="input" value={q.location} onChange={(e) => setQ({ ...q, location: e.target.value })} placeholder="Any" /></label>
          <label className="field"><span>As grade</span><input className="input" value={q.grade} onChange={(e) => setQ({ ...q, grade: e.target.value })} placeholder="Any" /></label>
          <label className="field"><span>As type</span><input className="input" value={q.employment_type} onChange={(e) => setQ({ ...q, employment_type: e.target.value })} placeholder="Any" /></label>
          <div className="form-actions"><button className="btn btn-primary">Ask</button></div>
        </div>
        {res && <AnswerView r={res} />}
      </form>

      <section className="card pad">
        <div className="split">
          <div>
            <h2>Checks</h2>
            <p className="small muted">Questions with the answer you expect. Run them after every policy or FAQ change.</p>
          </div>
          <button className="btn btn-primary" onClick={run} disabled={running || !cases.data?.length}>
            {running ? "Running…" : "Run checks"}
          </button>
        </div>
        {report && (
          <div className={`notice ${report.passed === report.total ? "notice-ok" : "notice-bad"}`}>
            {report.passed} of {report.total} passed.
            {report.sensitive_total > 0 && ` Sensitive questions routed to a person: ${report.sensitive_routed} of ${report.sensitive_total}${report.sensitive_routed < report.sensitive_total ? ". Fix this before going live." : "."}`}
          </div>
        )}
        <form className="form-grid" onSubmit={addCase}>
          <label className="field span-2"><span>Question</span>
            <input className="input" required value={c.question} onChange={(e) => setC({ ...c, question: e.target.value })} placeholder="Can I club sick and casual leave?" /></label>
          <label className="field"><span>Expected</span>
            {/* ds-allow-native-select: native is the better phone control; see design/DESIGN_RULES.md */}
            <select className="input" value={c.expect_route} onChange={(e) => setC({ ...c, expect_route: e.target.value })}>
              {ROUTES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select></label>
          <label className="field"><span>Policy title</span><input className="input" value={c.expect_policy_title} onChange={(e) => setC({ ...c, expect_policy_title: e.target.value })} placeholder="Optional" /></label>
          <label className="field"><span>Section</span><input className="input" value={c.expect_ref} onChange={(e) => setC({ ...c, expect_ref: e.target.value })} placeholder="e.g. 4.2" /></label>
          <label className="field"><span>Must mention</span><input className="input" value={c.must_include} onChange={(e) => setC({ ...c, must_include: e.target.value })} placeholder="Optional phrase" /></label>
          <label className="field"><span>As location</span><input className="input" value={c.as_location} onChange={(e) => setC({ ...c, as_location: e.target.value })} placeholder="Any" /></label>
          <div className="form-actions"><button className="btn">Add check</button></div>
        </form>
        {err && <div className="notice notice-bad">{err}</div>}
        <table className="table">
          <thead><tr><th /><th>Question</th><th>Expected</th><th>Last result</th><th /></tr></thead>
          <tbody>
            {(cases.data ?? []).map((x) => (
              <tr key={x.id}>
                <td>{x.last_passed === null ? <span className="dot" /> : <span className={`dot ${x.last_passed ? "dot-ok" : "dot-bad"}`} aria-label={x.last_passed ? "passed" : "failed"} />}</td>
                <td className="strong">{x.question}</td>
                <td className="small">{ROUTES.find(([v]) => v === x.expect_route)?.[1]}{x.expect_policy_title && ` · ${x.expect_policy_title}`}{x.expect_ref && ` §${x.expect_ref}`}</td>
                <td className="small muted">{x.last_detail}{x.last_run_at && <> · {fmtDayTime(parseUtc(x.last_run_at))}</>}</td>
                <td className="right"><button className="btn btn-ghost btn-sm btn-danger" onClick={() => remove(x.id)}>Delete</button></td>
              </tr>
            ))}
            {cases.data?.length === 0 && <tr><td colSpan={5} className="muted">No checks yet. Add a few real questions your team gets every week, plus one sensitive one.</td></tr>}
          </tbody>
        </table>
      </section>
    </>
  );
}
