# Newer-model comparison protocol

Status: live comparison started November 3, 2026; generated results are in `docs/results/current-model-comparison.md`.

Compare `gpt-6-luna` and `gpt-6.1-sol` against the committed GPT-4.1 baseline artifacts.
Sources checked November 3, 2026:

- https://developers.openai.com/api/docs/models/gpt-6-luna
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
- https://developers.openai.com/api/docs/pricing

Both new configurations use Responses and low reasoning effort. Record those settings in
each environment artifact. Historical configurations retain their previous transport and
settings; differences therefore concern complete configurations, not isolated model weights.

## Protocol

Freeze the existing cases, fixtures, prompts and scorer. Run both prompts (v1/v2) for each
model, three times each. Preserve each run, including failed or partial runs. Verify model
access with a small smoke case before starting full runs. Do not substitute unavailable models
without recording the change. Do not retune the scorer after seeing candidate results.

Report completion, clean completion, tool precision/recall, argument validity, policy and
privacy attempts, leakage, p50/p95 latency, tokens and estimated cost. Report individual runs
and min/mean/max rates across repetitions; latency percentiles should be computed from raw
case measurements rather than averaged percentiles. Exclude partial runs from full-set averages
and identify them explicitly. All 52 cases must be present for a complete run.

The 52 cases are a development set. Repetitions estimate sampling variability, not generalization.
Historical single runs are descriptive references. Cache discounts are not modeled: costs are
conservative estimates using uncached standard input prices and all output tokens.

## Execution

Configure `OPENAI_API_KEY` in the environment or git-ignored root `.env`. Never paste it into
documentation or commit it. The user authorized a $3 total API budget. The repeated-comparison script uses a shared, locked ledger and conservative pre-request reservations; the original runner
budget checks are estimates between cases, not a provider-enforced billing ceiling.

Example for one configuration:

```sh
LANGSMITH_TRACING=false uv run --project api python evals/run.py \
  --model gpt-6-luna --prompt v1 --max-cost-usd 0.40
```

Repeat for both model IDs and both prompts, retaining all three repetitions. Review raw traces
for claimed failures, then regenerate comparison reports. Write the LinkedIn post only after
the resulting summaries and limitations are checked. Use only complete runs from `artifacts/current-comparison/final/`.


## Execution notes

The Responses adapter now normalizes text blocks into plain answer text before scoring.
Early partial runs made before that correction, and debugging attempts with a concurrent ledger
write issue, are excluded from result aggregation. Their costs remain covered by a conservative
$1 prior-attempt reserve in the final ledger. The final runner uses an interprocess file lock,
a thread lock, and atomic replacement for ledger updates. Responses are capped at 2,048 output
tokens and automatic retries are disabled. All input is estimated at uncached standard prices.
Package versions are recorded from the installed uv lockfile because local metadata reads stalled.
No LangSmith upload was performed during this campaign.
