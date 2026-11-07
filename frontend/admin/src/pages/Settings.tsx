import { useState, type FormEvent } from "react";
import { api, errorText } from "@pp/shared";
import { useMe } from "../auth";
import type { Health } from "../types";
import { useLoad } from "../useLoad";

type ChannelOut = { kind: string; configured: boolean; webhook_path: string | null; webhook_secret: string | null };

export default function Settings() {
  const me = useMe();
  const health = useLoad(() => api<Health>("/api/health"));
  const h = health.data;
  const owner = me.role === "owner";

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="summary">Connections, the emergency stop, and how this install is running.</p>
        </div>
      </header>

      {h && (
        <section className="card pad">
          <h2>Status</h2>
          <ul className="status-list">
            <Row ok={h.database} label="Database" detail={h.database ? "Connected" : "Not reachable"} />
            <Row ok={h.channels.telegram || h.simulator} label="Telegram" detail={h.channels.telegram ? "Connected" : "Not connected"} />
            <Row ok={h.channels.whatsapp || h.simulator} label="WhatsApp" detail={h.channels.whatsapp ? "Connected" : "Not connected (optional)"} />
            <Row ok label="AI for free-text replies"
                 detail={h.llm_configured ? "On" : "Off. Buttons and common phrases still work. Add a local Ollama model for free if you want it."} />
            <Row ok={!h.messaging_paused} label="Outgoing messages" detail={h.messaging_paused ? "Paused" : "On"} />
            {h.simulator && <Row ok label="Simulator" detail="On. Messages stay inside the app (dev mode)." />}
          </ul>
        </section>
      )}

      {owner ? (
        <>
          <PauseSwitch paused={!!h?.messaging_paused} onDone={() => void health.reload()} />
          <HelpdeskContacts />
          <TelegramForm onDone={() => void health.reload()} />
          <WhatsAppForm onDone={() => void health.reload()} />
        </>
      ) : (
        <p className="muted">Only owners can change settings.</p>
      )}
    </div>
  );
}

function Row({ ok, label, detail }: { ok: boolean; label: string; detail: string }) {
  return (
    <li>
      <span className={`dot ${ok ? "dot-ok" : "dot-warn"}`} aria-hidden />
      <span className="strong">{label}</span>
      <span className="muted small">{detail}</span>
    </li>
  );
}

function HelpdeskContacts() {
  const cur = useLoad(() => api<{ ic_contact: string; hr_contact: string }>("/api/settings/helpdesk"));
  const [f, setF] = useState<{ ic_contact: string; hr_contact: string } | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const v = f ?? cur.data ?? { ic_contact: "", hr_contact: "" };

  async function save(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/api/settings/helpdesk", { method: "PUT", json: v });
      setMsg({ ok: true, text: "Saved." });
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }

  return (
    <form className="card pad" onSubmit={save}>
      <h2>Sensitive-topic contacts</h2>
      <p className="small muted">
        When an employee writes about harassment (POSH), self-harm or a legal issue, the assistant stops and shows
        these contacts instead of answering. Free national helplines (Tele-MANAS 14416, emergency 112) are always shown.
      </p>
      <div className="form-grid">
        <label className="field span-2"><span>Internal Committee (POSH) contact</span>
          <input className="input" value={v.ic_contact} onChange={(e) => setF({ ...v, ic_contact: e.target.value })}
                 placeholder="Meera Iyer, Presiding Officer · ic@acme.co.in · ext 2104" /></label>
        <label className="field span-2"><span>HR contact</span>
          <input className="input" value={v.hr_contact} onChange={(e) => setF({ ...v, hr_contact: e.target.value })}
                 placeholder="hr@acme.co.in · 080 4000 1234" /></label>
      </div>
      <div className="form-actions"><button className="btn btn-primary">Save contacts</button></div>
      {msg && <div className={`notice ${msg.ok ? "notice-ok" : "notice-bad"}`}>{msg.text}</div>}
    </form>
  );
}

