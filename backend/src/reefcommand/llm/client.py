"""LLM client with schema-constrained output.

Every call in this system requests structured output against a Pydantic model.
There is no free-text call path, deliberately: a text response has nowhere to go
in this architecture.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from time import sleep
from typing import Any

import anthropic
import httpx
from anthropic.types import ToolChoiceToolParam, ToolParam
from pydantic import BaseModel

from reefcommand.config import get_settings

_OUTPUT_TOOL_NAME = "emit_structured_output"


@dataclass(frozen=True)
class LlmCallMetrics:
    """Redacted metadata for one schema-validated provider call."""

    provider: str
    model: str
    attempt_count: int
    input_tokens: int | None = None
    output_tokens: int | None = None


_METRICS_COLLECTOR: ContextVar[list[LlmCallMetrics] | None] = ContextVar(
    "reefcommand_llm_metrics_collector",
    default=None,
)


@contextmanager
def collect_llm_calls() -> Iterator[list[LlmCallMetrics]]:
    """Collect redacted provider metrics inside one agent stage."""
    calls: list[LlmCallMetrics] = []
    token = _METRICS_COLLECTOR.set(calls)
    try:
        yield calls
    finally:
        _METRICS_COLLECTOR.reset(token)


def _record_metrics(metrics: LlmCallMetrics) -> None:
    collector = _METRICS_COLLECTOR.get()
    if collector is not None:
        collector.append(metrics)


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


def _deepseek_tool_input(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Extract arguments from the forced DeepSeek structured-output tool call."""
    try:
        tool_calls = payload["choices"][0]["message"]["tool_calls"]
        function = tool_calls[0]["function"]
        name = function["name"]
        arguments = function["arguments"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("DeepSeek response did not contain the required tool call") from exc
    if name != _OUTPUT_TOOL_NAME:
        raise ValueError("DeepSeek called an unexpected structured-output tool")
    if not isinstance(arguments, str) or not arguments.strip():
        raise ValueError("DeepSeek returned empty tool arguments")
    parsed = json.loads(arguments)
    if not isinstance(parsed, Mapping):
        raise ValueError("DeepSeek tool arguments were not a JSON object")
    return parsed


def _retryable_http_error(exc: httpx.HTTPStatusError) -> bool:
    return exc.response.status_code == 429 or exc.response.status_code >= 500


def _provider_error_message(response: httpx.Response) -> str:
    """Extract a bounded provider message without logging request headers or bodies."""
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message")
    except (TypeError, ValueError):
        message = None
    if not isinstance(message, str) or not message.strip():
        return "no provider detail"
    return message.strip()[:300]


def _deepseek_strict_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Convert Pydantic JSON Schema to DeepSeek's documented strict subset."""
    document = deepcopy(schema.model_json_schema())
    unsupported = {"minLength", "maxLength", "minItems", "maxItems", "default", "title"}

    def normalize(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                normalize(item)
            return
        if not isinstance(node, dict):
            return
        for key in unsupported:
            node.pop(key, None)
        properties = node.get("properties")
        if isinstance(properties, dict):
            node["required"] = list(properties)
            node["additionalProperties"] = False
        for value in node.values():
            normalize(value)

    normalize(document)
    return document


def _token_count(usage: object, field: str) -> int | None:
    """Read a provider token counter from an object or response mapping."""
    value = usage.get(field) if isinstance(usage, Mapping) else getattr(usage, field, None)
    return value if isinstance(value, int) and value >= 0 else None


def _accumulate(current: int | None, value: int | None) -> int | None:
    if value is None:
        return current
    return (current or 0) + value


def _complete_deepseek[T: BaseModel](
    system: str,
    user: str,
    schema: type[T],
    max_retries: int,
    *,
    client: httpx.Client | None = None,
) -> T:
    """Call DeepSeek with a forced strict function and validate its arguments."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise ValueError("REEFCOMMAND_DEEPSEEK_API_KEY is required when llm_provider is deepseek")

    schema_definition = _deepseek_strict_schema(schema)
    prompt = user
    owned_client = client or httpx.Client(
        timeout=settings.llm_timeout_seconds,
        trust_env=settings.deepseek_trust_env,
    )
    endpoint = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    try:
        for attempt in range(max_retries + 1):
            try:
                response = owned_client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {settings.deepseek_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.llm_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": _OUTPUT_TOOL_NAME,
                                    "description": (
                                        "Return the final response using exactly this schema."
                                    ),
                                    "parameters": schema_definition,
                                    "strict": True,
                                },
                            }
                        ],
                        "tool_choice": {
                            "type": "function",
                            "function": {"name": _OUTPUT_TOOL_NAME},
                        },
                        "thinking": {"type": "disabled"},
                        "max_tokens": settings.llm_max_tokens,
                    },
                    timeout=settings.llm_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, Mapping):
                    raise ValueError("DeepSeek response was not a JSON object")
                usage = payload.get("usage")
                total_input_tokens = _accumulate(
                    total_input_tokens,
                    _token_count(usage, "prompt_tokens"),
                )
                total_output_tokens = _accumulate(
                    total_output_tokens,
                    _token_count(usage, "completion_tokens"),
                )
                result = schema.model_validate(_deepseek_tool_input(payload))
                _record_metrics(
                    LlmCallMetrics(
                        provider="deepseek",
                        model=settings.llm_model,
                        attempt_count=attempt + 1,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                )
                return result
            except httpx.HTTPStatusError as exc:
                if not _retryable_http_error(exc) or attempt == max_retries:
                    detail = _provider_error_message(exc.response)
                    raise ValueError(f"DeepSeek HTTP {exc.response.status_code}: {detail}") from exc
                sleep(settings.llm_retry_backoff_seconds * (2**attempt))
            except httpx.TransportError as exc:
                if attempt == max_retries:
                    raise ValueError("DeepSeek transport failed after retries") from exc
                sleep(settings.llm_retry_backoff_seconds * (2**attempt))
            except (TypeError, ValueError) as exc:
                if attempt == max_retries:
                    raise ValueError("DeepSeek failed to produce valid structured output") from exc
                prompt = (
                    f"{user}\n\nYour previous response failed schema validation: {exc}. "
                    "Call the required output function again with corrected arguments."
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

    anthropic_client = client or anthropic.Anthropic(
        timeout=settings.llm_timeout_seconds,
        max_retries=max_retries,
    )
    tool = ToolParam(
        name=_OUTPUT_TOOL_NAME,
        description="Return the final response using exactly this JSON schema.",
        input_schema=schema.model_json_schema(),
    )
    prompt = user
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None

    for attempt in range(max_retries + 1):
        response = anthropic_client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice=ToolChoiceToolParam(type="tool", name=_OUTPUT_TOOL_NAME),
        )
        usage = getattr(response, "usage", None)
        total_input_tokens = _accumulate(
            total_input_tokens,
            _token_count(usage, "input_tokens"),
        )
        total_output_tokens = _accumulate(
            total_output_tokens,
            _token_count(usage, "output_tokens"),
        )
        try:
            result = schema.model_validate(_tool_use_input(response))
            _record_metrics(
                LlmCallMetrics(
                    provider="anthropic",
                    model=settings.llm_model,
                    attempt_count=attempt + 1,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
            )
            return result
        except (TypeError, ValueError) as exc:
            if attempt == max_retries:
                raise ValueError("model failed to produce valid structured output") from exc
            prompt = (
                f"{user}\n\nYour previous response failed schema validation: {exc}. "
                "Return a corrected structured output and no additional fields."
            )

    raise AssertionError("structured completion loop exited unexpectedly")
