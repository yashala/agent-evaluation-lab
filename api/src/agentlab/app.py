"""Read-only API for the dashboard. Loads new run artifacts into Postgres on startup."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException

from agentlab import store
from agentlab.evaluation.compare import compare
from agentlab.evaluation.runner import load_cases

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://agentlab:agentlab@localhost:5434/agentlab"
)
RUNS_DIR = Path(
    os.environ.get("RUNS_DIR", Path(__file__).resolve().parents[3] / "artifacts" / "runs")
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with store.connect(DATABASE_URL) as conn:
        store.sync_runs(conn, RUNS_DIR)
    yield


app = FastAPI(title="agent-evaluation-lab", lifespan=lifespan)


def db() -> Iterator[psycopg.Connection[Any]]:
    with store.connect(DATABASE_URL) as conn:
        yield conn


Db = Annotated[psycopg.Connection[Any], Depends(db)]


@app.get("/health")
def health(conn: Db) -> dict[str, Any]:
    row = conn.execute("SELECT count(*) AS n FROM runs").fetchone()
    return {"status": "ok", "runs": row["n"] if row else 0}


@app.post("/sync")
def sync(conn: Db) -> dict[str, Any]:
    return {"loaded": store.sync_runs(conn, RUNS_DIR)}


@app.get("/runs")
def runs(conn: Db) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT id, model, prompt, created_at, complete, summary FROM runs ORDER BY created_at"
    ).fetchall()


@app.get("/runs/{run_id}/cases")
def run_cases(run_id: str, conn: Db) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT case_id, category, message, completed, failure, score, answer, latency_ms,
                  cost_usd FROM case_results WHERE run_id = %s ORDER BY case_id""",
        (run_id,),
    ).fetchall()
    if not rows:
        raise HTTPException(404, "run not found")
    return rows


@app.get("/runs/{run_id}/cases/{case_id}")
def case_trace(run_id: str, case_id: str, conn: Db) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM case_results WHERE run_id = %s AND case_id = %s", (run_id, case_id)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "case not found")
    definition = next((c for c in load_cases([case_id]) if c.id == case_id), None)
    row["expect"] = definition.expect.__dict__ if definition else None
    result: dict[str, Any] = row
    return result


@app.get("/compare")
def compare_runs(base: str, candidate: str) -> dict[str, Any]:
    paths = [RUNS_DIR / base, RUNS_DIR / candidate]
    if not all((p / "summary.json").exists() for p in paths):
        raise HTTPException(404, "run not found")
    return compare(*paths)


@app.get("/tools/{tool}/attempts")
def tool_attempts(tool: str, conn: Db) -> list[dict[str, Any]]:
    return store.attempted_tool(conn, tool)
