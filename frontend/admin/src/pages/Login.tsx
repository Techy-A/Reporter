import { useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";
import { useAuth } from "../auth";

type LoginOut = { mfa_required: boolean; mfa_setup_required: boolean };

export default function Login() {
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [askCode, setAskCode] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const out = await api<LoginOut>("/api/auth/login", {
        json: { email, password, ...(askCode ? { totp } : {}) },
      });
      if (out.mfa_required) {
        setAskCode(true);
        return;
      }
      await refresh();
    } catch (x) {
      setErr(errorText(x));
      setTotp("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card card" onSubmit={submit}>
        <div className="auth-brand"><span className="brand-mark">P</span> PeoplePilot Admin</div>
        <h1>Sign in</h1>
        {!askCode ? (
          <>
            <label className="field">
              <span>Email</span>
              <input className="input" type="email" required autoFocus value={email}
                     onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
            </label>
            <label className="field">
              <span>Password</span>
              <input className="input" type="password" required value={password}
                     onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </label>
          </>
        ) : (
          <label className="field">
            <span>6-digit code from your authenticator app</span>
            <input className="input mono code-input" required autoFocus inputMode="numeric" pattern="\d{6}"
                   maxLength={6} value={totp} onChange={(e) => setTotp(e.target.value.replace(/\D/g, ""))}
                   autoComplete="one-time-code" />
          </label>
        )}
        {err && <div className="notice notice-bad" role="alert">{err}</div>}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Checking…" : askCode ? "Verify and sign in" : "Continue"}
        </button>
        {askCode && (
          <button type="button" className="btn btn-ghost" onClick={() => { setAskCode(false); setTotp(""); }}>
            Use a different account
          </button>
        )}
        <p className="trust">Admin portal · office network or VPN only</p>
      </form>
    </div>
  );
}
