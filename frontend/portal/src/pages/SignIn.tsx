import { useEffect, useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";

const RESEND_AFTER = 30;

export default function SignIn({ onSignedIn }: { onSignedIn: () => Promise<void> }) {
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  async function sendCode(e?: FormEvent) {
    e?.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const res = await api<{ detail: string; dev_code?: string }>("/api/auth/code", { json: { email } });
      setDevCode(res.dev_code ?? "");
      setStep("code");
      setCode("");
      setWait(RESEND_AFTER);
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
        <div className="p-brand">
          <span className="p-mark" aria-hidden>R</span>
          <span className="p-brand-name">Reporter</span>
          <span className="p-realm">Employee</span>
        </div>
        {step === "email" ? (
          <form onSubmit={sendCode} className="p-form">
            <h1>Interviewer sign-in</h1>
            <p className="muted">See the interviews you're running and mark who attended. We'll email you a 6-digit code, no password needed.</p>
            <label className="field">
              <span>Work email</span>
              <input className="input" type="email" required autoFocus value={email}
                     onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="you@company.com" />
            </label>
            {err && <div className="notice notice-bad" role="alert">{err}</div>}
            <button className="btn btn-primary big" disabled={busy}>{busy ? "Sending…" : "Email me a code"}</button>
          </form>
        ) : (
          <form onSubmit={verify} className="p-form">
            <h1>Enter your code</h1>
            <div className="p-sent">
              <span className="small">If this email is registered, a code is on its way. It works once and expires in 10 minutes.</span>
              <span className="p-sent-email">
                <b>{email}</b>
                <button type="button" className="btn btn-ghost btn-sm"
                        onClick={() => { setStep("email"); setCode(""); setErr(""); }}>Change</button>
              </span>
            </div>
            {devCode && (
              <div className="notice notice-info small">
                Dev mode (no email server): your code is <b className="mono">{devCode}</b>
              </div>
            )}
            <label className="field">
              <span>6-digit code</span>
              <div className="p-otp">
                {Array.from({ length: 6 }, (_, k) => (
                  <span key={k} className={`p-otp-cell mono${k === code.length ? " is-next" : ""}`} aria-hidden>{code[k] ?? ""}</span>
                ))}
                <input className="p-otp-input" required autoFocus inputMode="numeric" pattern="\d{6}" maxLength={6}
                       value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                       autoComplete="one-time-code" aria-label="6-digit code" />
              </div>
            </label>
            {err && <div className="notice notice-bad" role="alert">{err}</div>}
            <button className="btn btn-primary big" disabled={busy || code.length !== 6}>
              {busy ? "Checking…" : "Verify and sign in"}
            </button>
            <div className="p-resend small muted">
              Didn't get it?{" "}
              {wait > 0 ? <span className="mono">Resend in {wait}s</span>
                : <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => sendCode()}>Resend code</button>}
            </div>
          </form>
        )}
        <p className="trust p-auth-trust">Self-hosted · your data stays on your organisation's server</p>
      </div>
    </div>
  );
}
