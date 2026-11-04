"""Request compatibility and cost guards; no provider calls."""

import pytest

from agentlab.evaluation.runner import cost_usd
from agentlab.models import model_settings


def test_legacy_settings_preserved() -> None:
    assert model_settings("gpt-4.1-mini") == {"temperature": 0.0}
    assert model_settings("gpt-5-mini") == {}


@pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-6.1-sol"])
def test_current_models_use_responses(model: str) -> None:
    settings = model_settings(model)
    assert settings["use_responses_api"] is True
    assert settings["reasoning"] == {"effort": "low"}
    assert "temperature" not in settings


def test_current_prices() -> None:
    assert cost_usd("gpt-6-luna", 1_000_000, 1_000_000) == pytest.approx(0.60)
    assert cost_usd("gpt-6.1-sol", 1_000_000, 1_000_000) == pytest.approx(12.0)


def test_unknown_model_cannot_run_unbudgeted() -> None:
    with pytest.raises(SystemExit, match="no price"):
        cost_usd("unknown", 1, 1)


def test_responses_text_blocks_normalized_without_losing_usage() -> None:
    from unittest.mock import Mock

    from langchain_core.messages import AIMessage

    from agentlab.models import OpenAIModel

    model = OpenAIModel.__new__(OpenAIModel)
    model._chat = Mock()
    model._chat.invoke.return_value = AIMessage(
        content=[
            {"type": "reasoning", "summary": []},
            {"type": "text", "text": "Verified answer?"},
        ],
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )
    reply = model.invoke([])
    assert reply.content == "Verified answer?"
    assert reply.usage_metadata is not None
    assert reply.usage_metadata["output_tokens"] == 5
