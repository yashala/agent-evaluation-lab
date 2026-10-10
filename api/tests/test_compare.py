import json
from pathlib import Path
from typing import Any

from agentlab.evaluation.compare import compare


def write_run(
    path: Path, summary: dict[str, Any], scores: dict[str, tuple[bool, str | None]]
) -> Path:
    path.mkdir()
    (path / "environment.json").write_text(json.dumps({"model": "m", "prompt_version": "v1"}))
    (path / "summary.json").write_text(json.dumps(summary))
    with (path / "records.jsonl").open("w") as f:
        for case_id, (done, failure) in scores.items():
            f.write(
                json.dumps(
                    {
                        "case_id": case_id,
                        "score": {"category": "c", "completed": done, "failure": failure},
                    }
                )
                + "\n"
            )
    return path


def test_detects_tradeoff_and_flipped_cases(tmp_path: Path) -> None:
    base = write_run(
        tmp_path / "a",
        {"completion_rate": 0.80, "safe_rate": 1.0, "cost_usd": 0.10},
        {"x": (True, None), "y": (False, "incomplete")},
    )
    cand = write_run(
        tmp_path / "b",
        {"completion_rate": 0.90, "safe_rate": 0.90, "cost_usd": 0.10},
        {"x": (True, "unsafe_action"), "y": (True, None)},
    )
    result = compare(base, cand)
    assert result["improved"] == ["completion_rate"]
    assert result["regressed"] == ["safe_rate"]
    assert result["tradeoff"] is True
    assert [(f["case_id"], f["direction"]) for f in result["flipped_cases"]] == [
        ("x", "broke"),
        ("y", "fixed"),
    ]
    assert result["deltas"]["cost_usd"]["verdict"] == "same"


def test_changes_below_noise_threshold_are_same(tmp_path: Path) -> None:
    base = write_run(tmp_path / "a", {"completion_rate": 0.800}, {})
    cand = write_run(tmp_path / "b", {"completion_rate": 0.815}, {})
    assert compare(base, cand)["deltas"]["completion_rate"]["verdict"] == "same"
