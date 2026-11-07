import { dayKey, fmtTime, localHour, parseUtc } from "@pp/shared";
import type { CandidateRow } from "../types";
import { STATUS } from "../types";

const START_H = 9;
const END_H = 19;
const DAYS = 7;
const HOURS = Array.from({ length: END_H - START_H + 1 }, (_, i) => START_H + i);
const BOOKED = new Set(["booked", "rescheduled", "confirmed", "attended", "no_show"]);

/** The week at a glance: one column per day, booked interviews placed at their time. */
export default function SlotRail({ rows, onOpen }: { rows: CandidateRow[]; onOpen: (id: number) => void }) {
  const today = new Date();
  const days = Array.from({ length: DAYS }, (_, i) => new Date(today.getTime() + i * 86400000));
  const byDay = new Map<string, CandidateRow[]>();
  for (const r of rows) {
    if (!r.booked_start || !BOOKED.has(r.status)) continue;
    const k = dayKey(parseUtc(r.booked_start));
    byDay.set(k, [...(byDay.get(k) ?? []), r]);
  }
  const span = END_H - START_H;

  return (
    <section className="slot-rail card" aria-label="Interviews this week">
      <div className="rail-hours" aria-hidden>
        {HOURS.map((h) => (
          <span key={h} style={{ top: `${((h - START_H) / span) * 100}%` }}>{String(h).padStart(2, "0")}</span>
        ))}
      </div>
      {days.map((d, i) => {
        const k = dayKey(d);
        const items = byDay.get(k) ?? [];
        const sunday = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "short" })
          .format(d) === "Sun";
        return (
          <div key={k} className={`rail-day${i === 0 ? " is-today" : ""}${sunday ? " is-off" : ""}`}>
            <div className="rail-day-head">
              <span className="rail-dow">
                {i === 0 ? "Today" : new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "short" }).format(d)}
              </span>
              <span className="rail-date num">
                {new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit" }).format(d)}
              </span>
              <span className="rail-count num" aria-label={`${items.length} interviews`}>{items.length || ""}</span>
            </div>
            <div className="rail-track">
              {HOURS.map((h) => (
                <i key={h} className="rail-line" style={{ top: `${((h - START_H) / span) * 100}%` }} />
              ))}
              {items.map((r) => {
                const t = parseUtc(r.booked_start!);
                const top = Math.min(Math.max((localHour(t) - START_H) / span, 0), 0.94) * 100;
                const tone = STATUS[r.status]?.tone || "ok";
                // Interviews that overlap in time (different interviewers) sit side by side.
                const near = items.filter((o) => Math.abs(parseUtc(o.booked_start!).getTime() - t.getTime()) < 30 * 60000);
                const lane = near.indexOf(r);
                const width = 100 / near.length;
                return (
                  <button
                    key={r.id}
                    className={`rail-slot tone-${tone}${near.length > 1 ? " is-split" : ""}`}
                    style={{ top: `${top}%`, left: `${lane * width}%`, width: `calc(${width}% - ${near.length > 1 ? 2 : 0}px)` }}
                    onClick={() => onOpen(r.id)}
                    title={`${r.name} · ${fmtTime(t)} · ${STATUS[r.status]?.label ?? r.status}`}
                  >
                    <span className="num">{fmtTime(t)}</span> {r.name.split(" ")[0]}
                  </button>
                );
              })}
              {sunday && items.length === 0 && <span className="rail-off-label">Off</span>}
            </div>
          </div>
        );
      })}
    </section>
  );
}
