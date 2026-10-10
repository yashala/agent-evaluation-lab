FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv
WORKDIR /app/api
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY api/pyproject.toml api/uv.lock api/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY api/src ./src
RUN uv sync --frozen --no-dev
COPY data /app/data
COPY evals/cases.yaml evals/pricing.yaml /app/evals/
RUN useradd --create-home app
USER app
ENV PATH="/app/api/.venv/bin:$PATH" RUNS_DIR=/app/artifacts/runs
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "agentlab.app:app", "--host", "0.0.0.0", "--port", "8000"]
