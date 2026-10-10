"""Run every case through the agent, score it, and summarise. Writes JSON run artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

from agentlab.agent import PROMPTS, AgentModel, SupportAgent
from agentlab.evaluation.scoring import Case, CaseScore, score
from agentlab.fixtures import FixtureStore
from agentlab.policy import Session

ROOT = Path(__file__).resolve().parents[4]
CASES = ROOT / "evals" / "cases.yaml"
PRICING = ROOT / "evals" / "pricing.yaml"


def load_cases(ids: list[str] | None = None) -> list[Case]:
    cases = [Case.parse(raw) for raw in yaml.safe_load(CASES.read_text())]
    return [c for c in cases if not ids or c.id in ids or c.category in ids]


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices: dict[str, dict[str, float]] = yaml.safe_load(PRICING.read_text())
    if model not in prices:
        raise SystemExit(f"no price for {model} in evals/pricing.yaml; refusing to run unbudgeted")
    p = prices[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1e6


def run_case(agent: SupportAgent, case: Case, tags: list[str]) -> dict[str, Any]:
    store = FixtureStore.load(patch=case.patch)
    result = agent.run(case.message, store, Session(case.session), tags=[case.id, *tags])
    s = score(case, result.answer, result.events, result.hit_step_limit, result.steps)
    return {
        "case_id": case.id,
        "category": case.category,
        "message": case.message,
        "score": asdict(s),
        "answer": result.answer,
        "events": result.events,
        "latency_ms": round(result.latency_ms, 1),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": round(cost_usd(agent.model.name, result.input_tokens, result.output_tokens), 6),
    }


def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, min(len(ordered) - 1, round(p / 100 * len(ordered) + 0.5) - 1))], 1)


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [CaseScore(**r["score"]) for r in records]
    n = len(scores)

    def rate(pred: list[bool]) -> float | None:
        return round(sum(pred) / len(pred), 4) if pred else None

    def mean(values: list[float]) -> float | None:
        return round(statistics.fmean(values), 4) if values else None

    grounded = [s.grounded for s in scores if s.grounded is not None]
    by_category: dict[str, list[CaseScore]] = defaultdict(list)
    for s in scores:
        by_category[s.category].append(s)
    latencies = [r["latency_ms"] for r in records]
    return {
        "cases": n,
        "completion_rate": rate([s.completed for s in scores]),
        "tool_precision": mean([s.tool_precision for s in scores]),
        "tool_recall": mean([s.tool_recall for s in scores]),
        "args_valid_rate": mean([s.args_valid_rate for s in scores]),
        "sequence_ok_rate": rate([s.sequence_ok for s in scores]),
        "grounded_rate": rate(grounded),
        "safe_rate": rate(
            [
                s.unsafe_attempts == 0 and s.privacy_attempts == 0 and not s.leaked_facts
                for s in scores
            ]
        ),
        "unsafe_attempt_cases": sum(1 for s in scores if s.unsafe_attempts),
        "privacy_attempt_cases": sum(1 for s in scores if s.privacy_attempts),
        "leak_cases": sum(1 for s in scores if s.leaked_facts),
        "right_answer_wrong_tool": sum(1 for s in scores if s.right_answer_wrong_tool),
        "clean_rate": rate([s.failure is None for s in scores]),
        "mean_steps": mean([float(s.steps) for s in scores]),
        "failures": dict(Counter(s.failure for s in scores if s.failure)),
        "by_category": {
            cat: {
                "cases": len(group),
                "completion_rate": rate([s.completed for s in group]),
                "clean_rate": rate([s.failure is None for s in group]),
            }
            for cat, group in sorted(by_category.items())
        },
        "latency_ms": {"p50": _pct(latencies, 50), "p95": _pct(latencies, 95)},
        "tokens": {
            "input": sum(r["input_tokens"] for r in records),
            "output": sum(r["output_tokens"] for r in records),
        },
        "cost_usd": round(sum(r["cost_usd"] for r in records), 4),
    }


def environment(model: AgentModel, prompt: str) -> dict[str, Any]:
    def sh(*cmd: str) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT).stdout.strip()
        except OSError:
            return ""

    versions: dict[str, str | None] = {}
    for pkg in ("langgraph", "langchain-core", "langchain-openai"):
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = None
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": sh("git", "rev-parse", "HEAD"),
        "git_dirty": bool(sh("git", "status", "--porcelain")),
        "model": model.name,
        "prompt_version": prompt,
        "prompt_sha256": hashlib.sha256(PROMPTS[prompt].encode()).hexdigest()[:12],
        "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest()[:12],
        "platform": platform.platform(),
        "cpu": sh("sysctl", "-n", "machdep.cpu.brand_string") or platform.processor(),
        "memory_gb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1),
        "python": platform.python_version(),
        "packages": versions,
    }


def run(
    model: AgentModel,
    prompt: str,
    out_dir: Path,
    case_ids: list[str] | None = None,
    max_cost_usd: float | None = None,
) -> Path:
    cases = load_cases(case_ids)
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{model.name}-{prompt}"
    out = out_dir / run_id
    out.mkdir(parents=True)
    env = environment(model, prompt)
    agent = SupportAgent(model, prompt)
    records: list[dict[str, Any]] = []
    spent = 0.0
    with (out / "records.jsonl").open("w") as f:
        for case in cases:
            worst = max((r["cost_usd"] for r in records), default=0.01)
            if max_cost_usd is not None and spent + 2 * worst > max_cost_usd:
                print(f"budget stop before {case.id}: spent ${spent:.4f}")
                break
            record = run_case(agent, case, [run_id])
            spent += record["cost_usd"]
            records.append(record)
            f.write(json.dumps(record) + "\n")
            f.flush()
    env["complete"] = len(records) == len(cases)
    env["records"] = f"{len(records)}/{len(cases)}"
    (out / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    (out / "summary.json").write_text(json.dumps(summarise(records), indent=2) + "\n")
    return out
