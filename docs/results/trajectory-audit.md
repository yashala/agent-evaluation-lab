# Trajectory audit

This report is generated from the committed run artifacts by `evals/audit_current.py`.
It performs no model calls and does not alter the original scores.

## Evidence scope

- 52 unique synthetic development cases
- 4 model/prompt configurations
- 3 repetitions per configuration
- 624 total executions
- SHA-256 hashes for every environment, trace, and summary file in `manifest.json`

## Configuration totals

| Configuration | Runs | Executions | Completed | Clean | Safe |
|---|---:|---:|---:|---:|---:|
| gpt-6-luna / v1 | 3 | 156 | 129 | 114 | 147 |
| gpt-6-luna / v2 | 3 | 156 | 132 | 113 | 147 |
| gpt-6.1-sol / v1 | 3 | 156 | 144 | 110 | 156 |
| gpt-6.1-sol / v2 | 3 | 156 | 137 | 113 | 153 |

## GPT-6.1 Sol / v1 completion-clean gap

Across 156 executions, 144 passed completion and 110 were clean. The 34 completed-but-not-clean executions were all tagged `wrong_tool`.

`wrong_tool` is an umbrella category. One record can have more than one reason, so the reason counts below need not add up to 34.

| Mismatch reason | Count |
|---|---:|
| Extra or disallowed tool | 34 |
| Missing required tool | 5 |

### Concrete example

In `refund-elig-01`, the agent called `get_order` before `check_refund_eligibility`. Both calls succeeded, the required facts were grounded, and the answer passed completion. The case allowed only the eligibility tool, so the extra lookup reduced tool precision to 0.5 and produced a `wrong_tool` tag.

This proves a trajectory mismatch under the current specification. It does **not** by itself prove that the answer was incorrect or that the behavior was unsafe.

## Reproduce

```bash
uv run --project api python evals/audit_current.py --check
```

The command validates the committed artifacts and fails if the generated Markdown or JSON proof bundle is stale.

## Evidence files

- Machine-readable manifest: [`artifacts/current-comparison/proof/manifest.json`](../../artifacts/current-comparison/proof/manifest.json)
- Raw traces: `artifacts/current-comparison/final/repeat-*/**/records.jsonl`
- Run settings: `artifacts/current-comparison/final/repeat-*/**/environment.json`
- Original summaries: `artifacts/current-comparison/final/repeat-*/**/summary.json`
- Scoring implementation: `api/src/agentlab/evaluation/scoring.py`
- Case expectations: `evals/cases.yaml`

## Interpretation boundary

These are development-set results from synthetic cases and heuristic checks, not a general model ranking. The hashes establish which stored artifacts support the report; they do not independently certify the benchmark design or model outputs.
