"""Recompute scores for existing runs from their stored traces. No model calls, no cost.

    uv run --project api python evals/rescore.py artifacts/runs/<run_id> [...]

Generation and scoring are separate: when a scorer or case expectation is corrected, every run
can be re-scored on identical model outputs. The case-file hash used is recorded.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from agentlab.evaluation.runner import CASES, load_cases, summarise
from agentlab.evaluation.scoring import score


def rescore(run: Path) -> dict[str, object]:
    cases = {c.id: c for c in load_cases()}
    records = [json.loads(line) for line in (run / "records.jsonl").open()]
    for r in records:
        old = r["score"]
        hit_limit = old["outcome_observed"] == "step_limit"
        r["score"] = asdict(
            score(cases[r["case_id"]], r["answer"], r["events"], hit_limit, old["steps"])
        )
    with (run / "records.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    summary = summarise(records)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    env = json.loads((run / "environment.json").read_text())
    env.setdefault("rescored", []).append(
        {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest()[:12],
        }
    )
    (run / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    for path in sys.argv[1:]:
        s = rescore(Path(path))
        print(
            Path(path).name,
            {k: s[k] for k in ("completion_rate", "clean_rate", "safe_rate")},
            s["failures"],
        )
