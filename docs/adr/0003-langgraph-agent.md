# ADR 0003: LangGraph loop with explicit escalation tool; LangChain for tool binding

Status: accepted (2026-10-10)

## Decision
- A two-node LangGraph (`agent` -> `tools` -> `agent`) with a step limit. Every model and tool
  call is appended to the state's `events`, which is the scored trace; with LangSmith enabled each
  node is also a traced span tagged with model, prompt version and case id.
- `ChatOpenAI.bind_tools` with hand-built function schemas named exactly like the policy's tools.
- Escalation is a tool (`escalate_to_human`) rather than a phrase in the answer, so "did it
  escalate?" is checked from the trace, not by keyword matching.

## Simpler alternative
`langgraph.prebuilt.create_react_agent` would replace the graph with one call. It is not used
because the policy check and per-call trace recording sit inside the tools node, and the custom
node keeps that logic visible and testable.
