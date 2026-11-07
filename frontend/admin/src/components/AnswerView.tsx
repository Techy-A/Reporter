import type { AskResult } from "../types";

const KIND: Record<AskResult["kind"], { label: string; tone: string }> = {
  sensitive: { label: "Handed to a person", tone: "warn" },
  faq: { label: "HR's own answer", tone: "ok" },
  leave: { label: "From HR's leave records", tone: "ok" },
  policy_answer: { label: "AI answer, checked against policy", tone: "info" },
  policy_quote: { label: "Quoted from policy", tone: "info" },
  tool_answer: { label: "AI answer from HR records", tone: "info" },
  no_answer: { label: "Not in policies: goes to HR", tone: "bad" },
};

/** How an answer looks, with where it came from. Used by "Try a question". */
export default function AnswerView({ r }: { r: AskResult }) {
  const k = KIND[r.kind];
  return (
    <div className="answer">
      <div className="answer-head">
        <span className={`pill pill-${k.tone}`}>{k.label}</span>
        {r.meta.used_llm && (
          <span className="small muted num">
            {r.meta.agent_steps} step{r.meta.agent_steps === 1 ? "" : "s"} · {r.meta.tokens_in} tokens in, {r.meta.tokens_out} out
            {r.meta.tools_used.length > 0 && ` · tools: ${[...new Set(r.meta.tools_used)].join(", ")}`}
          </span>
        )}
      </div>
      <p className="answer-text">{r.text}</p>
      {r.citations.length > 0 && (
        <div className="cites">
          {r.citations.map((c, i) => (
            <details key={i} className="cite" open={r.kind === "policy_quote"}>
              <summary>
                <b>{c.policy_title}</b>
                {c.ref && <span className="mono"> §{c.ref}</span>}
                {c.heading && <span> · {c.heading}</span>}
                {c.version && <span className="muted mono small"> · v{c.version}</span>}
              </summary>
              {c.excerpt && <p className="small">{c.excerpt}</p>}
            </details>
          ))}
        </div>
      )}
      {r.contacts.length > 0 && (
        <ul className="contacts">
          {r.contacts.map((c) => <li key={c.label}><span className="muted">{c.label}</span> <b>{c.value}</b></li>)}
        </ul>
      )}
      {r.actions.length > 0 && (
        <div className="small muted">Employee sees: {r.actions.map((a) => `“${a.label}”`).join(", ")}
          {r.actions.some((a) => a.draft) && <> with draft “{r.actions.find((a) => a.draft)!.draft}”</>}</div>
      )}
    </div>
  );
}
