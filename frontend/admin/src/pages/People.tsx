import { useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";
import { useMe } from "../auth";
import type { Employee } from "../types";
import { useLoad } from "../useLoad";

export default function People() {
  const me = useMe();
  const people = useLoad(() => api<Employee[]>("/api/employees"));
  const [f, setF] = useState({ name: "", email: "" });
  const [err, setErr] = useState("");

  async function add(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api("/api/employees", { json: { ...f, is_interviewer: true } });
      setF({ name: "", email: "" });
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
          <h1>Interviewers & team</h1>
          <p className="summary">
            Interviewers sign in to the separate employee portal with a code sent to their email. They see only
            their own interviews, never candidates' phone numbers.
          </p>
        </div>
      </header>

      <section className="card pad">
        <h2>Interviewers</h2>
        <form className="inline-form" onSubmit={add}>
          <input className="input" required placeholder="Full name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} aria-label="Name" />
          <input className="input" required type="email" placeholder="Work email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} aria-label="Email" />
          <button className="btn btn-primary">Add interviewer</button>
        </form>
        {err && <div className="notice notice-bad">{err}</div>}
        <table className="table">
          <thead><tr><th>Name</th><th>Email</th><th>Status</th><th /></tr></thead>
          <tbody>
            {(people.data ?? []).map((p) => (
              <tr key={p.id}>
                <td className="strong">{p.name}</td>
                <td className="small">{p.email}</td>
                <td>{p.active ? <span className="pill pill-ok">Active</span> : <span className="pill">Removed</span>}</td>
                <td className="right">{p.active && <button className="btn btn-ghost btn-sm btn-danger" onClick={() => deactivate(p)}>Remove</button>}</td>
              </tr>
            ))}
            {people.data?.length === 0 && <tr><td colSpan={4} className="muted">No interviewers yet.</td></tr>}
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
