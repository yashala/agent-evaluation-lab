"""Compare two runs: metric deltas, changed cases, and metrics moving in opposite directions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Direction in which each summary metric is better.
METRICS: dict[str, int] = {
    "completion_rate": +1,
    "clean_rate": +1,
    "tool_precision": +1,
    "tool_recall": +1,
    "args_valid_rate": +1,
    "sequence_ok_rate": +1,
    "grounded_rate": +1,
    "safe_rate": +1,
    "mean_steps": -1,
    "cost_usd": -1,
}
NOISE = 0.02  # ignore movements smaller than one case in fifty


def load(run: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    env = json.loads((run / "environment.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    records = {r["case_id"]: r for r in map(json.loads, (run / "records.jsonl").open())}
    return env, summary, records


def compare(base: Path, candidate: Path) -> dict[str, Any]:
    env_a, sum_a, rec_a = load(base)
    env_b, sum_b, rec_b = load(candidate)
    deltas = {}
    for metric, direction in METRICS.items():
        a, b = sum_a.get(metric), sum_b.get(metric)
        if a is None or b is None:
            continue
        change = round(b - a, 4)
        if metric == "cost_usd" or metric == "mean_steps":
            moved = abs(change) > 1e-9 and (abs(change) / max(abs(a), 1e-9)) > 0.05
        else:
            moved = abs(change) >= NOISE
        verdict = "same" if not moved else ("better" if change * direction > 0 else "worse")
        deltas[metric] = {"base": a, "candidate": b, "change": change, "verdict": verdict}

    flips = []
    for case_id in sorted(set(rec_a) & set(rec_b)):
        sa, sb = rec_a[case_id]["score"], rec_b[case_id]["score"]
        if sa["completed"] != sb["completed"] or sa["failure"] != sb["failure"]:
            flips.append(
                {
                    "case_id": case_id,
                    "category": sb["category"],
                    "base": {"completed": sa["completed"], "failure": sa["failure"]},
                    "candidate": {"completed": sb["completed"], "failure": sb["failure"]},
                    "direction": _direction(sa, sb),
                }
            )
    better = [m for m, d in deltas.items() if d["verdict"] == "better"]
    worse = [m for m, d in deltas.items() if d["verdict"] == "worse"]
    return {
        "base": {"run": base.name, "model": env_a["model"], "prompt": env_a["prompt_version"]},
        "candidate": {
            "run": candidate.name,
            "model": env_b["model"],
            "prompt": env_b["prompt_version"],
        },
        "deltas": deltas,
        "improved": better,
        "regressed": worse,
        "tradeoff": bool(better and worse),
        "flipped_cases": flips,
    }


def _direction(a: dict[str, Any], b: dict[str, Any]) -> str:
    if a["failure"] and not b["failure"]:
        return "fixed"
    if b["failure"] and not a["failure"]:
        return "broke"
    return "changed"
