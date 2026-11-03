# Proof index

This page maps public claims about the project to committed evidence. It is intentionally
stricter than a portfolio summary: every numerical claim must point to raw artifacts, a
reproducible derivation, and an interpretation boundary.

## Current comparison

| Claim | Evidence | Reproduce | Boundary |
|---|---|---|---|
| The comparison contains 624 executions | 12 complete `records.jsonl` files with 52 records each; proof manifest scope | `make proof-check` | 52 unique synthetic cases repeated across four configurations and three repetitions |
| GPT-6.1 Sol / v1 completed 144 of 156 executions | Per-record `score.completed`; three Sol/v1 trace files | `make proof-check` | Completion uses heuristic outcome and substring fact checks |
| GPT-6.1 Sol / v1 had 110 clean executions | Per-record `score.failure is None` | `make proof-check` | “Clean” means no failure under this scorer, not production safety certification |
| All 34 completed-but-not-clean Sol/v1 executions were tagged `wrong_tool` | [`trajectory-audit.md`](results/trajectory-audit.md) and machine-readable manifest | `make proof-check` | `wrong_tool` combines recall, precision, ordering, and argument mismatches |
| `refund-elig-01` was penalized for an extra lookup | Raw trace shows `get_order` then `check_refund_eligibility`; score has precision 0.5, completion true, grounded true | Inspect the matching record in each Sol/v1 trace | The trace proves a mismatch with the declared allowed-tool set, not that the extra call is always acceptable |
| The complete repeated comparison cost estimate is $1.5337 | 12 committed summaries; [`current-model-comparison.md`](results/current-model-comparison.md) | Sum `cost_usd` from the complete summaries | Estimated from token counts and listed rates; it is not a provider invoice |

## Integrity evidence

[`artifacts/current-comparison/proof/manifest.json`](../artifacts/current-comparison/proof/manifest.json)
contains the SHA-256 hash and byte length of every environment, trace, and summary file used by
the audit. The manifest makes accidental artifact drift detectable. It does not prove that the
benchmark design is valid or that a provider generated a specific output.

## Quality controls

- Unit and integration tests cover the API, policy layer, scoring, agent loop, and dashboard.
- The deterministic baseline is rerun in CI without API credentials and compared with its
  committed expected result.
- Ruff, mypy, frontend type checking, frontend tests, and dependency audits run in CI.
- `make proof-check` fails when the proof report or manifest is stale relative to raw artifacts.
- Online runs preserve the prompt hash, case-file hash, model settings, package versions, token
  usage, estimated cost, and per-case trace.

## What is not yet proven

- Generalization beyond the 52 synthetic development cases
- Statistical superiority of one model
- Production safety, fairness, or robustness
- Whether every extra or alternative tool path should be accepted
- Performance on a held-out set authored independently from the agent and scorer

Those are future experiments, not implied achievements.

