"""LLM client with schema-constrained output.

Every call in this system requests structured output against a Pydantic model.
There is no free-text call path, deliberately: a text response has nowhere to go
in this architecture.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import anthropic
import httpx
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


def _deepseek_json(response: httpx.Response) -> Mapping[str, Any]:
    """Extract the JSON object returned by DeepSeek JSON mode."""
    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("DeepSeek response did not contain message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise ValueError("DeepSeek returned empty structured output")
    parsed = json.loads(content)
    if not isinstance(parsed, Mapping):
        raise ValueError("DeepSeek structured output was not a JSON object")
    return parsed


def _complete_deepseek[T: BaseModel](
    system: str,
    user: str,
    schema: type[T],
    max_retries: int,
    *,
    client: httpx.Client | None = None,
) -> T:
    """Call DeepSeek's OpenAI-compatible JSON mode and validate the object."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise ValueError("REEFCOMMAND_DEEPSEEK_API_KEY is required when llm_provider is deepseek")

    schema_text = json.dumps(schema.model_json_schema(), indent=2)
    prompt = (
        f"{user}\n\nReturn one JSON object only. The JSON object must conform to "
        "this JSON schema:\n"
        f"{schema_text}"
    )
    owned_client = client or httpx.Client(timeout=settings.llm_timeout_seconds)
    endpoint = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    try:
        for attempt in range(max_retries + 1):
            response = owned_client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"{system}\nYour final answer must be a valid JSON object."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 2048,
                },
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            try:
                return schema.model_validate(_deepseek_json(response))
            except (TypeError, ValueError) as exc:
                if attempt == max_retries:
                    raise ValueError("DeepSeek failed to produce valid structured output") from exc
                prompt = (
                    f"{user}\n\nYour previous response failed schema validation: {exc}. "
                    "Return a corrected JSON object only.\n\n"
                    f"JSON schema:\n{schema_text}"
                )
    finally:
        if client is None:
            owned_client.close()

    raise AssertionError("DeepSeek structured completion loop exited unexpectedly")


def complete_structured[T: BaseModel](
    system: str,
    user: str,
    schema: type[T],
    max_retries: int = 2,
    *,
    client: anthropic.Anthropic | None = None,
    http_client: httpx.Client | None = None,
) -> T:
    """Call the model and parse into `schema`.

    On a validation failure, retry with the validation error appended so the model
    can correct itself. After `max_retries`, raise rather than returning a
    partially-repaired object.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")

    settings = get_settings()
    if settings.llm_provider == "deepseek":
        return _complete_deepseek(
            system,
            user,
            schema,
            max_retries,
            client=http_client,
        )

    anthropic_client = client or anthropic.Anthropic(timeout=settings.llm_timeout_seconds)
    tool = ToolParam(
        name=_OUTPUT_TOOL_NAME,
        description="Return the final response using exactly this JSON schema.",
        input_schema=schema.model_json_schema(),
    )
    prompt = user

    for attempt in range(max_retries + 1):
        response = anthropic_client.messages.create(
            model=settings.llm_model,
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
