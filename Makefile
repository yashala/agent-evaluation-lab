API := uv run --project api
TEST_DB ?= postgresql://agentlab:agentlab@localhost:5434/agentlab_test

.PHONY: setup up down db lint typecheck test web-test eval-offline eval-online gate report langsmith audit

setup:
	cd api && uv sync
	cd web && npm ci

up:
	docker compose up --build -d
	@echo "Dashboard http://localhost:8081  API http://localhost:8001/health"

down:
	docker compose down

db:
	docker compose up -d --wait db
	docker compose exec -T db psql -U agentlab -tc "SELECT 1 FROM pg_database WHERE datname='agentlab_test'" | grep -q 1 || docker compose exec -T db createdb -U agentlab agentlab_test

lint:
	$(API) ruff check api evals
	$(API) ruff format --check api evals

typecheck:
	$(API) mypy --config-file api/pyproject.toml api/src api/tests evals/run.py evals/gate.py evals/report.py evals/rescore.py evals/langsmith_experiment.py
	cd web && npm run typecheck

test: db
	cd api && LANGSMITH_TRACING=false TEST_DATABASE_URL=$(TEST_DB) uv run pytest

web-test:
	cd web && npm test

eval-offline:
	LANGSMITH_TRACING=false $(API) python evals/run.py --model rule-baseline

gate:
	rm -rf /tmp/agentlab-gate && LANGSMITH_TRACING=false $(API) python evals/run.py --model rule-baseline --out /tmp/agentlab-gate >/dev/null
	$(API) python evals/gate.py /tmp/agentlab-gate/*

# Example: make eval-online MODEL=gpt-4.1-mini PROMPT=v1
eval-online:
	$(API) python evals/run.py --model $(MODEL) --prompt $(or $(PROMPT),v1) --max-cost-usd $(or $(BUDGET),1)

report:
	$(API) python evals/report.py

langsmith:
	for run in artifacts/runs/*; do $(API) python evals/langsmith_experiment.py --from-run $$run; done

audit:
	uv export --project api --frozen --no-hashes --no-dev --no-emit-project > /tmp/agentlab-req.txt && $(API) pip-audit -r /tmp/agentlab-req.txt
	cd web && npm audit --omit=dev
