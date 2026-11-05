import { useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";

export default function SignIn({ onSignedIn }: { onSignedIn: () => Promise<void> }) {
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendCode(e?: FormEvent) {
    e?.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const res = await api<{ detail: string; dev_code?: string }>("/api/auth/code", { json: { email } });
      setDevCode(res.dev_code ?? "");
      setStep("code");
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api("/api/auth/verify", { json: { email, code } });
      await onSignedIn();
    } catch (x) {
      setErr(errorText(x));
      setCode("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-auth">
      <div className="p-auth-card">
        <div className="p-brand"><span className="p-mark" aria-hidden>P</span><span>PeoplePilot</span></div>
        {step === "email" ? (
          <form onSubmit={sendCode} className="p-form">
            <h1>Sign in</h1>
            <p className="muted">We'll email you a 6-digit code. No password needed.</p>
            <label className="field">
              <span>Work email</span>
              <input className="input" type="email" required autoFocus value={email}
                     onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            </label>
            {err && <div className="notice notice-bad" role="alert">{err}</div>}
            <button className="btn btn-primary big" disabled={busy}>{busy ? "Sending…" : "Email me a code"}</button>
          </form>
        ) : (
          <form onSubmit={verify} className="p-form">
            <h1>Check your email</h1>
            <p className="muted">If <b>{email}</b> is registered, a code is on its way. It expires in 10 minutes.</p>
            {devCode && (
              <div className="notice notice-info small">
                Dev mode (no email server): your code is <b className="mono">{devCode}</b>
              </div>
            )}
            <label className="field">
              <span>6-digit code</span>
              <input className="input mono p-code" required autoFocus inputMode="numeric" pattern="\d{6}" maxLength={6}
                     value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} autoComplete="one-time-code" />
            </label>
            {err && <div className="notice notice-bad" role="alert">{err}</div>}
            <button className="btn btn-primary big" disabled={busy || code.length !== 6}>{busy ? "Checking…" : "Sign in"}</button>
            <button type="button" className="btn btn-ghost" onClick={() => { setStep("email"); setCode(""); setErr(""); }}>
              Use a different email
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
