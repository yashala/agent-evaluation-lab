# ADR 0002: A policy check owns tool execution, and denied attempts are scored

Status: accepted (2026-10-10)

## Decision
The model only proposes tool calls. `policy.check` validates arguments against the Pydantic
schema (including unknown arguments), denies non-read-only tools for the agent role, and denies
access to records owned by a different customer than the session's. Denied calls return an
error to the model and are recorded in the trace.

## Why score attempts, not only outcomes
A blocked attempt to read another customer's order looks identical to a correct refusal if only
the final answer is checked. The evaluation counts the attempt, because in a system with a weaker
policy layer the same behaviour would leak data.

## Consequences
Safety numbers measure the model's behaviour under this policy, not the safety of the system:
the policy blocks every attempted violation in these cases by construction.
