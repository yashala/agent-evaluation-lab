import { useEffect, useState } from "react";
import { api, FAILURE_HELP, type Trace } from "../api";

const VERDICT_LABEL: Record<string, string> = {
  allowed: "executed",
  invalid_arguments: "blocked: invalid arguments",
  not_permitted: "blocked: not permitted",
  other_customer: "blocked: other customer's data",
  unknown_tool: "blocked: unknown tool",
};

export default function TraceView({ runId, caseId }: { runId: string; caseId: string }) {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTrace(null);
    setError(null);
    api.trace(runId, caseId).then(setTrace).catch((e: Error) => setError(e.message));
  }, [runId, caseId]);

  if (error) return <p className="error panel">{error}</p>;
  if (!trace) return <p className="muted panel">Loading trace…</p>;
  const s = trace.score;
  const e = trace.expect;

  return (
    <section className="panel trace" aria-labelledby="trace-heading">
      <h2 id="trace-heading">
        {trace.case_id} <span className="muted">{trace.category}</span>
      </h2>
      <p className={s.failure ? "banner fail" : "banner ok"} role="status">
        {s.failure ? `${s.failure}: ${FAILURE_HELP[s.failure] ?? ""}` : "No failure"}
      </p>

      <dl className="score-grid">
        <div><dt>Outcome</dt><dd>{s.outcome_observed}{e && ` (expected ${e.outcome.join(" or ")})`}</dd></div>
        <div><dt>Tool precision / recall</dt><dd>{s.tool_precision} / {s.tool_recall}</dd></div>
        <div><dt>Valid arguments</dt><dd>{s.args_valid_rate}</dd></div>
        <div><dt>Grounded</dt><dd>{s.grounded === null ? "n/a" : String(s.grounded)}</dd></div>
        <div><dt>Blocked attempts</dt><dd>{s.unsafe_attempts} unsafe, {s.privacy_attempts} privacy</dd></div>
        <div><dt>Steps · latency · cost</dt><dd>{s.steps} · {Math.round(trace.latency_ms)} ms · ${trace.cost_usd.toFixed(5)}</dd></div>
      </dl>
      {e && (
        <p className="muted">
          Expected tools: {e.tools_required.join(" → ") || "none"}
          {e.forbidden_tools.length > 0 && ` · forbidden: ${e.forbidden_tools.join(", ")}`}
        </p>
      )}

      <ol className="timeline">
        <li className="event user">
          <span className="event-kind">customer</span>
          <p>{trace.message}</p>
        </li>
        {trace.events.map((ev, i) =>
          ev.type === "model" ? (
            <li key={i} className="event model">
              <span className="event-kind">model · step {ev.step + 1} · {Math.round(ev.ms)} ms</span>
              {ev.content && <p>{ev.content}</p>}
              {ev.tool_calls.map((c, j) => (
                <code key={j} className="call">
                  {c.name}({JSON.stringify(c.args)})
                </code>
              ))}
            </li>
          ) : (
            <li key={i} className={`event tool ${ev.verdict === "allowed" ? "allowed" : "denied"}`}>
              <span className="event-kind">
                tool · {ev.name} · {VERDICT_LABEL[ev.verdict] ?? ev.verdict}
              </span>
              <details>
                <summary>result</summary>
                <pre>{JSON.stringify(ev.result, null, 2)}</pre>
              </details>
            </li>
          ),
        )}
      </ol>
      <h3>Final answer</h3>
      <p className="answer">{trace.answer || <em>none (step limit)</em>}</p>
    </section>
  );
}
