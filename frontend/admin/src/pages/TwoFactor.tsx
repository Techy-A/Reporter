import { useEffect, useRef, useState, type FormEvent } from "react";
import QRCode from "qrcode";
import { api, errorText } from "@pp/shared";
import { useAuth } from "../auth";

export default function TwoFactor() {
  const { refresh } = useAuth();
  const [uri, setUri] = useState("");
  const [qr, setQr] = useState("");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    api<{ otpauth_uri: string }>("/api/auth/mfa/setup", { method: "POST" })
      .then(async ({ otpauth_uri }) => {
        setUri(otpauth_uri);
        setQr(await QRCode.toDataURL(otpauth_uri, { margin: 1, width: 200 }));
      })
      .catch((e) => setErr(errorText(e)));
  }, []);

  const secret = uri ? new URL(uri).searchParams.get("secret") ?? "" : "";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api("/api/auth/mfa/confirm", { json: { code } });
      await refresh();
    } catch (x) {
      setErr(errorText(x));
      setCode("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card card" onSubmit={submit}>
        <div className="auth-brand"><span className="brand-mark">P</span> PeoplePilot Admin</div>
        <h1>Turn on two-factor sign-in</h1>
        <p className="muted">
          Admins can see candidate data, so every admin account needs a second step. Use any free
          authenticator app (Google Authenticator, Microsoft Authenticator, Aegis).
        </p>
        <div className="qr-row">
          {qr ? <img src={qr} alt="QR code to add PeoplePilot to your authenticator app" width={160} height={160} />
              : <div className="qr-ph" />}
          <div className="small">
            <div className="muted">Can't scan? Enter this key:</div>
            <code className="mono secret">{secret.replace(/(.{4})/g, "$1 ").trim()}</code>
          </div>
        </div>
        <label className="field">
          <span>6-digit code from the app</span>
          <input className="input mono code-input" required inputMode="numeric" pattern="\d{6}" maxLength={6}
                 value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                 autoComplete="one-time-code" />
        </label>
        {err && <div className="notice notice-bad" role="alert">{err}</div>}
        <button className="btn btn-primary" disabled={busy || !uri}>{busy ? "Checking…" : "Turn on and continue"}</button>
      </form>
    </div>
  );
}
