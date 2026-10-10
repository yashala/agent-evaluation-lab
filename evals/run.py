"""Run the evaluation.

uv run --project api python evals/run.py --model rule-baseline
uv run --project api python evals/run.py --model gpt-4.1-mini --prompt v1 --max-cost-usd 1
uv run --project api python evals/run.py --compare artifacts/runs/<a> artifacts/runs/<b>
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from agentlab.agent import AgentModel
from agentlab.evaluation import compare, runner
from agentlab.models import OpenAIModel, RuleBasedModel

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    load_dotenv(ROOT / ".env")  # LangSmith reads LANGSMITH_* from the environment
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="rule-baseline")
    parser.add_argument("--prompt", default="v1", choices=["v1", "v2"])
    parser.add_argument("--cases", nargs="*", help="case ids or categories")
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "runs"))
    parser.add_argument("--compare", nargs=2, metavar=("BASE", "CANDIDATE"))
    args = parser.parse_args()

    if args.compare:
        result = compare.compare(Path(args.compare[0]), Path(args.compare[1]))
        print(json.dumps(result, indent=2))
        return

    model: AgentModel
    if args.model == "rule-baseline":
        model = RuleBasedModel()
    else:
        if args.max_cost_usd is None:
            raise SystemExit("online runs need --max-cost-usd")
        model = OpenAIModel(args.model, os.environ["OPENAI_API_KEY"])
    out = runner.run(model, args.prompt, Path(args.out), args.cases, args.max_cost_usd)
    summary = json.loads((out / "summary.json").read_text())
    keys = [
        "completion_rate",
        "clean_rate",
        "tool_precision",
        "args_valid_rate",
        "safe_rate",
        "grounded_rate",
        "right_answer_wrong_tool",
        "cost_usd",
    ]
    print(out.name, {k: summary[k] for k in keys})
    print("failures:", summary["failures"])


if __name__ == "__main__":
    main()
