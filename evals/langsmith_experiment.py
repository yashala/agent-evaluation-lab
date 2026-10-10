"""Publish cases as a LangSmith dataset and runs as LangSmith experiments.

    # replay a stored run (no model calls, no cost)
    uv run --project api python evals/langsmith_experiment.py --from-run artifacts/runs/<run_id>
    # run the agent live inside LangSmith's evaluate()
    uv run --project api python evals/langsmith_experiment.py --model gpt-4.1-mini --prompt v1

Needs LANGSMITH_API_KEY. The dataset name includes a hash of evals/cases.yaml, so a changed
case file creates a new dataset version instead of silently editing the old one. Scores come
from the same scorer as evals/run.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from langsmith import Client

from agentlab.agent import SupportAgent
from agentlab.evaluation.runner import CASES
from agentlab.evaluation.scoring import Case, score
from agentlab.fixtures import FixtureStore
from agentlab.models import OpenAIModel, RuleBasedModel
from agentlab.policy import Session

ROOT = Path(__file__).resolve().parent.parent


def ensure_dataset(client: Client) -> str:
    digest = hashlib.sha256(CASES.read_bytes()).hexdigest()[:10]
    name = f"agentlab-cases-{digest}"
    if client.has_dataset(dataset_name=name):
        return name
    dataset = client.create_dataset(
        name, description=f"52 support-agent cases, cases.yaml sha {digest}"
    )
    raw_cases = yaml.safe_load(CASES.read_text())
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {
                    "case_id": c["id"],
                    "message": c["message"],
                    "session": c["session"],
                    "patch": c.get("patch"),
                },
                "outputs": {"case": c},
                "metadata": {"category": c["category"]},
            }
            for c in raw_cases
        ],
    )
    return name


def trajectory(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    """LangSmith evaluator: score the trajectory with the project's scorer."""
    case = Case.parse(reference_outputs["case"])
    s = score(case, outputs["answer"], outputs["events"], outputs["hit_limit"], outputs["steps"])
    return {
        "results": [
            {"key": "completed", "score": int(s.completed)},
            {"key": "clean", "score": int(s.failure is None), "comment": s.failure or ""},
            {"key": "tool_precision", "score": s.tool_precision},
            {"key": "tool_recall", "score": s.tool_recall},
            {"key": "args_valid", "score": s.args_valid_rate},
            {
                "key": "safe",
                "score": int(
                    s.unsafe_attempts == 0 and s.privacy_attempts == 0 and not s.leaked_facts
                ),
            },
        ]
    }


def replay_target(run: Path) -> Any:
    records = {r["case_id"]: r for r in map(json.loads, (run / "records.jsonl").open())}

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        r = records[inputs["case_id"]]
        return {
            "answer": r["answer"],
            "events": r["events"],
            "steps": r["score"]["steps"],
            "hit_limit": r["score"]["outcome_observed"] == "step_limit",
        }

    return target


def live_target(agent: SupportAgent) -> Any:
    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        result = agent.run(
            inputs["message"],
            FixtureStore.load(patch=inputs["patch"]),
            Session(inputs["session"]),
            tags=[inputs["case_id"]],
        )
        return {**asdict(result), "hit_limit": result.hit_step_limit}

    return target


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-run")
    parser.add_argument("--model")
    parser.add_argument("--prompt", default="v1")
    args = parser.parse_args()
    client = Client()
    dataset = ensure_dataset(client)

    if args.from_run:
        run = Path(args.from_run)
        env = json.loads((run / "environment.json").read_text())
        target, prefix = replay_target(run), f"{env['model']}-{env['prompt_version']}"
        metadata = {
            "source_run": run.name,
            "model": env["model"],
            "prompt": env["prompt_version"],
            "replayed": True,
        }
    elif args.model:
        model = (
            RuleBasedModel()
            if args.model == "rule-baseline"
            else OpenAIModel(args.model, os.environ["OPENAI_API_KEY"])
        )
        target, prefix = (
            live_target(SupportAgent(model, args.prompt)),
            f"{args.model}-{args.prompt}",
        )
        metadata = {"model": args.model, "prompt": args.prompt, "replayed": False}
    else:
        raise SystemExit("pass --from-run or --model")

    results = client.evaluate(
        target,
        data=dataset,
        evaluators=[trajectory],
        experiment_prefix=prefix,
        metadata=metadata,
        max_concurrency=1,
    )
    print(f"experiment {results.experiment_name} on dataset {dataset}")


if __name__ == "__main__":
    main()
