"""Tests for Anthropic structured-output request and validation behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict, Field

from reefcommand.llm.client import complete_structured


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)


class FakeMessages:
    def __init__(self, inputs: list[dict[str, object]]) -> None:
        self.inputs = inputs

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.inputs.append(kwargs)
        if len(self.inputs) == 1:
            block = SimpleNamespace(
                type="tool_use",
                name="emit_structured_output",
                input={"score": 2},
            )
        else:
            block = SimpleNamespace(
                type="tool_use",
                name="emit_structured_output",
                input={"score": 0.4},
            )
        return SimpleNamespace(content=[block])


class FakeClient:
    def __init__(self) -> None:
        self.inputs: list[dict[str, object]] = []
        self.messages = FakeMessages(self.inputs)


def test_complete_structured_forces_schema_tool_and_retries_validation() -> None:
    client = FakeClient()

    result = complete_structured("system", "user", Output, client=client)

    assert result.score == 0.4
    assert len(client.inputs) == 2
    tool_choice = client.inputs[0]["tool_choice"]
    assert tool_choice["type"] == "tool"
    assert tool_choice["name"] == "emit_structured_output"
    tools = client.inputs[0]["tools"]
    assert isinstance(tools, list)
    assert tools[0]["input_schema"] == Output.model_json_schema()


def test_complete_structured_fails_after_retry_budget() -> None:
    class AlwaysInvalid(FakeClient):
        def __init__(self) -> None:
            super().__init__()

            def create(**kwargs: object) -> SimpleNamespace:
                self.inputs.append(kwargs)
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            name="emit_structured_output",
                            input={"score": 2},
                        )
                    ]
                )

            self.messages = SimpleNamespace(
                create=create,
            )

    with pytest.raises(ValueError, match="valid structured output"):
        complete_structured(
            "system",
            "user",
            Output,
            max_retries=1,
            client=AlwaysInvalid(),
        )
