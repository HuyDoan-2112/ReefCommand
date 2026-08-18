"""Tests for the DeepSeek JSON-mode provider adapter."""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ConfigDict, Field

from reefcommand.config import get_settings
from reefcommand.llm.client import (
    _deepseek_strict_schema,
    collect_llm_calls,
    complete_structured,
)


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)


def test_strict_schema_requires_every_property_and_removes_unsupported_keywords() -> None:
    class NestedOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")

        summary: str = Field(default="valid", min_length=1)
        notes: list[str] = Field(default_factory=list, min_length=1)

    schema = _deepseek_strict_schema(NestedOutput)

    assert schema["required"] == ["summary", "notes"]
    assert schema["additionalProperties"] is False
    assert "default" not in schema["properties"]["summary"]
    assert "minLength" not in schema["properties"]["summary"]
    assert "minItems" not in schema["properties"]["notes"]


class FakeDeepSeek:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> httpx.Response:
        self.requests.append({"url": url, **kwargs})
        content = {"score": 2.0} if len(self.requests) == 1 else {"score": 0.4}
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "emit_structured_output",
                                        "arguments": json.dumps(content),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )


def test_deepseek_forced_tool_validates_and_retries(monkeypatch) -> None:
    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REEFCOMMAND_LLM_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "test-key")
    get_settings.cache_clear()
    client = FakeDeepSeek()

    try:
        with collect_llm_calls() as calls:
            result = complete_structured(
                "system",
                "user",
                Output,
                client=None,
                http_client=client,
            )
    finally:
        get_settings.cache_clear()

    assert result.score == 0.4
    assert len(client.requests) == 2
    request = client.requests[0]
    assert request["url"] == "https://api.deepseek.com/beta/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    body = request["json"]
    assert body["model"] == "deepseek-v4-flash"
    assert body["tool_choice"]["function"]["name"] == "emit_structured_output"
    assert body["thinking"] == {"type": "disabled"}
    assert body["tools"][0]["function"]["strict"] is True
    parameters = body["tools"][0]["function"]["parameters"]
    assert parameters["required"] == ["score"]
    assert parameters["additionalProperties"] is False
    assert body["max_tokens"] == 4096
    assert len(calls) == 1
    assert calls[0].provider == "deepseek"
    assert calls[0].attempt_count == 2
    assert calls[0].input_tokens == 20
    assert calls[0].output_tokens == 4


def test_deepseek_retries_transient_http_failures(monkeypatch) -> None:
    class TransientDeepSeek(FakeDeepSeek):
        def post(self, url: str, **kwargs: object) -> httpx.Response:
            if not self.requests:
                self.requests.append({"url": url, **kwargs})
                return httpx.Response(429, request=httpx.Request("POST", url))
            return super().post(url, **kwargs)

    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REEFCOMMAND_LLM_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("REEFCOMMAND_LLM_RETRY_BACKOFF_SECONDS", "0")
    get_settings.cache_clear()
    client = TransientDeepSeek()
    try:
        result = complete_structured("system", "user", Output, http_client=client)
    finally:
        get_settings.cache_clear()

    assert result.score == 0.4
    assert len(client.requests) == 2
