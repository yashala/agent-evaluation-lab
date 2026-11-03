"""Budgeted repeated comparison. Never logs credentials."""

from __future__ import annotations

import fcntl
import json
import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage

from agentlab.evaluation.runner import cost_usd, run
from agentlab.models import OpenAIModel

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "current-comparison"
LEDGER = OUT / "final-budget.json"
LIMIT = 3.0
LOCK = threading.Lock()


@contextmanager
def budget_lock() -> Iterator[None]:
    with LOCK, (OUT / "budget.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def save_ledger(ledger: dict[str, Any]) -> None:
    temp = LEDGER.with_suffix(".tmp")
    temp.write_text(json.dumps(ledger, indent=2))
    temp.replace(LEDGER)


class BudgetModel(OpenAIModel):
    def __init__(self, model: str, api_key: str) -> None:
        super().__init__(model, api_key, max_output_tokens=2048, max_retries=0)
        # Disable automatic retries and bound response tokens, including reasoning.
        self.settings.update({"max_output_tokens": 2048, "max_retries": 0})

    def invoke(self, messages: list[AnyMessage]) -> AIMessage:
        # Reserve before transmission; keep it if a request fails after submission.
        size = len(json.dumps([m.model_dump() for m in messages], default=str).encode()) + 20000
        reserve = cost_usd(self.name, size, 2048)
        with budget_lock():
            ledger = (
                json.loads(LEDGER.read_text())
                if LEDGER.exists()
                else {"estimated_usd": 0.0, "calls": 0}
            )
            if ledger["estimated_usd"] + reserve > LIMIT:
                raise RuntimeError("Campaign budget reserve exhausted before request")
            ledger["estimated_usd"] += reserve
            ledger["calls"] += 1
            save_ledger(ledger)
        reply = super().invoke(messages)
        usage: dict[str, Any] = dict(reply.usage_metadata or {})
        if "input_tokens" not in usage or "output_tokens" not in usage:
            raise RuntimeError("Missing usage; keeping reserved budget and stopping")
        actual = cost_usd(self.name, usage["input_tokens"], usage["output_tokens"])
        with budget_lock():
            ledger = json.loads(LEDGER.read_text())
            ledger["estimated_usd"] += actual - reserve
            save_ledger(ledger)
        return reply


def main() -> None:
    load_dotenv(ROOT / ".env")
    os.environ["LANGSMITH_TRACING"] = "false"
    OUT.mkdir(parents=True, exist_ok=True)

    def job(task: tuple[int, str, str]) -> None:
        repetition, name, prompt = task
        print(f"Start repeat={repetition} model={name} prompt={prompt}", flush=True)
        dest = OUT / "final" / f"repeat-{repetition}"
        try:
            result = run(
                BudgetModel(name, os.environ["OPENAI_API_KEY"]), prompt, dest, max_cost_usd=1
            )
        except Exception as exc:
            print(f"Stopped {name}/{prompt}: {type(exc).__name__}", flush=True)
            return
        summary = json.loads((result / "summary.json").read_text())
        print(
            json.dumps(
                {
                    "run": result.name,
                    "cases": summary["cases"],
                    "completion": summary["completion_rate"],
                    "clean": summary["clean_rate"],
                    "cost": summary["cost_usd"],
                }
            ),
            flush=True,
        )

    tasks = [
        (r, m, p) for r in range(1, 4) for m in ("gpt-6-luna", "gpt-6.1-sol") for p in ("v1", "v2")
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(job, tasks))
    print("BUDGET", LEDGER.read_text(), flush=True)


if __name__ == "__main__":
    main()
