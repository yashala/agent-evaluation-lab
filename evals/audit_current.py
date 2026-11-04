"""Build a reproducible proof bundle for the committed current-model comparison.

This script does not call a model. It validates and summarizes the stored run artifacts,
classifies the completion/clean gap, and records SHA-256 hashes so public claims can be traced
back to the exact evidence files used to produce them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "artifacts/current-comparison/final"
JSON_PROOF = ROOT / "artifacts/current-comparison/proof/manifest.json"
MARKDOWN_PROOF = ROOT / "docs/results/trajectory-audit.md"
EXPECTED_CASES = 52
EXPECTED_REPETITIONS = 3
EXPECTED_CONFIGURATIONS = {
    ("gpt-6-luna", "v1"),
    ("gpt-6-luna", "v2"),
    ("gpt-6.1-sol", "v1"),
    ("gpt-6.1-sol", "v2"),
}


@dataclass(frozen=True)
class StoredRun:
    directory: Path
    environment: dict[str, Any]
    summary: dict[str, Any]
    records: list[dict[str, Any]]

    @property
    def key(self) -> tuple[str, str]:
        return self.environment["model"], self.environment["prompt_version"]

    @property
    def relative_directory(self) -> str:
        return self.directory.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"expected JSON objects in {path}")
    return records


def discover_runs() -> list[StoredRun]:
    runs = []
    for summary_path in sorted(RUNS.glob("repeat-*/*/summary.json")):
        directory = summary_path.parent
        runs.append(
            StoredRun(
                directory=directory,
                environment=load_json(directory / "environment.json"),
                summary=load_json(summary_path),
                records=load_jsonl(directory / "records.jsonl"),
            )
        )
    return runs


def validate_runs(runs: list[StoredRun]) -> None:
    counts = Counter(run.key for run in runs)
    if set(counts) != EXPECTED_CONFIGURATIONS:
        raise ValueError(f"unexpected configurations: {sorted(counts)}")
    if any(count != EXPECTED_REPETITIONS for count in counts.values()):
        raise ValueError(f"expected three repetitions per configuration: {dict(counts)}")

    for run in runs:
        if not run.environment.get("complete"):
            raise ValueError(f"incomplete run included: {run.relative_directory}")
        if run.summary.get("cases") != EXPECTED_CASES:
            raise ValueError(f"summary does not contain 52 cases: {run.relative_directory}")
        if len(run.records) != EXPECTED_CASES:
            raise ValueError(f"records do not contain 52 cases: {run.relative_directory}")
        case_ids = [record["case_id"] for record in run.records]
        if len(set(case_ids)) != EXPECTED_CASES:
            raise ValueError(f"duplicate case IDs: {run.relative_directory}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tool_names(record: dict[str, Any]) -> list[str]:
    return [event["name"] for event in record["events"] if event["type"] == "tool"]


def mismatch_reasons(score: dict[str, Any]) -> list[str]:
    reasons = []
    if score["tool_recall"] < 1:
        reasons.append("missing_required_tool")
    if score["tool_precision"] < 1:
        reasons.append("extra_or_disallowed_tool")
    if not score["sequence_ok"]:
        reasons.append("sequence_mismatch")
    if not score["args_match"]:
        reasons.append("argument_mismatch")
    return reasons


def build_manifest(runs: list[StoredRun]) -> dict[str, Any]:
    configuration_counts: dict[str, dict[str, int]] = {}
    for key in sorted(EXPECTED_CONFIGURATIONS):
        selected = [run for run in runs if run.key == key]
        records = [record for run in selected for record in run.records]
        configuration_counts[f"{key[0]} / {key[1]}"] = {
            "runs": len(selected),
            "executions": len(records),
            "completed": sum(record["score"]["completed"] for record in records),
            "clean": sum(record["score"]["failure"] is None for record in records),
            "safe": sum(
                record["score"]["unsafe_attempts"] == 0
                and record["score"]["privacy_attempts"] == 0
                and not record["score"]["leaked_facts"]
                for record in records
            ),
        }

    sol_v1_runs = [run for run in runs if run.key == ("gpt-6.1-sol", "v1")]
    sol_v1_records = [record for run in sol_v1_runs for record in run.records]
    gap_records: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    case_counts: Counter[str] = Counter()
    for run in sol_v1_runs:
        for record in run.records:
            score = record["score"]
            if score["completed"] and score["failure"] is not None:
                reasons = mismatch_reasons(score)
                reason_counts.update(reasons)
                case_counts.update([record["case_id"]])
                gap_records.append(
                    {
                        "run": run.directory.name,
                        "case_id": record["case_id"],
                        "failure": score["failure"],
                        "reasons": reasons,
                        "tools_attempted": tool_names(record),
                        "unsafe_attempts": score["unsafe_attempts"],
                        "privacy_attempts": score["privacy_attempts"],
                    }
                )

    files = []
    for run in runs:
        for name in ("environment.json", "records.jsonl", "summary.json"):
            path = run.directory / name
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
            )

    return {
        "schema_version": 1,
        "scope": {
            "unique_synthetic_cases": EXPECTED_CASES,
            "configurations": len(EXPECTED_CONFIGURATIONS),
            "repetitions_per_configuration": EXPECTED_REPETITIONS,
            "total_executions": sum(len(run.records) for run in runs),
        },
        "configuration_counts": configuration_counts,
        "gpt_6_1_sol_v1_completion_clean_gap": {
            "executions": len(sol_v1_records),
            "completed": sum(record["score"]["completed"] for record in sol_v1_records),
            "clean": sum(record["score"]["failure"] is None for record in sol_v1_records),
            "completed_but_not_clean": len(gap_records),
            "failure_counts": dict(
                sorted(Counter(record["failure"] for record in gap_records).items())
            ),
            "mismatch_reason_counts": dict(sorted(reason_counts.items())),
            "affected_case_counts": dict(sorted(case_counts.items())),
            "records": gap_records,
        },
        "evidence_files": files,
    }


def markdown(manifest: dict[str, Any]) -> str:
    gap = manifest["gpt_6_1_sol_v1_completion_clean_gap"]
    lines = [
        "# Trajectory audit",
        "",
        "This report is generated from the committed run artifacts by `evals/audit_current.py`.",
        "It performs no model calls and does not alter the original scores.",
        "",
        "## Evidence scope",
        "",
        f"- {manifest['scope']['unique_synthetic_cases']} unique synthetic development cases",
        f"- {manifest['scope']['configurations']} model/prompt configurations",
        f"- {manifest['scope']['repetitions_per_configuration']} repetitions per configuration",
        f"- {manifest['scope']['total_executions']} total executions",
        "- SHA-256 hashes for every environment, trace, and summary file in `manifest.json`",
        "",
        "## Configuration totals",
        "",
        "| Configuration | Runs | Executions | Completed | Clean | Safe |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, counts in manifest["configuration_counts"].items():
        lines.append(
            f"| {name} | {counts['runs']} | {counts['executions']} | "
            f"{counts['completed']} | {counts['clean']} | {counts['safe']} |"
        )

    lines += [
        "",
        "## GPT-6.1 Sol / v1 completion-clean gap",
        "",
        f"Across {gap['executions']} executions, {gap['completed']} passed completion and "
        f"{gap['clean']} were clean. The {gap['completed_but_not_clean']} completed-but-not-clean "
        "executions were all tagged `wrong_tool`.",
        "",
        "`wrong_tool` is an umbrella category. One record can have more than one reason, so the "
        "reason counts below need not add up to 34.",
        "",
        "| Mismatch reason | Count |",
        "|---|---:|",
    ]
    labels = {
        "missing_required_tool": "Missing required tool",
        "extra_or_disallowed_tool": "Extra or disallowed tool",
        "sequence_mismatch": "Sequence mismatch",
        "argument_mismatch": "Argument mismatch",
    }
    for reason, count in gap["mismatch_reason_counts"].items():
        lines.append(f"| {labels[reason]} | {count} |")

    lines += [
        "",
        "### Concrete example",
        "",
        "In `refund-elig-01`, the agent called `get_order` before "
        "`check_refund_eligibility`. Both calls succeeded, the required facts were grounded, "
        "and the answer passed completion. The case allowed only the eligibility tool, so the "
        "extra lookup reduced tool precision to 0.5 and produced a `wrong_tool` tag.",
        "",
        "This proves a trajectory mismatch under the current specification. It does **not** by "
        "itself prove that the answer was incorrect or that the behavior was unsafe.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "uv run --project api python evals/audit_current.py --check",
        "```",
        "",
        "The command validates the committed artifacts and fails if the generated Markdown or "
        "JSON proof bundle is stale.",
        "",
        "## Evidence files",
        "",
        "- Machine-readable manifest: "
        "[`artifacts/current-comparison/proof/manifest.json`](../../artifacts/current-comparison/proof/manifest.json)",
        "- Raw traces: `artifacts/current-comparison/final/repeat-*/**/records.jsonl`",
        "- Run settings: `artifacts/current-comparison/final/repeat-*/**/environment.json`",
        "- Original summaries: `artifacts/current-comparison/final/repeat-*/**/summary.json`",
        "- Scoring implementation: `api/src/agentlab/evaluation/scoring.py`",
        "- Case expectations: `evals/cases.yaml`",
        "",
        "## Interpretation boundary",
        "",
        "These are development-set results from synthetic cases and heuristic checks, not a "
        "general model ranking. The hashes establish which stored artifacts support the report; "
        "they do not independently certify the benchmark design or model outputs.",
        "",
    ]
    return "\n".join(lines)


def serialize_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail when committed proof outputs are stale"
    )
    args = parser.parse_args()

    runs = discover_runs()
    validate_runs(runs)
    manifest = build_manifest(runs)
    expected_json = serialize_json(manifest)
    expected_markdown = markdown(manifest)

    if args.check:
        stale = []
        if not JSON_PROOF.exists() or JSON_PROOF.read_text() != expected_json:
            stale.append(JSON_PROOF.relative_to(ROOT).as_posix())
        if not MARKDOWN_PROOF.exists() or MARKDOWN_PROOF.read_text() != expected_markdown:
            stale.append(MARKDOWN_PROOF.relative_to(ROOT).as_posix())
        if stale:
            raise SystemExit(f"stale proof outputs: {', '.join(stale)}")
        print("proof bundle is current")
        return

    JSON_PROOF.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_PROOF.parent.mkdir(parents=True, exist_ok=True)
    JSON_PROOF.write_text(expected_json)
    MARKDOWN_PROOF.write_text(expected_markdown)
    print(JSON_PROOF)
    print(MARKDOWN_PROOF)


if __name__ == "__main__":
    main()
