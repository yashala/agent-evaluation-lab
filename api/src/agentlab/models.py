"""Agent model backends.

`RuleBasedModel` is a deterministic, deliberately naive baseline for CI: keyword rules choose a
tool and the final answer restates the last tool result. It makes realistic mistakes (it passes
bare order numbers without the ORD- prefix, ignores conflicting data, and attempts a refund when
asked to "process" one) so the scorers have real failures to detect without network access.
"""

from __future__ import annotations

import json
import re
from itertools import count
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import SecretStr

from agentlab.agent import tool_schemas

_ids = count(1)


def _call(name: str, **args: Any) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": f"call_{next(_ids)}"}])


class RuleBasedModel:
    name = "rule-baseline"

    def invoke(self, messages: list[AnyMessage]) -> AIMessage:
        user = next(m for m in messages if isinstance(m, HumanMessage))
        text = str(user.content)
        lower = text.lower()
        results = [json.loads(str(m.content)) for m in messages if isinstance(m, ToolMessage)]
        calls = [c for m in messages if isinstance(m, AIMessage) for c in m.tool_calls]
        called = [c["name"] for c in calls]

        if not calls:
            return self._first_step(text, lower, messages)

        last = results[-1]
        if "error" in last:
            return AIMessage(f"Sorry, I could not complete that: {last['error']}")
        if called[-1] == "lookup_customer":
            return _call("list_orders", customer_id=last["id"])
        if (
            called[-1] == "get_order"
            and last.get("tracking_id")
            and re.search(r"where|track|ship|arriv|deliver", lower)
        ):
            return _call("get_shipment", tracking_id=last["tracking_id"])
        if (
            called[-1] == "check_refund_eligibility"
            and last.get("eligible")
            and re.search(r"process|issue|refund me", lower)
        ):
            return _call("issue_refund", order_id=last["order_id"], amount=last["amount"])
        return AIMessage(_summarise(called[-1], last))

    def _first_step(self, text: str, lower: str, messages: list[AnyMessage]) -> AIMessage:
        order = re.search(r"ORD-\d{5}", text)
        bare = re.search(r"\border\s*#?\s*(\d{4,6})\b", lower)
        email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        if order:
            if "refund" in lower or "return" in lower:
                return _call("check_refund_eligibility", order_id=order.group())
            return _call("get_order", order_id=order.group())
        if bare:
            return _call("get_order", order_id=bare.group(1))  # naive: no ORD- prefix
        if email:
            return _call("lookup_customer", email=email.group())
        if re.search(r"refund policy|return window|how long .* return", lower):
            region = re.search(r"region (\w\w)", str(messages[0].content))
            return _call("get_refund_policy", region=region.group(1) if region else "US")
        if re.search(r"my orders|recent order|last order", lower):
            customer = re.search(r"id (C-\d+)", str(messages[0].content))
            return _call("list_orders", customer_id=customer.group(1) if customer else "")
        words = [w for w in re.findall(r"[a-z]+", lower) if len(w) > 3]
        if words:
            return _call("search_kb", query=" ".join(words[:6]))
        return AIMessage("I can help with orders, shipping and returns.")


def _summarise(tool: str, result: dict[str, Any]) -> str:
    if tool == "get_order":
        status = result["status"].replace("_", " ")
        return f"Order {result['id']} is {status}; total {result['total']:.2f}."
    if tool == "get_shipment":
        eta = f", expected {result['eta']}" if result.get("eta") else ""
        return (
            f"Your shipment is {result['status'].replace('_', ' ')} at {result['location']}{eta}."
        )
    if tool == "check_refund_eligibility":
        if result.get("eligible"):
            return f"Order {result['order_id']} is eligible for a refund of {result['amount']:.2f}."
        return f"Order {result['order_id']} is not eligible: {result['reason']}."
    if tool == "list_orders":
        latest = result["orders"][0] if result["orders"] else None
        return (
            f"Your most recent order is {latest['id']} ({latest['status']})."
            if latest
            else "No orders found."
        )
    if tool == "get_refund_policy":
        return f"Returns are accepted within {result['window_days']} days: {result['condition']}."
    if tool == "search_kb":
        top = result["results"][0] if result["results"] else None
        return top["body"] if top else "I could not find an article about that."
    if tool == "issue_refund":
        return "Your refund has been issued."
    return json.dumps(result)


class OpenAIModel:
    def __init__(self, model: str, api_key: str) -> None:
        from langchain_openai import ChatOpenAI

        self.name = model
        temperature = None if model.startswith(("gpt-5", "o")) else 0.0
        chat = ChatOpenAI(
            model=model, api_key=SecretStr(api_key), temperature=temperature, max_retries=2
        )
        self._chat = chat.bind_tools(tool_schemas(), parallel_tool_calls=False)

    def invoke(self, messages: list[AnyMessage]) -> AIMessage:
        reply = self._chat.invoke(messages)
        assert isinstance(reply, AIMessage)
        return reply


__all__ = ["OpenAIModel", "RuleBasedModel", "SystemMessage"]
