import { useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";
import { useAuth } from "../auth";

export default function Setup() {
  const { refresh } = useAuth();
  const [f, setF] = useState({
    setup_token: "",
    org_name: "",
    org_kind: "company",
    email: "",
    password: "",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api("/api/setup", { json: { ...f, timezone: "Asia/Kolkata" } });
      await refresh();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card card" onSubmit={submit}>
        <div className="auth-brand"><span className="brand-mark">P</span> PeoplePilot Admin</div>
        <h1>Set up your workspace</h1>
        <p className="muted">You only do this once. You'll add two-factor sign-in on the next screen.</p>

        <label className="field">
          <span>Setup token</span>
          <input className="input mono" required value={f.setup_token} onChange={set("setup_token")}
                 autoComplete="off" />
          <span className="hint">The value of PP_SETUP_TOKEN in the server's .env file.</span>
        </label>
        <label className="field">
          <span>Organisation name</span>
          <input className="input" required minLength={2} value={f.org_name} onChange={set("org_name")} />
        </label>
        <label className="field">
          <span>What kind of organisation?</span>
          <select className="input" value={f.org_kind} onChange={set("org_kind")}>
            <option value="company">Company</option>
            <option value="staffing_agency">Staffing agency</option>
            <option value="placement_cell">College placement cell</option>
          </select>
        </label>
        <label className="field">
          <span>Your email</span>
          <input className="input" type="email" required value={f.email} onChange={set("email")}
                 autoComplete="username" />
        </label>
        <label className="field">
          <span>Password</span>
          <input className="input" type="password" required minLength={12} value={f.password}
                 onChange={set("password")} autoComplete="new-password" />
          <span className="hint">At least 12 characters. A short sentence works well.</span>
        </label>
        {err && <div className="notice notice-bad" role="alert">{err}</div>}
        <button className="btn btn-primary" disabled={busy}>{busy ? "Creating…" : "Create workspace"}</button>
      </form>
    </div>
  );
}
