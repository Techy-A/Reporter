import { STATUS } from "../types";

export default function StatusPill({ status }: { status: string }) {
  const s = STATUS[status] ?? { label: status, tone: "" };
  return <span className={`pill${s.tone ? ` pill-${s.tone}` : ""}`}>{s.label}</span>;
}
