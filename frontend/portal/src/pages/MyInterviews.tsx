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

export default function MyInterviews({ me }: { me: Me }) {
  const [items, setItems] = useState<Interview[] | null>(null);
  const [err, setErr] = useState("");

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
    try {
      await api(`/api/me/interviews/${id}/outcome`, { json: { outcome } });
      await load();
    } catch (e) {
      setErr(errorText(e));
    }
  }

  const now = new Date();
  const upcoming = (items ?? []).filter((i) => parseUtc(i.start).getTime() + i.duration_min * 60000 >= now.getTime());
  const past = (items ?? []).filter((i) => !upcoming.includes(i)).reverse();
  const groups = new Map<string, Interview[]>();
  for (const i of upcoming) {
    const k = dayKey(parseUtc(i.start));
    groups.set(k, [...(groups.get(k) ?? []), i]);
  }
  const todayKey = dayKey(now);

  return (
    <div className="p-page">
      <h1>Hi {me.name.split(" ")[0]}</h1>
      <p className="muted">
        {items === null ? "Loading your interviews…"
          : upcoming.length === 0 ? "You have no upcoming interviews."
          : `You have ${upcoming.length} upcoming interview${upcoming.length === 1 ? "" : "s"}.`}
      </p>
      {err && <div className="notice notice-bad">{err}</div>}

      {[...groups.entries()].map(([k, list]) => (
        <section key={k} className="p-day">
          <h3>{k === todayKey ? "Today" : fmtDay(parseUtc(list[0].start))}</h3>
          {list.map((i) => <Ticket key={i.id} i={i} />)}
        </section>
      ))}

      {past.length > 0 && (
        <section className="p-day">
          <h3>Earlier this week</h3>
          {past.map((i) => (
            <Ticket key={i.id} i={i} past>
              {["attended", "no_show"].includes(i.status) ? (
                <span className={`pill ${i.status === "attended" ? "pill-ok" : "pill-bad"}`}>
                  {i.status === "attended" ? "Attended" : "No-show"}
                </span>
              ) : (
                <div className="p-outcome">
                  <span className="small muted">Did they attend?</span>
                  <button className="btn btn-sm" onClick={() => mark(i.id, "attended")}>Attended</button>
                  <button className="btn btn-sm" onClick={() => mark(i.id, "no_show")}>No-show</button>
                </div>
              )}
            </Ticket>
          ))}
        </section>
      )}
    </div>
  );
}

function Ticket({ i, past, children }: { i: Interview; past?: boolean; children?: React.ReactNode }) {
  const start = parseUtc(i.start);
  const end = new Date(start.getTime() + i.duration_min * 60000);
  const isLink = i.mode === "video" && /^https:\/\//.test(i.location);
  return (
    <article className={`p-ticket${past ? " is-past" : ""}`}>
      <div className="p-time">
        <span className="mono p-time-start">{fmtTime(start)}</span>
        <span className="mono small muted">{fmtTime(end)}</span>
      </div>
      <div className="p-body">
        <div className="p-who">{i.candidate_first_name}</div>
        <div className="small muted">{i.role_title} · {i.round_name}</div>
        <div className="small p-where">
          {i.mode === "video" ? "Video call" : "In person"}
          {i.location && (isLink
            ? <> · <a href={i.location} target="_blank" rel="noopener noreferrer">Join link</a></>
            : <> · {i.location}</>)}
        </div>
        {!past && (
          <a className="btn btn-sm p-ics" href={`/api/me/interviews/${i.id}.ics`}>Add to my calendar</a>
        )}
        {children}
      </div>
    </article>
  );
}