function PauseSwitch({ paused, onDone }: { paused: boolean; onDone: () => void }) {
  const [err, setErr] = useState("");
  async function toggle() {
    if (!paused && !confirm("Stop all outgoing messages to candidates now?")) return;
    try {
      await api("/api/settings/pause", { json: { paused: !paused } });
      onDone();
    } catch (x) {
      setErr(errorText(x));
    }
  }
  return (
    <section className="card pad split">
      <div>
        <h2>Emergency stop</h2>
        <p className="muted small">Stops every message the assistant would send, including reminders. Use it if something looks wrong.</p>
        {err && <div className="notice notice-bad">{err}</div>}
      </div>
      <button className={`btn ${paused ? "btn-primary" : "btn-danger"}`} onClick={toggle}>
        {paused ? "Turn messages back on" : "Pause all messages"}
      </button>
    </section>
  );
}

function TelegramForm({ onDone }: { onDone: () => void }) {
  const [f, setF] = useState({ bot_token: "", bot_username: "" });
  const [out, setOut] = useState<ChannelOut | null>(null);
  const [err, setErr] = useState("");

  async function save(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      setOut(await api<ChannelOut>("/api/settings/channel", { method: "PUT", json: { kind: "telegram", ...f } }));
      setF({ bot_token: "", bot_username: "" });
      onDone();
    } catch (x) {
      setErr(errorText(x));
    }
  }

  return (
    <section className="card pad">
      <h2>Telegram <span className="pill pill-ok">Free</span></h2>
      <p className="muted small">
        Create a bot by messaging <span className="mono">@BotFather</span> in Telegram, then paste its token here.
        Candidates open a link you share and book from there.
      </p>
      <form className="inline-form" onSubmit={save}>
        <input className="input mono" required placeholder="Bot token" value={f.bot_token}
               onChange={(e) => setF({ ...f, bot_token: e.target.value })} aria-label="Bot token" autoComplete="off" />
        <input className="input" required placeholder="Bot username (without @)" value={f.bot_username}
               onChange={(e) => setF({ ...f, bot_username: e.target.value.replace(/^@/, "") })} aria-label="Bot username" />
        <button className="btn btn-primary">Save</button>
      </form>
      {err && <div className="notice notice-bad">{err}</div>}
      {out?.webhook_secret && (
        <div className="notice notice-info small">
          Saved. Point the bot at your webhook once (this secret is shown only now):
          <pre className="mono codeblock">{`https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-domain>${out.webhook_path}&secret_token=${out.webhook_secret}`}</pre>
        </div>
      )}
    </section>
  );
}

function WhatsAppForm({ onDone }: { onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ phone_number_id: "", access_token: "", app_secret: "", verify_token: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function save(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      const out = await api<ChannelOut>("/api/settings/channel", { method: "PUT", json: { kind: "whatsapp", ...f } });
      setMsg({ ok: true, text: `Saved. Webhook path: ${out.webhook_path}` });
      setF({ phone_number_id: "", access_token: "", app_secret: "", verify_token: "" });
      onDone();
    } catch (x) {
      setMsg({ ok: false, text: errorText(x) });
    }
  }

  return (
    <section className="card pad">
      <div className="split">
        <div>
          <h2>WhatsApp <span className="pill">Optional</span></h2>
          <p className="muted small">
            Meta's free test number can message up to 5 phone numbers you verify, with no business verification needed.
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => setOpen(!open)}>{open ? "Hide" : "Connect WhatsApp"}</button>
      </div>
      {open && (
        <form className="form-grid" onSubmit={save}>
          {(["phone_number_id", "access_token", "app_secret", "verify_token"] as const).map((k) => (
            <label key={k} className="field">
              <span>{k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}</span>
              <input className="input mono" required value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} autoComplete="off" />
            </label>
          ))}
          <div className="span-all"><button className="btn btn-primary">Save</button></div>
        </form>
      )}
      {msg && <div className={`notice ${msg.ok ? "notice-ok" : "notice-bad"}`}>{msg.text}</div>}
    </section>
  );
}
