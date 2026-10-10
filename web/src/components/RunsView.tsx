import { METRIC_LABELS, pct, runLabel, type Run } from "../api";

const COLUMNS = ["completion_rate", "clean_rate", "tool_precision", "args_valid_rate", "safe_rate", "grounded_rate"] as const;

interface Props {
  runs: Run[];
  selected: string[];
  onToggle: (id: string) => void;
  onOpenCases: (id: string) => void;
  onCompare: () => void;
}

export default function RunsView({ runs, selected, onToggle, onOpenCases, onCompare }: Props) {
  const best = Object.fromEntries(COLUMNS.map((c) => [c, Math.max(...runs.map((r) => r.summary[c] ?? 0))]));
  return (
    <section className="panel" aria-labelledby="runs-heading">
      <div className="panel-head">
        <h2 id="runs-heading">Runs</h2>
        <button type="button" className="primary" disabled={selected.length !== 2} onClick={onCompare}>
          Compare selected ({selected.length}/2)
        </button>
      </div>
      <p className="muted">
        Same 52 cases for every run. Task completion alone can look equal while behaviour differs; read it next to
        clean and safe.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">
                <span className="visually-hidden">Select</span>
              </th>
              <th scope="col">Run</th>
              {COLUMNS.map((c) => (
                <th scope="col" key={c}>
                  {METRIC_LABELS[c]}
                </th>
              ))}
              <th scope="col">Unsafe / privacy attempts</th>
              <th scope="col">Right answer, wrong tool</th>
              <th scope="col">Cost</th>
              <th scope="col">
                <span className="visually-hidden">Open</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className={selected.includes(run.id) ? "selected" : undefined}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Select ${runLabel(run)} for comparison`}
                    checked={selected.includes(run.id)}
                    onChange={() => onToggle(run.id)}
                  />
                </td>
                <th scope="row">
                  {runLabel(run)}
                  <span className="muted block">{run.id.slice(0, 16)}</span>
                </th>
                {COLUMNS.map((c) => (
                  <td key={c} className={run.summary[c] === best[c] ? "best" : undefined}>
                    <span className="meter" style={{ ["--v" as string]: `${(run.summary[c] ?? 0) * 100}%` }} />
                    {pct(run.summary[c])}
                  </td>
                ))}
                <td className={run.summary.unsafe_attempt_cases + run.summary.privacy_attempt_cases > 0 ? "warn" : undefined}>
                  {run.summary.unsafe_attempt_cases} / {run.summary.privacy_attempt_cases}
                </td>
                <td>{run.summary.right_answer_wrong_tool}</td>
                <td>${run.summary.cost_usd.toFixed(4)}</td>
                <td>
                  <button type="button" className="ghost" onClick={() => onOpenCases(run.id)}>
                    Cases
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
