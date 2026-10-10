import { useEffect, useState } from "react";
import { api, type Run } from "./api";
import CasesView from "./components/CasesView";
import CompareView from "./components/CompareView";
import RunsView from "./components/RunsView";

type View = { name: "runs" } | { name: "compare" } | { name: "cases"; runId: string; caseId: string | null };

export default function App() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [view, setView] = useState<View>({ name: "runs" });

  useEffect(() => {
    api
      .runs()
      .then((r) => {
        setRuns(r);
        const pick = (model: string, prompt: string) => r.find((x) => x.model === model && x.prompt === prompt)?.id;
        const defaults = [pick("gpt-4.1-mini", "v1"), pick("gpt-4.1-nano", "v1")].filter((x): x is string => !!x);
        setSelected(defaults.length === 2 ? defaults : r.slice(0, 2).map((x) => x.id));
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s.slice(-1), id]));
  const openTrace = (runId: string, caseId: string) => setView({ name: "cases", runId, caseId });
  function go(name: View["name"]) {
    if (name === "cases") setView({ name, runId: selected[0] ?? runs![0]!.id, caseId: null });
    else if (name === "compare") setView({ name });
    else setView({ name });
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Agent Evaluation Lab</h1>
          <p className="muted">Trajectory-level evaluation of a tool-using support agent</p>
        </div>
        <nav aria-label="Views" className="tabs" role="tablist">
          {(["runs", "compare", "cases"] as const).map((name) => (
            <button
              key={name}
              role="tab"
              aria-selected={view.name === name}
              disabled={!runs || (name === "compare" && selected.length !== 2)}
              onClick={() => go(name)}
            >
              {name === "runs" ? "Runs" : name === "compare" ? "Compare" : "Cases & traces"}
            </button>
          ))}
        </nav>
      </header>

      {error && <p className="error">Could not reach the API: {error}</p>}
      {!runs && !error && <p className="muted">Loading runs…</p>}
      {runs && runs.length === 0 && <p className="empty">No runs yet. Run `make eval-offline` to create one.</p>}
      {runs && runs.length > 0 && (
        <main>
          {view.name === "runs" && (
            <RunsView
              runs={runs}
              selected={selected}
              onToggle={toggle}
              onOpenCases={(id) => setView({ name: "cases", runId: id, caseId: null })}
              onCompare={() => setView({ name: "compare" })}
            />
          )}
          {view.name === "compare" && selected.length === 2 && (
            <CompareView base={selected[0]!} candidate={selected[1]!} onOpenTrace={openTrace} />
          )}
          {view.name === "cases" && (
            <CasesView
              runs={runs}
              runId={view.runId}
              initialCase={view.caseId}
              onRunChange={(runId) => setView({ name: "cases", runId, caseId: view.caseId })}
            />
          )}
        </main>
      )}
    </div>
  );
}
