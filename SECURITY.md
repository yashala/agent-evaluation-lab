# Security

This repository evaluates an agent; it does not operate one against real systems.

- All data is synthetic. No tool touches a real account, payment system or network service.
- `issue_refund` is simulated and denied by the policy for the agent role in every run.
- The API is read-only, unauthenticated and bound to `127.0.0.1` by Docker Compose.
- Keys (`OPENAI_API_KEY`, `LANGSMITH_API_KEY`) are read from `.env`, which is git-ignored.

Report vulnerabilities through GitHub's private vulnerability reporting for this repository.
