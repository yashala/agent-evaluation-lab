# ADR 0001: Tool fixtures in memory; run results in Postgres, rebuilt from artifacts

Status: accepted (2026-10-10)

## Context
Tools need data that is identical for every run, and some cases need deliberately contradictory
data (an order and its shipment disagreeing). Results need to be compared across runs.

## Decision
- Tools read an in-memory `FixtureStore` loaded from `data/fixtures.json`; each case may patch
  its own copy. No shared mutable state between cases.
- Each run writes JSON artifacts (`records.jsonl`, `summary.json`, `environment.json`), which
  are committed and are the source of truth.
- Postgres is a query layer loaded from artifacts (`store.sync_runs`). It can be dropped and
  rebuilt. JSONB plus a GIN index answers cross-run questions such as "every case where the
  agent attempted `issue_refund`".

## Simpler alternative
At this size the dashboard could read the JSON files directly. Postgres is kept because the
brief asks for it and because cross-run JSONB queries are the realistic way such a lab grows;
the cost is one more container.
