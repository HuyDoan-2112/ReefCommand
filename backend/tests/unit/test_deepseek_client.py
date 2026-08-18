"""Tests for the DeepSeek JSON-mode provider adapter."""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ConfigDict, Field

from reefcommand.config import get_settings
from reefcommand.llm.client import collect_llm_calls, complete_structured


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)


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
                "choices": [{"message": {"content": json.dumps(content)}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )


def test_deepseek_json_mode_validates_and_retries(monkeypatch) -> None:
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
    assert request["url"] == "https://api.deepseek.com/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    body = request["json"]
    assert body["model"] == "deepseek-v4-flash"
    assert body["response_format"] == {"type": "json_object"}
    assert "json" in body["messages"][0]["content"].lower()
    assert "score" in body["messages"][1]["content"]
    assert len(calls) == 1
    assert calls[0].provider == "deepseek"
    assert calls[0].attempt_count == 2
    assert calls[0].input_tokens == 20
    assert calls[0].output_tokens == 4
