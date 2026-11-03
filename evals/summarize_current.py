# ruff: noqa: E501
"""Generate a descriptive repeated-run report from complete, validated artifacts."""

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "artifacts/current-comparison/final"
REPORT = ROOT / "docs/results/current-model-comparison.md"
groups = defaultdict(list)
for p in sorted(BASE.glob("*/*/summary.json")):
    env = json.loads((p.parent / "environment.json").read_text())
    summary = json.loads(p.read_text())
    if env["complete"] and summary["cases"] == 52:
        groups[(env["model"], env["prompt_version"])].append((p.parent, summary))
lines = [
    "# Current-model comparison",
    "",
    "Measured November 3, 2026. 52 synthetic development cases per complete run. Responses API, low reasoning effort, 2,048 output-token cap, no automatic retries. Historical GPT-4.1 results use earlier adapter defaults and one run per configuration.",
    "",
    "| Configuration | Complete runs | Completion mean (range) | Clean mean (range) | Safe mean | Estimated cost total |",
    "|---|---:|---:|---:|---:|---:|",
]
for (model, prompt), rows in sorted(groups.items()):

    def fmt(metric, current_rows=rows):
        vals = [s[metric] * 100 for _, s in current_rows]
        return f"{statistics.mean(vals):.1f}% ({min(vals):.1f}-{max(vals):.1f}%)"

    safe = statistics.mean(s["safe_rate"] for _, s in rows) * 100
    cost = sum(s["cost_usd"] for _, s in rows)
    lines.append(
        f"| {model} / {prompt} | {len(rows)} | {fmt('completion_rate')} | {fmt('clean_rate')} | {safe:.1f}% | ${cost:.4f} |"
    )
lines += [
    "",
    "Clean means no recorded failure category. Safety includes attempted forbidden calls, attempted cross-customer access, and detected leaks. Costs use uncached standard input/output rates and include reasoning output tokens; they are estimates, not invoices.",
    "",
    "## Individual runs",
    "",
]
for (_model, _prompt), rows in sorted(groups.items()):
    for path, s in rows:
        lines += [
            f"### {path.name}",
            "",
            f"Completion {s['completion_rate']:.4f}; clean {s['clean_rate']:.4f}; safe {s['safe_rate']:.4f}; p50 {s['latency_ms']['p50']} ms; p95 {s['latency_ms']['p95']} ms; estimated cost ${s['cost_usd']:.4f}.",
            "",
            f"Failures: `{json.dumps(s['failures'], sort_keys=True)}`",
            "",
        ]
lines += [
    "## Limitations",
    "",
    "These are development-set results, not a held-out benchmark or general model ranking. The scorer uses substring checks and heuristic outcome classification. Repetition captures only a small amount of sampling variability. Historical and current runs differ in transport, reasoning settings, output cap, date, and number of repetitions. Early compatibility/debugging partial runs are excluded and still counted in the campaign budget. Partial runs must not be averaged as complete evaluations.",
    "",
]
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines))
print(REPORT)
for key, rows in sorted(groups.items()):
    print(
        key,
        len(rows),
        {
            k: round(statistics.mean(s[k] for _, s in rows), 4)
            for k in ["completion_rate", "clean_rate", "safe_rate"]
        },
    )
