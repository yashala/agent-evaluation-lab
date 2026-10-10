"""CI gate: the deterministic rule-baseline run must reproduce the committed baseline exactly.

    uv run --project api python evals/gate.py <fresh-run-dir>            # check
    uv run --project api python evals/gate.py <fresh-run-dir> --update   # accept new baseline

The baseline model is deterministic, so any change in per-case outcomes comes from a code,
case or scorer change and must be accepted explicitly (with --update) in the same commit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASELINE = Path(__file__).resolve().parent / "baseline_rule.json"


def snapshot(run: Path) -> dict[str, dict[str, object]]:
    out = {}
    for line in (run / "records.jsonl").open():
        r = json.loads(line)
        s = r["score"]
        out[r["case_id"]] = {
            "completed": s["completed"],
            "failure": s["failure"],
            "outcome": s["outcome_observed"],
        }
    return out


def main() -> int:
    run = Path(sys.argv[1])
    current = snapshot(run)
    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"baseline updated from {run.name} ({len(current)} cases)")
        return 0
    expected = json.loads(BASELINE.read_text())
    changed = {k for k in expected.keys() | current.keys() if expected.get(k) != current.get(k)}
    for case_id in sorted(changed):
        print(f"CHANGED {case_id}: {expected.get(case_id)} -> {current.get(case_id)}")
    print(f"{len(current) - len(changed)}/{len(current)} cases match the baseline")
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
