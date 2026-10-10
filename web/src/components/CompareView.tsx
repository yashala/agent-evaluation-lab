import { useEffect, useState } from "react";
import { api, METRIC_LABELS, pct, type Comparison } from "../api";

const isRate = (metric: string) => metric.endsWith("_rate") || metric.startsWith("tool_");

interface Props {
  base: string;
  candidate: string;
  onOpenTrace: (runId: string, caseId: string) => void;
}

export default function CompareView({ base, candidate, onOpenTrace }: Props) {
  const [data, setData] = useState<Comparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api.compare(base, candidate).then(setData).catch((e: Error) => setError(e.message));
  }, [base, candidate]);

  if (error) return <p className="error">Could not compare: {error}</p>;
  if (!data) return <p className="muted">Comparing…</p>;

  const fmt = (metric: string, v: number) => (isRate(metric) ? pct(v) : metric === "cost_usd" ? `$${v.toFixed(4)}` : v.toFixed(2));
  return (
    <section className="panel" aria-labelledby="compare-heading">
      <h2 id="compare-heading">
        {data.base.model} · {data.base.prompt} → {data.candidate.model} · {data.candidate.prompt}
      </h2>
      <p className={data.tradeoff ? "banner tradeoff" : "banner"} role="status">
        {data.tradeoff
          ? `Trade-off: better ${data.improved.map((m) => METRIC_LABELS[m] ?? m).join(", ")}; worse ${data.regressed
              .map((m) => METRIC_LABELS[m] ?? m)
              .join(", ")}.`
          : data.regressed.length
            ? `Worse on ${data.regressed.map((m) => METRIC_LABELS[m] ?? m).join(", ")}.`
            : data.improved.length
              ? `Better on ${data.improved.map((m) => METRIC_LABELS[m] ?? m).join(", ")}.`
              : "No metric moved by more than one case in fifty."}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Base</th>
              <th scope="col">Candidate</th>
              <th scope="col">Change</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.deltas).map(([metric, d]) => (
              <tr key={metric} className={`delta ${d.verdict}`}>
                <th scope="row">{METRIC_LABELS[metric] ?? metric}</th>
                <td>{fmt(metric, d.base)}</td>
                <td>{fmt(metric, d.candidate)}</td>
                <td>
                  <span className="verdict">{d.verdict === "same" ? "–" : d.verdict}</span>{" "}
                  {d.change > 0 ? "+" : ""}
                  {isRate(metric) ? `${(d.change * 100).toFixed(1)} pts` : metric === "cost_usd" ? `${d.change < 0 ? "-" : ""}$${Math.abs(d.change).toFixed(4)}` : d.change.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>Cases that changed ({data.flipped_cases.length})</h3>
      {data.flipped_cases.length === 0 && <p className="muted">No case changed outcome.</p>}
      <ul className="flips">
        {data.flipped_cases.map((f) => (
          <li key={f.case_id} className={f.direction}>
            <span className="badge">{f.direction}</span>
            <button type="button" className="link" onClick={() => onOpenTrace(data.candidate.run, f.case_id)}>
              {f.case_id}
            </button>
            <span className="muted">
              {f.category}: {f.base.failure ?? "ok"} → {f.candidate.failure ?? "ok"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
