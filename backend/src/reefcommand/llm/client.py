"""LLM client with schema-constrained output.

Every call in this system requests structured output against a Pydantic model.
There is no free-text call path, deliberately: a text response has nowhere to go
in this architecture.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import anthropic
from anthropic.types import ToolChoiceToolParam, ToolParam
from pydantic import BaseModel

from reefcommand.config import get_settings

_OUTPUT_TOOL_NAME = "emit_structured_output"


def _tool_use_input(response: Any) -> Mapping[str, Any]:
    """Extract the forced output tool payload from an Anthropic response."""
    for block in response.content:
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == _OUTPUT_TOOL_NAME
        ):
            input_data = getattr(block, "input", None)
            if isinstance(input_data, Mapping):
                return input_data
    raise ValueError("model response did not contain the required structured output tool call")


def complete_structured[T: BaseModel](
    system: str,
    user: str,
    schema: type[T],
    max_retries: int = 2,
    *,
    client: anthropic.Anthropic | None = None,
) -> T:
    """Call the model and parse into `schema`.

    On a validation failure, retry with the validation error appended so the model
    can correct itself. After `max_retries`, raise rather than returning a
    partially-repaired object.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")

    anthropic_client = client or anthropic.Anthropic(timeout=get_settings().llm_timeout_seconds)
    tool = ToolParam(
        name=_OUTPUT_TOOL_NAME,
        description="Return the final response using exactly this JSON schema.",
        input_schema=schema.model_json_schema(),
    )
    prompt = user

    for attempt in range(max_retries + 1):
        response = anthropic_client.messages.create(
            model=get_settings().llm_model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice=ToolChoiceToolParam(type="tool", name=_OUTPUT_TOOL_NAME),
        )
        try:
            return schema.model_validate(_tool_use_input(response))
        except (TypeError, ValueError) as exc:
            if attempt == max_retries:
                raise ValueError("model failed to produce valid structured output") from exc
            prompt = (
                f"{user}\n\nYour previous response failed schema validation: {exc}. "
                "Return a corrected structured output and no additional fields."
            )

    raise AssertionError("structured completion loop exited unexpectedly")
