/** The backend sends naive UTC timestamps. Display everything in the organisation's zone (IST). */
export const TZ = "Asia/Kolkata";

export function parseUtc(s: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(s) ? s : s + "Z");
}

const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-IN", { timeZone: TZ, ...o });
const dayFmt = fmt({ weekday: "short", day: "numeric", month: "short" });
const timeFmt = fmt({ hour: "2-digit", minute: "2-digit", hour12: false });
const keyFmt = fmt({ year: "numeric", month: "2-digit", day: "2-digit" });
const hourFmt = fmt({ hour: "numeric", hour12: false });
const minFmt = fmt({ minute: "numeric" });

export const fmtDay = (d: Date) => dayFmt.format(d);
export const fmtTime = (d: Date) => timeFmt.format(d);
export const fmtDayTime = (d: Date) => `${dayFmt.format(d)}, ${timeFmt.format(d)}`;
export const dayKey = (d: Date) => keyFmt.format(d);
/** Hours since local midnight, e.g. 14.5 for 14:30 IST. */
export const localHour = (d: Date) => Number(hourFmt.format(d)) % 24 + Number(minFmt.format(d)) / 60;

export function relative(d: Date): string {
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h} h ago`;
  return fmtDay(d);
}
