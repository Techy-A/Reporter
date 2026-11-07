import { useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";
import { useMe } from "../auth";
import type { Employee } from "../types";
import { useLoad } from "../useLoad";
import { CsvButton } from "./Knowledge";

const EMP_TEMPLATE = "name,email,location,grade,employment_type,interviewer\nPriya Sharma,priya@acme.co.in,Bengaluru,L2,Full-time,yes\n";
const BLANK = { name: "", email: "", location: "", grade: "", employment_type: "", is_interviewer: false };

export default function People() {
  const me = useMe();
  const people = useLoad(() => api<Employee[]>("/api/employees"));
  const [f, setF] = useState(BLANK);
  const [edit, setEdit] = useState<Employee | null>(null);
  const [err, setErr] = useState("");

  async function add(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api("/api/employees", { json: f });
      setF(BLANK);
      void people.reload();
    } catch (x) {
      setErr(errorText(x));
    }
  }

  async function saveEdit(e: FormEvent) {
    e.preventDefault();
    if (!edit) return;
    try {
      await api(`/api/employees/${edit.id}`, { method: "PATCH", json: {
        location: edit.location, grade: edit.grade, employment_type: edit.employment_type, is_interviewer: edit.is_interviewer } });
      setEdit(null);
      void people.reload();
    } catch (x) {
      setErr(errorText(x));
    }
  }

  async function deactivate(p: Employee) {
    if (!confirm(`Remove ${p.name}? They'll be signed out of the employee portal and won't get new interviews.`)) return;
    try {
      await api(`/api/employees/${p.id}/deactivate`, { method: "POST" });
      void people.reload();
    } catch (x) {
      setErr(errorText(x));
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>People</h1>
          <p className="summary">
            Everyone here can sign in to the separate employee portal with a code sent to their email, and ask HR
            questions there. Location, grade and type decide which policies apply to them. Interviewers also see
            their own interviews, never candidates' phone numbers.
          </p>
        </div>
      </header>

      <section className="card pad">
        <h2>Employees</h2>
        <form className="form-grid" onSubmit={add}>
          <label className="field"><span>Full name</span><input className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <label className="field"><span>Work email</span><input className="input" required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
          <label className="field"><span>Location</span><input className="input" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} placeholder="Bengaluru" /></label>
          <label className="field"><span>Grade</span><input className="input" value={f.grade} onChange={(e) => setF({ ...f, grade: e.target.value })} placeholder="L2" /></label>
          <label className="field"><span>Employment type</span><input className="input" value={f.employment_type} onChange={(e) => setF({ ...f, employment_type: e.target.value })} placeholder="Full-time" /></label>
          <label className="check"><input type="checkbox" checked={f.is_interviewer} onChange={(e) => setF({ ...f, is_interviewer: e.target.checked })} /> Interviewer</label>
          <div className="form-actions"><button className="btn btn-primary">Add person</button></div>
        </form>
        <CsvButton path="/api/employees/csv" label="Import CSV" template={EMP_TEMPLATE} templateName="employees.csv"
                   hint="Columns: name, email, location, grade, employment_type, interviewer (yes/no). Existing emails are updated."
                   onDone={() => void people.reload()} />
        {err && <div className="notice notice-bad">{err}</div>}
        <table className="table">
          <thead><tr><th>Name</th><th>Email</th><th>Location · grade · type</th><th>Role</th><th>Status</th><th /></tr></thead>
          <tbody>
            {(people.data ?? []).map((p) => edit?.id === p.id ? (
              <tr key={p.id}>
                <td className="strong">{p.name}</td>
                <td className="small">{p.email}</td>
                <td colSpan={2}>
                  <form className="inline-form" onSubmit={saveEdit}>
                    <input className="input" aria-label="Location" placeholder="Location" value={edit.location} onChange={(e) => setEdit({ ...edit, location: e.target.value })} />
                    <input className="input" aria-label="Grade" placeholder="Grade" value={edit.grade} onChange={(e) => setEdit({ ...edit, grade: e.target.value })} />
                    <input className="input" aria-label="Employment type" placeholder="Type" value={edit.employment_type} onChange={(e) => setEdit({ ...edit, employment_type: e.target.value })} />
                    <label className="check"><input type="checkbox" checked={edit.is_interviewer} onChange={(e) => setEdit({ ...edit, is_interviewer: e.target.checked })} /> Interviewer</label>
                    <button className="btn btn-sm btn-primary">Save</button>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => setEdit(null)}>Cancel</button>
                  </form>
                </td>
                <td /><td />
              </tr>
            ) : (
              <tr key={p.id}>
                <td className="strong">{p.name}</td>
                <td className="small">{p.email}</td>
                <td className="small">{[p.location, p.grade, p.employment_type].filter(Boolean).join(" · ") || <span className="muted">Not set: only company-wide policies apply</span>}</td>
                <td className="small">{p.is_interviewer ? "Interviewer" : "Employee"}</td>
                <td>{p.active ? <span className="pill pill-ok">Active</span> : <span className="pill">Removed</span>}</td>
                <td className="right nowrap">
                  {p.active && <button className="btn btn-ghost btn-sm" onClick={() => setEdit(p)}>Edit</button>}
                  {p.active && <button className="btn btn-ghost btn-sm btn-danger" onClick={() => deactivate(p)}>Remove</button>}
                </td>
              </tr>
            ))}
            {people.data?.length === 0 && <tr><td colSpan={6} className="muted">No one yet. Add people or import a CSV.</td></tr>}
          </tbody>
        </table>
      </section>

      {me.role === "owner" && <AdminUsers />}
    </div>
  );
}

function AdminUsers() {
  const [f, setF] = useState({ email: "", password: "", role: "recruiter" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/api/admin-users", { json: f });
      setMsg({ ok: true, text: `Added ${f.email}. They'll set up two-factor sign-in the first time they log in.` });
      setF({ email: "", password: "", role: "recruiter" });
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }

  return (
    <section className="card pad">
      <h2>Admin portal access</h2>
      <p className="muted small">Recruiters can manage rounds and candidates. Only owners can change settings and see the activity log.</p>
      <form className="inline-form" onSubmit={add}>
        <input className="input" type="email" required placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} aria-label="Email" />
        <input className="input" type="password" required minLength={12} placeholder="Temporary password (12+ characters)" value={f.password}
               onChange={(e) => setF({ ...f, password: e.target.value })} aria-label="Temporary password" autoComplete="new-password" />
        <select className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} aria-label="Role">
          <option value="recruiter">Recruiter</option>
          <option value="owner">Owner</option>
        </select>
        <button className="btn">Add admin</button>
      </form>
      {msg && <div className={`notice ${msg.ok ? "notice-ok" : "notice-bad"}`}>{msg.text}</div>}
    </section>
  );
}
