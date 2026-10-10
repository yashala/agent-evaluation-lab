# Contributing

```bash
make setup db
make lint typecheck test web-test gate
```
No API keys are needed for any of these; the gate uses the deterministic rule baseline.

- **Changing the agent, policy, cases or scorer** usually changes baseline outcomes. Run
  `make gate`; if the change is intended, accept it with
  `uv run --project api python evals/gate.py <run> --update` in the same commit and explain why.
- **Correcting a case after reading model output**: say so in the commit message and re-score
  existing runs with `evals/rescore.py` rather than re-running models.
- **Online runs** always need `--max-cost-usd`. Add new model prices to `evals/pricing.yaml`
  with the source and date.
- Do not edit `docs/results/` or the README results table by hand; run `make report`.
