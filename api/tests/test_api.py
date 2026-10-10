import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from agentlab.evaluation import runner
from agentlab.models import RuleBasedModel

pytestmark = pytest.mark.integration
URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    if not URL:
        pytest.skip("TEST_DATABASE_URL not set")
    with psycopg.connect(URL) as conn:
        conn.execute("DROP TABLE IF EXISTS case_results, runs")
    runner.run(RuleBasedModel(), "v1", tmp_path, ["status-01", "refund-req-02", "privacy-01"])
    from agentlab import app as app_module

    monkeypatch.setattr(app_module, "DATABASE_URL", URL)
    monkeypatch.setattr(app_module, "RUNS_DIR", tmp_path)
    with TestClient(app_module.app) as c:
        yield c


def test_run_is_loaded_and_served(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "runs": 1}
    run = client.get("/runs").json()[0]
    assert run["model"] == "rule-baseline"
    assert run["summary"]["cases"] == 3
    cases = client.get(f"/runs/{run['id']}/cases").json()
    assert [c["case_id"] for c in cases] == ["privacy-01", "refund-req-02", "status-01"]


def test_trace_includes_events_and_expectation(client: TestClient) -> None:
    run_id = client.get("/runs").json()[0]["id"]
    trace = client.get(f"/runs/{run_id}/cases/refund-req-02").json()
    tools = [e["name"] for e in trace["events"] if e["type"] == "tool"]
    assert tools[-1] == "issue_refund"  # the naive baseline attempts it; policy denies it
    assert trace["score"]["failure"] == "unsafe_action"
    assert trace["expect"]["forbidden_tools"] == ["issue_refund"]


def test_cross_run_query_finds_attempted_tool(client: TestClient) -> None:
    hits = client.get("/tools/issue_refund/attempts").json()
    assert [h["case_id"] for h in hits] == ["refund-req-02"]


def test_unknown_run_is_404(client: TestClient) -> None:
    assert client.get("/runs/nope/cases").status_code == 404
    assert client.get("/compare", params={"base": "a", "candidate": "b"}).status_code == 404
