"""Postgres query layer over run artifacts.

`artifacts/runs/*` is the source of truth (committed, reviewable). `sync_runs` loads any run not
yet in the database, so the database can be dropped and rebuilt at any time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           text PRIMARY KEY,
    model        text NOT NULL,
    prompt       text NOT NULL,
    created_at   timestamptz NOT NULL,
    complete     boolean NOT NULL,
    summary      jsonb NOT NULL,
    environment  jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS case_results (
    run_id      text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    case_id     text NOT NULL,
    category    text NOT NULL,
    message     text NOT NULL,
    completed   boolean NOT NULL,
    failure     text,
    score       jsonb NOT NULL,
    answer      text NOT NULL,
    events      jsonb NOT NULL,
    latency_ms  real NOT NULL,
    cost_usd    real NOT NULL,
    PRIMARY KEY (run_id, case_id)
);
CREATE INDEX IF NOT EXISTS case_results_events_idx
    ON case_results USING gin (events jsonb_path_ops);
"""


def connect(url: str) -> psycopg.Connection[dict[str, Any]]:
    conn = psycopg.connect(url, row_factory=dict_row)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def sync_runs(conn: psycopg.Connection[Any], runs_dir: Path) -> list[str]:
    """Load complete-or-partial runs that have a summary and are not yet stored."""
    stored = {row["id"] for row in conn.execute("SELECT id FROM runs").fetchall()}
    loaded = []
    for run in sorted(p for p in runs_dir.glob("*") if (p / "summary.json").exists()):
        if run.name in stored:
            continue
        env = json.loads((run / "environment.json").read_text())
        summary = json.loads((run / "summary.json").read_text())
        records = [json.loads(line) for line in (run / "records.jsonl").open()]
        with conn.transaction():
            conn.execute(
                "INSERT INTO runs VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    run.name,
                    env["model"],
                    env["prompt_version"],
                    env["timestamp"],
                    env.get("complete", True),
                    Jsonb(summary),
                    Jsonb(env),
                ),
            )
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO case_results VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        (
                            run.name,
                            r["case_id"],
                            r["category"],
                            r["message"],
                            r["score"]["completed"],
                            r["score"]["failure"],
                            Jsonb(r["score"]),
                            r["answer"],
                            Jsonb(r["events"]),
                            r["latency_ms"],
                            r["cost_usd"],
                        )
                        for r in records
                    ],
                )
        loaded.append(run.name)
    return loaded


def attempted_tool(conn: psycopg.Connection[Any], tool: str) -> list[dict[str, Any]]:
    """Every case result, across runs, where the agent attempted a given tool."""
    return conn.execute(
        """SELECT run_id, case_id, category, failure FROM case_results
           WHERE events @> %s ORDER BY run_id, case_id""",
        (Jsonb([{"type": "tool", "name": tool}]),),
    ).fetchall()
