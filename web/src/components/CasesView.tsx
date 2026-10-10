import { useEffect, useMemo, useState } from "react";
import { api, FAILURE_HELP, runLabel, type CaseRow, type Run } from "../api";
import TraceView from "./TraceView";

interface Props {
  runs: Run[];
  runId: string;
  initialCase: string | null;
  onRunChange: (id: string) => void;
}

export default function CasesView({ runs, runId, initialCase, onRunChange }: Props) {
  const [rows, setRows] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("all");
  const [onlyFailures, setOnlyFailures] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(initialCase);

  useEffect(() => {
    setRows(null);
    setError(null);
    api.cases(runId).then(setRows).catch((e: Error) => setError(e.message));
  }, [runId]);

  useEffect(() => setCaseId(initialCase), [initialCase]);

  const categories = useMemo(() => [...new Set(rows?.map((r) => r.category) ?? [])].sort(), [rows]);
  const visible = (rows ?? []).filter((r) => (category === "all" || r.category === category) && (!onlyFailures || r.failure));

  return (
    <div className="cases-layout">
      <section className="panel" aria-labelledby="cases-heading">
        <div className="panel-head">
          <h2 id="cases-heading">Cases</h2>
          <label>
            <span className="visually-hidden">Run</span>
            <select value={runId} onChange={(e) => onRunChange(e.target.value)}>
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {runLabel(r)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="filters">
          <label>
            Category{" "}
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="all">all</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label>
            <input type="checkbox" checked={onlyFailures} onChange={(e) => setOnlyFailures(e.target.checked)} /> failures only
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        {!rows && !error && <p className="muted">Loading…</p>}
        <ul className="case-list">
          {visible.map((r) => (
            <li key={r.case_id}>
              <button type="button" className={caseId === r.case_id ? "case active" : "case"} onClick={() => setCaseId(r.case_id)}>
                <span className={r.failure ? "dot bad" : "dot ok"} aria-hidden />
                <span className="case-id">{r.case_id}</span>
                <span className="case-failure" title={r.failure ? FAILURE_HELP[r.failure] : undefined}>
                  {r.failure ?? "ok"}
                </span>
              </button>
            </li>
          ))}
          {rows && visible.length === 0 && <li className="muted">No cases match.</li>}
        </ul>
      </section>
      {caseId ? <TraceView runId={runId} caseId={caseId} /> : <p className="muted panel">Select a case to see its trace.</p>}
    </div>
  );
}
