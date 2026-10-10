from typing import Any

import pytest
from langchain_core.messages import AIMessage, AnyMessage

from agentlab import tools
from agentlab.agent import SupportAgent, tool_schemas
from agentlab.fixtures import FixtureStore
from agentlab.models import RuleBasedModel
from agentlab.policy import Session

MAYA = Session("C-1001")


class Scripted:
    """Returns pre-written replies in order, like a model that always makes the same choices."""

    name = "scripted"

    def __init__(self, *replies: AIMessage) -> None:
        self.replies = list(replies)

    def invoke(self, messages: list[AnyMessage]) -> AIMessage:
        return self.replies.pop(0) if self.replies else AIMessage("done")


def call(name: str, **args: Any) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": f"c-{name}"}])


def test_denied_tool_never_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    executed: list[str] = []

    def spy(store: FixtureStore, args: Any) -> dict[str, Any]:
        executed.append("issue_refund")
        return {}

    spec = tools.TOOLS["issue_refund"]
    monkeypatch.setitem(
        tools.TOOLS, "issue_refund", tools.ToolSpec(spec.name, spec.args, spy, read_only=False)
    )
    agent = SupportAgent(Scripted(call("issue_refund", order_id="ORD-20401", amount=129.0)))
    result = agent.run("refund please", FixtureStore.load(), MAYA)
    assert executed == []
    tool_events = [e for e in result.events if e["type"] == "tool"]
    assert tool_events[0]["verdict"] == "not_permitted"
    assert "DENIED" in tool_events[0]["result"]["error"]


def test_step_limit_stops_a_looping_model() -> None:
    looping = Scripted(*[call("search_kb", query="returns") for _ in range(20)])
    result = SupportAgent(looping, max_steps=3).run("help", FixtureStore.load(), MAYA)
    assert result.hit_step_limit
    assert result.steps == 3
    assert result.answer == ""


def test_trace_records_model_and_tool_events_in_order() -> None:
    result = SupportAgent(RuleBasedModel()).run(
        "Where is my order ORD-20417?", FixtureStore.load(), MAYA
    )
    kinds = [(e["type"], e.get("name")) for e in result.events]
    assert kinds == [
        ("model", None),
        ("tool", "get_order"),
        ("model", None),
        ("tool", "get_shipment"),
        ("model", None),
    ]
    assert "Omaha" in result.answer


def test_tool_schemas_use_policy_names() -> None:
    names = {t["function"]["name"] for t in tool_schemas()}
    assert names == set(tools.TOOLS)
