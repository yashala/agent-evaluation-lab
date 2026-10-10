# Architecture

See the diagram in the README. Components:

| Component | File | Notes |
|---|---|---|
| Fixtures | `data/fixtures.json`, `fixtures.py` | Fictional store; per-case patches create conflicting data |
| Tools | `tools.py` | 7 read-only tools, simulated `issue_refund`, `escalate_to_human`; Pydantic arguments |
| Policy | `policy.py` | Runs before every call: schema, unknown args, role, record ownership |
| Agent | `agent.py` | LangGraph `agent -> tools -> agent`, step limit 6, records events |
| Models | `models.py` | `OpenAIModel` (LangChain `bind_tools`), `RuleBasedModel` (deterministic baseline) |
| Scoring | `evaluation/scoring.py` | Pure functions over (case, trace) |
| Runner | `evaluation/runner.py`, `evals/run.py` | Spend cap, artifacts, environment metadata |
| Compare | `evaluation/compare.py` | Deltas, flipped cases, trade-off detection |
| Store | `store.py` | Postgres loaded from artifacts; JSONB GIN index for cross-run queries |
| API | `app.py` | Read-only FastAPI: runs, cases, traces, comparisons, tool attempts |
| Dashboard | `web/` | React + TypeScript; runs table, comparison, case list and trace timeline |
| LangSmith | `evals/langsmith_experiment.py` | Dataset per case-file hash; experiments by replay or live |

## Trust boundaries
- The model never executes anything; the policy decides. `issue_refund` cannot run for the
  agent role, so no simulated money moves in any run.
- Tool results are passed back as tool messages. Text inside them (including planted
  instructions in help articles) reaches the model; the system prompt says it is data.
- The API is read-only and unauthenticated; it serves committed evaluation artifacts.
