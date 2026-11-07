import { useCallback, useEffect, useState } from "react";
import { api, dayKey, errorText, fmtDay, fmtTime, parseUtc } from "@pp/shared";
import type { Me } from "../main";

type Interview = {
  id: number;
  candidate_first_name: string;
  role_title: string;
  round_name: string;
  start: string;
  duration_min: number;
  mode: "video" | "in_person";
  location: string;
  status: string;
};

type Filter = "all" | "feedback" | "today";

const STATUS: Record<string, { label: string; tone: string }> = {
  booked: { label: "Booked", tone: "info" },
  rescheduled: { label: "Rescheduled", tone: "info" },
  confirmed: { label: "Confirmed", tone: "ok" },
  attended: { label: "Attended", tone: "ok" },
  no_show: { label: "No-show", tone: "bad" },
  needs_recruiter: { label: "With recruiter", tone: "warn" },
  cancelled: { label: "Cancelled", tone: "bad" },
};

const endOf = (i: Interview) => parseUtc(i.start).getTime() + i.duration_min * 60000;
const isDone = (i: Interview) => i.status === "attended" || i.status === "no_show";

function useMinuteTick() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);
  return now;
}

export default function MyInterviews({ me }: { me: Me }) {
  const [items, setItems] = useState<Interview[] | null>(null);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [saving, setSaving] = useState<number | null>(null);
  const now = useMinuteTick();

  const load = useCallback(async () => {
    try {
      setItems(await api<Interview[]>("/api/me/interviews"));
      setErr("");
    } catch (e) {
      setErr(errorText(e));
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  async function mark(id: number, outcome: "attended" | "no_show") {
    setSaving(id);
    try {
      await api(`/api/me/interviews/${id}/outcome`, { json: { outcome } });
      await load();
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setSaving(null);
    }
  }

  const all = items ?? [];
  const t = now.getTime();
  const todayKey = dayKey(now);
  const needsAction = all.filter((i) => endOf(i) < t && !isDone(i) && i.status !== "cancelled").reverse();
  const upcoming = all.filter((i) => endOf(i) >= t && i.status !== "cancelled");
  const today = upcoming.filter((i) => dayKey(parseUtc(i.start)) === todayKey);
  const done = all.filter((i) => endOf(i) < t && isDone(i)).reverse();

  const showAction = filter !== "today";
  const showUpcoming = filter !== "feedback";
  const upcomingList = filter === "today" ? today : upcoming;
  const groups = new Map<string, Interview[]>();
  for (const i of upcomingList) {
    const k = dayKey(parseUtc(i.start));
    groups.set(k, [...(groups.get(k) ?? []), i]);
  }

  const initials = me.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="p-page">
      <div className="p-title">
        <div>
          <h1>My interviews</h1>
          <p className="small muted">
            {new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "long", day: "numeric", month: "short" }).format(now)} · IST
          </p>
        </div>
        {items && <span className="pill pill-ok">{upcoming.length} scheduled</span>}
      </div>

      <section className="p-me">
        <span className="p-avatar" aria-hidden>{initials}</span>
        <div>
          <div className="p-me-name">{me.name}</div>
          <div className="small muted">Interviewer · {me.organisation}</div>
        </div>
      </section>

      <div className="p-chips" role="group" aria-label="Show">
        {([
          ["all", "All", upcoming.length + needsAction.length],
          ["feedback", "Needs feedback", needsAction.length],
          ["today", "Today", today.length],
        ] as const).map(([k, label, n]) => (
          <button key={k} className={`p-chip${filter === k ? " is-on" : ""}`} aria-pressed={filter === k}
                  onClick={() => setFilter(k)}>
            {label} <span className="p-chip-n">{n}</span>
          </button>
        ))}
      </div>

      {err && <div className="notice notice-bad" role="alert">{err}</div>}
      {items === null && !err && <p className="muted">Loading your interviews…</p>}

      {showAction && needsAction.length > 0 && (
        <section className="p-section">
          <div className="p-section-head"><h3 className="dot-warn">Needs your action</h3></div>
          {needsAction.map((i) => (
            <Card key={i.id} i={i} now={now} badge={<span className="pill pill-warn">Ended {fmtAgo(t - endOf(i))}</span>}>
              <div className="p-verify">
                <span className="small muted">Did the candidate attend?</span>
                <div className="p-verify-btns">
                  <button className="btn p-btn-ink" disabled={saving === i.id} onClick={() => mark(i.id, "attended")}>
                    Attended
                  </button>
                  <button className="btn p-btn-soft-bad" disabled={saving === i.id} onClick={() => mark(i.id, "no_show")}>
                    No-show
                  </button>
                </div>
                <p className="small muted p-note">This goes straight to the recruiter's board. Nothing else is recorded.</p>
              </div>
            </Card>
          ))}
        </section>
      )}

      {showUpcoming && (
        <section className="p-section">
          <div className="p-section-head">
            <h3 className="dot-ok">Upcoming</h3>
          </div>
          {items && upcomingList.length === 0 && (
            <div className="p-empty">
              {filter === "today" ? "Nothing left today." : "No upcoming interviews. New bookings appear here as candidates pick slots."}
            </div>
          )}
          {[...groups.entries()].map(([k, list]) => (
            <div key={k} className="p-group">
              <div className="p-group-day small">{k === todayKey ? "Today" : fmtDay(parseUtc(list[0].start))}</div>
              {list.map((i) => <Card key={i.id} i={i} now={now} upcoming />)}
            </div>
          ))}
        </section>
      )}

      {filter === "all" && done.length > 0 && (
        <section className="p-section">
          <div className="p-section-head"><h3>Done this week</h3></div>
          {done.map((i) => (
            <div key={i.id} className="p-done">
              <span className="p-done-name">{i.candidate_first_name}</span>
              <span className="small muted">{fmtDay(parseUtc(i.start))} · {fmtTime(parseUtc(i.start))}</span>
              <StatusPill s={i.status} />
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function fmtAgo(ms: number) {
  const m = Math.round(ms / 60000);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

function StatusPill({ s }: { s: string }) {
  const st = STATUS[s] ?? { label: s, tone: "info" };
  return <span className={`pill pill-${st.tone}`}>{st.label}</span>;
}

function Card({ i, now, upcoming, badge, children }: {
  i: Interview; now: Date; upcoming?: boolean; badge?: React.ReactNode; children?: React.ReactNode;
}) {
  const start = parseUtc(i.start);
  const end = new Date(start.getTime() + i.duration_min * 60000);
  const isLink = i.mode === "video" && /^https:\/\//.test(i.location);
  const mins = Math.round((start.getTime() - now.getTime()) / 60000);
  const live = upcoming && mins <= 0;
  const soon = upcoming && mins > 0 && mins <= 120;

  let when: React.ReactNode = badge;
  if (upcoming) {
    when = live ? <span className="pill pill-bad">In progress</span>
      : soon ? <span className="pill pill-warn">Starts in {mins < 60 ? `${mins} min` : `${Math.floor(mins / 60)} h ${mins % 60} min`}</span>
      : <span className="pill">{fmtTime(start)}</span>;
  }

  return (
    <article className={`p-card2${live || soon ? " is-soon" : ""}`}>
      <div className="p-card2-top">
        {when}
        {upcoming && <StatusPill s={i.status} />}
      </div>
      <div className="p-cand">
        <span className="p-cand-name">{i.candidate_first_name}</span>
        <span className="p-ref mono">#{i.id}</span>
      </div>
      <div className="p-role">{i.role_title}</div>
      <div className="small muted">{i.round_name}</div>

      <div className="p-where-box">
        <div className="p-where-row">
          <span className="p-where-kind">{i.mode === "video" ? "Video call" : "In person"}</span>
          <span className="num small">{fmtTime(start)} to {fmtTime(end)}</span>
        </div>
        {i.location && !isLink && <div className="small p-where-loc">{i.location}</div>}
      </div>

      {upcoming && (
        <div className="p-actions">
          {isLink && (
            <a className="btn btn-primary p-join" href={i.location} target="_blank" rel="noopener noreferrer">
              Join call
            </a>
          )}
          <a className={`btn${isLink ? " p-ics-icon" : " p-ics"}`} href={`/api/me/interviews/${i.id}.ics`}
             aria-label="Add to my calendar (.ics)" title="Add to my calendar (.ics)">
            <CalIcon />{!isLink && <span>Add to calendar (.ics)</span>}
          </a>
        </div>
      )}
      {children}
    </article>
  );
}

function CalIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18M12 14v4M10 16h4" />
    </svg>
  );
}
